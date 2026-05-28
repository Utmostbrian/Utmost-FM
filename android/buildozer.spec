[app]

# Nombre visible de la app
title = UTMOST.FM

# Identidad del paquete
package.name = utmostfm
package.domain = org.utmostbrian

# Fuente
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

# Version
version = 2.0

# Dependencias Python (recipes de python-for-android)
# Fijar python3/hostpython3 evita que Buildozer 1.6 use Python 3.14 por defecto,
# que todavia rompe la compilacion de Kivy 2.3.x en python-for-android master.
# - kivy: UI
# - mutagen: metadatos/caratulas (pure python)
# - pyjnius: acceso a MediaPlayer / permisos Android
# - openssl + certifi: HTTPS para LRCLIB via urllib
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.0,mutagen,pyjnius,openssl,certifi

# Orientacion
orientation = portrait
fullscreen = 0

# Icono y presplash
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/icon.png

# Permisos Android
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,READ_MEDIA_AUDIO,WAKE_LOCK

# API / NDK
android.api = 33
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a

# Aceptar licencias del SDK automaticamente (para CI)
android.accept_sdk_license = True

# No usar AndroidX problematico; backend SDL2 por defecto
android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 0
