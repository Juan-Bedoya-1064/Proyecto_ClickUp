#!/usr/bin/env bash
# Espera a que MySQL esté listo y arranca la aplicación en el puerto 5000.
echo "→ Esperando a que MySQL arranque..."
until python -c "import pymysql; pymysql.connect(host='db', user='root', password='codespaces')" 2>/dev/null; do
  sleep 2
done
python run.py
