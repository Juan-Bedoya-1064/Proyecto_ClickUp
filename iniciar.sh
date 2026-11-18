#!/usr/bin/env sh
# Sprint 1 · Acceso y usuarios — arranque en macOS / Linux
# Requiere MySQL o MariaDB encendido (XAMPP, Homebrew, apt...).
set -e
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
[ -f .env ] || cp .env.example .env
exec .venv/bin/python run.py
