#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/tte"
DJANGO_DIR="$APP_DIR/apps/django/app"
VENV_DIR="$APP_DIR/apps/django/venv"
SERVICE_NAME="django-app"

echo "[INFO] Deploying Django"

sudo apt update
sudo apt install -y python3 python3-venv python3-pip

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$APP_DIR/apps/django/requirements.txt"

cd "$DJANGO_DIR"

python manage.py collectstatic --noinput || true
python manage.py migrate || true

sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Django App
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$DJANGO_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python manage.py runserver 127.0.0.1:8001
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

sleep 3
curl -fsS http://127.0.0.1:8001 >/dev/null || true

echo "[INFO] Django deployed"