#!/usr/bin/env bash
set -euo pipefail

if ! command -v buildozer >/dev/null 2>&1; then
  echo 'Buildozer não encontrado. Instale as dependências descritas em BUILD_ANDROID.md.' >&2
  exit 1
fi

export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export PATH="$JAVA_HOME/bin:$PATH"

buildozer -v android debug

echo
echo 'APK(s) gerado(s):'
find bin -maxdepth 1 -type f -name '*.apk' -print
