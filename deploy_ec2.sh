#!/usr/bin/env bash
# ==============================================================================
# BUILDCORP ENTERPRISE — SCRIPT DE DESPLIEGUE AUTOMATIZADO EN AWS EC2
# Asignatura: Desarrollo Backend (Evaluación 3)
# Alumno: Rodrigo Nicolás Peña Sagredo
# ==============================================================================

set -e

echo ">>> [1/7] Actualizando paquetes del sistema..."
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv postgresql postgresql-contrib nginx libpq-dev git curl

echo ">>> [2/7] Configurando Servidor PostgreSQL nativo local..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

sudo -u postgres psql -c "DROP DATABASE IF EXISTS buildcorp_db;" || true
sudo -u postgres psql -c "DROP USER IF EXISTS buildcorp_user;" || true
sudo -u postgres psql -c "CREATE USER buildcorp_user WITH PASSWORD 'BuildCorp2026!';"
sudo -u postgres psql -c "CREATE DATABASE buildcorp_db OWNER buildcorp_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE buildcorp_db TO buildcorp_user;"
sudo -u postgres psql -c "ALTER USER buildcorp_user CREATEDB;"

echo ">>> [3/7] Preparando Entorno Virtual Python..."
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

if [ ! -d "env" ]; then
    python3 -m venv env
fi

./env/bin/pip install --upgrade pip
./env/bin/pip install -r requirements.txt gunicorn

echo ">>> [4/7] Configurando Variables de Entorno de Producción..."
cat <<EOF > .env
SECRET_KEY=buildcorp-production-secret-key-evaluacion3-inacap-2026
DEBUG=False
ALLOWED_HOSTS=*
DATABASE_URL=postgresql://buildcorp_user:BuildCorp2026!@127.0.0.1:5432/buildcorp_db
EOF

echo ">>> [5/7] Ejecutando Migraciones y Carga Inicial de Datos..."
./env/bin/python manage.py migrate --noinput
./env/bin/python manage.py collectstatic --noinput || true
./env/bin/python manage.py seed_buildcorp

echo ">>> [6/7] Creando Servicio Systemd para Gunicorn..."
sudo bash -c "cat <<EOF > /etc/systemd/system/buildcorp.service
[Unit]
Description=Gunicorn daemon para BuildCorp Enterprise
After=network.target postgresql.service

[Service]
User=$USER
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/env/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 buildcorp_core.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable buildcorp
sudo systemctl restart buildcorp

echo ">>> [7/7] Configurando Nginx como Proxy Inverso en Puerto 80..."
sudo bash -c "cat <<EOF > /etc/nginx/sites-available/buildcorp
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 20M;

    location /static/ {
        alias $APP_DIR/static_root/;
    }

    location /media/ {
        alias $APP_DIR/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }
}
EOF"

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/buildcorp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 || curl -s ifconfig.me || echo "IP_PUBLICA")

echo "=========================================================================="
echo ">>> DESPLIEGUE EXITOSO DE BUILDCORP EN AWS EC2!"
echo ">>> Acceso Web: http://${PUBLIC_IP}/"
echo ">>> Swagger API: http://${PUBLIC_IP}/api/docs/"
echo ">>> Django Admin: http://${PUBLIC_IP}/admin/"
echo ">>> Credenciales:"
echo "    - Superuser: admin / admin123"
echo "    - Bodeguero: bodega_central / bodega123"
echo "=========================================================================="
