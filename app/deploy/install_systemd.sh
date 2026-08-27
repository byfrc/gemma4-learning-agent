#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${1:-/opt/gemma4_learning_agent}"
if [ ! -d "${PROJECT_DIR}/backend" ] && [ -d "${PROJECT_DIR}/app/backend" ]; then
  PROJECT_DIR="${PROJECT_DIR}/app"
fi

cp "${PROJECT_DIR}/deploy/gemma4-learning-api.service" /etc/systemd/system/
cp "${PROJECT_DIR}/deploy/gemma4-vllm.service" /etc/systemd/system/
sed -i "s#/opt/gemma4_learning_agent#${PROJECT_DIR}#g" /etc/systemd/system/gemma4-learning-api.service
sed -i "s#/opt/gemma4_learning_agent#${PROJECT_DIR}#g" /etc/systemd/system/gemma4-vllm.service

cp "${PROJECT_DIR}/deploy/nginx.conf" /etc/nginx/sites-available/gemma4_learning
sed -i "s#/opt/gemma4_learning_agent#${PROJECT_DIR}#g" /etc/nginx/sites-available/gemma4_learning
ln -sf /etc/nginx/sites-available/gemma4_learning /etc/nginx/sites-enabled/gemma4_learning
rm -f /etc/nginx/sites-enabled/default

FRONTEND_DIR="/var/www/gemma4_learning_agent"
mkdir -p "${FRONTEND_DIR}"
cp -r "${PROJECT_DIR}/frontend/." "${FRONTEND_DIR}/"
chown -R www-data:www-data "${FRONTEND_DIR}" || true

systemctl daemon-reload
nginx -t
systemctl restart nginx
systemctl enable gemma4-learning-api
echo "Systemd installed. Start with:"
echo "  systemctl start gemma4-learning-api"
echo "  systemctl start gemma4-vllm"
