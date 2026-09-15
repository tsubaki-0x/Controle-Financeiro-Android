[app]
title = Controle Financeiro
package.name = controlefinanceiro
package.domain = br.local
version = 1.0.0

source.dir = .
source.include_exts = py,html,css,js,sql,db,png,jpg,jpeg,svg,json,txt,md
source.exclude_dirs = .git,__pycache__,.venv,venv,.buildozer,bin

# O bootstrap WebView do python-for-android executa o Flask no próprio aparelho
# e abre http://127.0.0.1:5000 dentro do APK.
requirements = python3,flask
p4a.bootstrap = webview
p4a.port = 5000
p4a.branch = develop

# INTERNET é necessária para a WebView acessar o servidor HTTP local.
android.permissions = INTERNET

android.api = 36
android.minapi = 24
android.ndk_api = 24
android.ndk = 28c

android.archs = arm64-v8a

android.accept_sdk_license = True

android.debug_artifact = apk
android.release_artifact = aab

fullscreen = 0
orientation = all

[buildozer]
log_level = 2
warn_on_root = 1
