#!/bin/sh
set -e

# Asegurar que el directorio de datos existe y tiene permisos para appuser
mkdir -p /home/appuser/app/data
chown -R appuser:appgroup /home/appuser/app/data 2>/dev/null || true
chmod -R 775 /home/appuser/app/data 2>/dev/null || true

# Ejecutar el comando final pasando la ejecucion a appuser
exec gosu appuser "$@"
