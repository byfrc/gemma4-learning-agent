#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/root/autodl-tmp/gemma4_learning_agent}"

if [ -d "${PROJECT_ROOT}/app/backend" ]; then
  PROJECT_DIR="${PROJECT_ROOT}/app"
elif [ -d "${PROJECT_ROOT}/backend" ]; then
  PROJECT_DIR="${PROJECT_ROOT}"
else
  for candidate in \
    /root/autodl-tmp/gemma4_learning_agent/app \
    /root/autodl-tmp/gemma4_learning_agent \
    /opt/gemma4_learning_agent/app \
    /opt/gemma4_learning_agent
  do
    if [ -d "${candidate}/backend" ]; then
      PROJECT_DIR="${candidate}"
      break
    fi
  done
fi

if [ -z "${PROJECT_DIR:-}" ] || [ ! -d "${PROJECT_DIR}/backend" ]; then
  echo "找不到项目目录。请传入正确路径，例如："
  echo "  bash deploy/06_start_autodl.sh /root/autodl-tmp/gemma4_learning_agent"
  exit 1
fi

MODEL_ROOT="${PROJECT_ROOT}"
if [ ! -d "${MODEL_ROOT}/models" ] && [ -d "${PROJECT_DIR}/models" ]; then
  MODEL_ROOT="${PROJECT_DIR}"
fi
if [ ! -d "${MODEL_ROOT}/models" ] && [ "$(basename "${PROJECT_DIR}")" = "app" ] && [ -d "${PROJECT_DIR}/../models" ]; then
  MODEL_ROOT="${PROJECT_DIR}/.."
fi

FRONTEND_DIR="/var/www/gemma4_learning_agent"
VLLM_LOG="/root/autodl-tmp/vllm.log"
API_LOG="/root/autodl-tmp/api.log"

source /root/miniconda3/etc/profile.d/conda.sh

echo "[1/5] 同步前端到 ${FRONTEND_DIR}"
mkdir -p "${FRONTEND_DIR}"
cp -r "${PROJECT_DIR}/frontend/." "${FRONTEND_DIR}/"
chown -R www-data:www-data "${FRONTEND_DIR}" || true

echo "[2/5] 清理旧服务"
pkill -f "uvicorn app.main:app" || true
pkill -f "vllm serve" || true
sleep 2

echo "[3/5] 启动 Nginx"
nginx -t
if pgrep -x nginx >/dev/null 2>&1; then
  nginx -s reload
else
  nginx
fi

echo "[4/5] 启动 vLLM"
conda activate gemma4_vllm
nohup bash "${PROJECT_DIR}/deploy/05_start_vllm_with_lora.sh" "${MODEL_ROOT}" > "${VLLM_LOG}" 2>&1 &

for i in $(seq 1 180); do
  if curl -fsS --max-time 3 http://127.0.0.1:8001/v1/models >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS --max-time 3 http://127.0.0.1:8001/v1/models >/dev/null 2>&1; then
  echo "vLLM 启动超时，请查看 ${VLLM_LOG}"
  tail -n 80 "${VLLM_LOG}" || true
  exit 1
fi

echo "[5/5] 启动 FastAPI"
nohup bash "${PROJECT_DIR}/deploy/04_start_dev.sh" "${PROJECT_ROOT}" > "${API_LOG}" 2>&1 &

for i in $(seq 1 120); do
  if curl -fsS --max-time 3 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS --max-time 3 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  echo "FastAPI 启动超时，请查看 ${API_LOG}"
  tail -n 80 "${API_LOG}" || true
  exit 1
fi

echo "启动完成。"
echo "  前端:  http://127.0.0.1/"
echo "  API:   http://127.0.0.1:8000/api/health"
echo "  模型:  http://127.0.0.1:8001/v1/models"
