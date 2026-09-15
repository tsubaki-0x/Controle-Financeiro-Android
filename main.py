"""Entrada usada pelo APK Android (python-for-android WebView bootstrap)."""
from app import app


if __name__ == "__main__":
    # O WebView do python-for-android espera o site local nesta porta.
    # debug/reloader precisam permanecer desativados no Android.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True,
    )
