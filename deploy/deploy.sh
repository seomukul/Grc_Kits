#!/usr/bin/env bash
# Pull the latest code and restart. Run on the server as the grckits user: ./deploy/deploy.sh
set -euo pipefail
cd /srv/grckits/app
export DJANGO_SETTINGS_MODULE=config.settings.prod
PY=/srv/grckits/venv/bin/python

git pull --ff-only
/srv/grckits/venv/bin/pip install -q -r requirements.txt
$PY manage.py migrate --noinput
$PY manage.py tailwind build
$PY manage.py collectstatic --noinput
$PY manage.py check --deploy
sudo systemctl reload grckits
echo "Deployed $(git rev-parse --short HEAD)"
