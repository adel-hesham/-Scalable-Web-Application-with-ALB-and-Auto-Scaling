#!/bin/bash
set -euxo pipefail

REPO_URL="https://github.com/<your-username>/<your-repo>.git"

dnf update -y
dnf install -y python3 python3-pip git

mkdir -p /opt/webapp
git clone "$REPO_URL" /opt/webapp/src
cp -r /opt/webapp/src/app /opt/webapp/app

python3 -m venv /opt/webapp/venv
/opt/webapp/venv/bin/pip install --upgrade pip
/opt/webapp/venv/bin/pip install -r /opt/webapp/app/requirements.txt

cp /opt/webapp/src/deploy/webapp.service /etc/systemd/system/webapp.service
systemctl daemon-reload
systemctl enable webapp
systemctl start webapp
