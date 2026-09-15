from __future__ import annotations

import os
import re
import shutil
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from flask import Flask, flash, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent


def resolve_database_path() -> Path:
    """Retorna um caminho persistente e gravável para o SQLite.

    O python-for-android expõe ANDROID_PRIVATE apontando para o diretório
    privado da aplicação (Context.getFilesDir). No desktop, mantemos exatamente
    o comportamento original usando ``instance/financeiro.db`` ao lado do app.
    """
    android_private = os.environ.get("ANDROID_PRIVATE")
    if not android_private:
        return BASE_DIR / "instance" / "financeiro.db"

    android_instance = Path(android_private) / "financeiro" / "instance"
    android_instance.mkdir(parents=True, exist_ok=True)
    database = android_instance / "financeiro.db"

    if not database.exists():
        bundled_database = BASE_DIR / "instance" / "financeiro.db"
        if bundled_database.exists():
            shutil.copy2(bundled_database, database)

    return database


DATABASE = resolve_database_path()

CATEGORIES = {
    "receita": ["Salário", "Freelance", "Investimentos", "Vendas", "Outros"],
    "despesa": ["Alimentação", "Moradia", "Transporte", "Saúde", "Educação", "Lazer", "Assinaturas", "Outros"],
}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-financeiro-local")
    app.config["DATABASE"] = str(DATABASE)
    DATABASE.parent.mkdir(parents=True, exist_ok=True)

    @app.teardown_appcontext
    def close_db(_error: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.template_filter("brl")
    def brl(value: int | float) -> str:
        number = float(value or 0)
        formatted = f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"

    @app.template_filter("date_br")
    def date_br(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            return value

    @app.get("/")
    def dashboard():
        db = get_db(app)
        rows = db.execute(
            "SELECT id, tipo, descricao, valor_centavos, categoria, data FROM movimentacoes ORDER BY data DESC, id DESC"
        ).fetchall()
        transactions = [row_to_dict(row) for row in rows]

        receitas = sum(item["valor"] for item in transactions if item["tipo"] == "receita")
        despesas = sum(item["valor"] for item in transactions if item["tipo"] == "despesa")
        saldo = receitas - despesas
        taxa_economia = round((saldo / receitas) * 100) if receitas else 0

        today = date.today()
        monthly_data: list[dict[str, Any]] = []
        month_names = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
        for offset in range(5, -1, -1):
            month_index = today.year * 12 + today.month - 1 - offset
            year = month_index // 12
            month = month_index % 12 + 1
            prefix = f"{year:04d}-{month:02d}"
            month_items = [item for item in transactions if item["data"].startswith(prefix)]
            monthly_data.append({
                "label": month_names[month - 1],
                "receita": sum(item["valor"] for item in month_items if item["tipo"] == "receita"),
                "despesa": sum(item["valor"] for item in month_items if item["tipo"] == "despesa"),
            })

        category_totals: dict[str, float] = {}
        for item in transactions:
            if item["tipo"] == "despesa":
                category_totals[item["categoria"]] = category_totals.get(item["categoria"], 0) + item["valor"]
        category_data = [
            {"categoria": name, "valor": value}
            for name, value in sorted(category_totals.items(), key=lambda pair: pair[1], reverse=True)
        ]

        return render_template(
            "dashboard.html",
            active_page="dashboard",
            page_title="Visão geral",
            transactions=transactions,
            recent=transactions[:5],
            receitas=receitas,
            despesas=despesas,
            saldo=saldo,
            taxa_economia=taxa_economia,
            income_count=sum(1 for item in transactions if item["tipo"] == "receita"),
            expense_count=sum(1 for item in transactions if item["tipo"] == "despesa"),
            monthly_data=monthly_data,
            category_data=category_data,
        )

    @app.route("/cadastro", methods=["GET", "POST"])
    def cadastro():
        if request.method == "POST":
            data, errors = validate_transaction(request.form)
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template(
                    "cadastro.html",
                    active_page="cadastro",
                    page_title="Cadastrar movimentação",
                    form_data=request.form,
                    editing=False,
                    categories=CATEGORIES,
                ), 400

            db = get_db(app)
            db.execute(
                "INSERT INTO movimentacoes (tipo, descricao, valor_centavos, categoria, data) VALUES (?, ?, ?, ?, ?)",
                (data["tipo"], data["descricao"], data["valor_centavos"], data["categoria"], data["data"]),
            )
            db.commit()
            flash("Movimentação cadastrada com sucesso.", "success")
            return redirect(url_for("lista"))

        form_data = {"tipo": request.args.get("tipo", "receita"), "data": date.today().isoformat()}
        return render_template(
            "cadastro.html",
            active_page="cadastro",
            page_title="Cadastrar movimentação",
            form_data=form_data,
            editing=False,
            categories=CATEGORIES,
        )

    @app.route("/editar/<int:transaction_id>", methods=["GET", "POST"])
    def editar(transaction_id: int):
        db = get_db(app)
        row = db.execute("SELECT * FROM movimentacoes WHERE id = ?", (transaction_id,)).fetchone()
        if row is None:
            flash("Movimentação não encontrada.", "error")
            return redirect(url_for("lista"))

        if request.method == "POST":
            data, errors = validate_transaction(request.form)
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template(
                    "cadastro.html",
                    active_page="cadastro",
                    page_title="Editar movimentação",
                    form_data=request.form,
                    editing=True,
                    transaction_id=transaction_id,
                    categories=CATEGORIES,
                ), 400

            db.execute(
                "UPDATE movimentacoes SET tipo = ?, descricao = ?, valor_centavos = ?, categoria = ?, data = ? WHERE id = ?",
                (data["tipo"], data["descricao"], data["valor_centavos"], data["categoria"], data["data"], transaction_id),
            )
            db.commit()
            flash("Movimentação atualizada com sucesso.", "success")
            return redirect(url_for("lista"))

        form_data = {
            "tipo": row["tipo"],
            "descricao": row["descricao"],
            "valor": cents_to_input(row["valor_centavos"]),
            "categoria": row["categoria"],
            "data": row["data"],
        }
        return render_template(
            "cadastro.html",
            active_page="cadastro",
            page_title="Editar movimentação",
            form_data=form_data,
            editing=True,
            transaction_id=transaction_id,
            categories=CATEGORIES,
        )

    @app.post("/excluir/<int:transaction_id>")
    def excluir(transaction_id: int):
        db = get_db(app)
        result = db.execute("DELETE FROM movimentacoes WHERE id = ?", (transaction_id,))
        db.commit()
        if result.rowcount:
            flash("Movimentação excluída.", "success")
        else:
            flash("Movimentação não encontrada.", "error")
        return redirect(url_for("lista"))

    @app.get("/movimentacoes")
    def lista():
        search = request.args.get("busca", "").strip()
        tipo = request.args.get("tipo", "todos")
        categoria = request.args.get("categoria", "todas")
        month = request.args.get("mes", "")

        clauses: list[str] = []
        params: list[Any] = []
        if search:
            clauses.append("(descricao LIKE ? OR categoria LIKE ?)")
            term = f"%{search}%"
            params.extend([term, term])
        if tipo in {"receita", "despesa"}:
            clauses.append("tipo = ?")
            params.append(tipo)
        if categoria and categoria != "todas":
            clauses.append("categoria = ?")
            params.append(categoria)
        if month:
            clauses.append("substr(data, 1, 7) = ?")
            params.append(month)

        sql = "SELECT id, tipo, descricao, valor_centavos, categoria, data FROM movimentacoes"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY data DESC, id DESC"

        db = get_db(app)
        rows = db.execute(sql, params).fetchall()
        transactions = [row_to_dict(row) for row in rows]
        all_categories = sorted(set(CATEGORIES["receita"] + CATEGORIES["despesa"]))

        return render_template(
            "lista.html",
            active_page="lista",
            page_title="Movimentações",
            transactions=transactions,
            categories=all_categories,
            filters={"busca": search, "tipo": tipo, "categoria": categoria, "mes": month},
        )

    with app.app_context():
        init_db(app)

    return app


def get_db(app: Flask) -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db(app: Flask) -> None:
    db = get_db(app)
    schema = (BASE_DIR / "schema.sql").read_text(encoding="utf-8")
    db.executescript(schema)
    db.commit()


def parse_amount(raw: str) -> int | None:
    """Converte valores digitados para centavos inteiros."""
    text = (raw or "").strip()
    if not text or not re.fullmatch(r"\d[\d.,]*", text):
        return None

    normalized: str
    if "." in text and "," in text:
        if text.rfind(",") > text.rfind("."):
            if not re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d{1,2}", text):
                return None
            normalized = text.replace(".", "").replace(",", ".")
        else:
            if not re.fullmatch(r"\d{1,3}(?:,\d{3})+\.\d{1,2}", text):
                return None
            normalized = text.replace(",", "")
    elif "," in text:
        if text.count(",") == 1 and re.fullmatch(r"\d+,\d{1,2}", text):
            normalized = text.replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(?:,\d{3})+", text):
            normalized = text.replace(",", "")
        else:
            return None
    elif "." in text:
        if text.count(".") == 1 and re.fullmatch(r"\d+\.\d{1,2}", text):
            normalized = text
        elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
            normalized = text.replace(".", "")
        else:
            return None
    else:
        normalized = text

    try:
        value = Decimal(normalized)
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return int(value * 100)


def validate_transaction(form: Any) -> tuple[dict[str, Any], list[str]]:
    tipo = (form.get("tipo") or "").strip()
    descricao = (form.get("descricao") or "").strip()
    categoria = (form.get("categoria") or "").strip()
    data = (form.get("data") or "").strip()
    valor_centavos = parse_amount(form.get("valor") or "")
    errors: list[str] = []

    if tipo not in CATEGORIES:
        errors.append("Selecione um tipo válido.")
    if not descricao or len(descricao) > 60:
        errors.append("Informe uma descrição com até 60 caracteres.")
    if valor_centavos is None:
        errors.append("No campo Valor, use somente números, ponto ou vírgula e informe um valor maior que zero.")
    if tipo in CATEGORIES and categoria not in CATEGORIES[tipo]:
        errors.append("Selecione uma categoria válida para o tipo escolhido.")
    try:
        datetime.strptime(data, "%Y-%m-%d")
    except ValueError:
        errors.append("Informe uma data válida.")

    return {
        "tipo": tipo,
        "descricao": descricao,
        "valor_centavos": valor_centavos,
        "categoria": categoria,
        "data": data,
    }, errors


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "tipo": row["tipo"],
        "descricao": row["descricao"],
        "valor": row["valor_centavos"] / 100,
        "categoria": row["categoria"],
        "data": row["data"],
    }


def cents_to_input(cents: int) -> str:
    value = cents / 100
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


app = create_app()

if __name__ == "__main__":
    is_android = "ANDROID_ARGUMENT" in os.environ or "P4A_BOOTSTRAP" in os.environ
    app.run(host="127.0.0.1", port=5000, debug=not is_android, use_reloader=not is_android)
