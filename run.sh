#!/usr/bin/env bash
# Arranca el bot creando el entorno virtual la primera vez.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --requirement requirements.txt

if [ ! -f .env ]; then
    echo "Falta el fichero .env. Copia .env.example y pega tu token de BotFather." >&2
    exit 1
fi

exec python -m bot
