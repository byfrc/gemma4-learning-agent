#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-/opt/gemma4_learning_agent}"
if [ -d "${PROJECT_ROOT}/app/backend" ]; then
  APP_DIR="${PROJECT_ROOT}/app"
else
  APP_DIR="${PROJECT_ROOT}"
fi

MODEL_ROOT="${PROJECT_ROOT}"
if [ ! -d "${MODEL_ROOT}/models" ] && [ -d "${APP_DIR}/models" ]; then
  MODEL_ROOT="${APP_DIR}"
fi
if [ ! -d "${MODEL_ROOT}/models" ] && [ "$(basename "${APP_DIR}")" = "app" ] && [ -d "${APP_DIR}/../models" ]; then
  MODEL_ROOT="${APP_DIR}/.."
fi

MODEL="${MODEL_ROOT}/models/gemma/gemma-4-12B-it"
ADAPTER="${MODEL_ROOT}/models/lora/gemma4_learning_v5/adapter"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate gemma4_vllm

ARGS=(
  "${MODEL}"
  --host 0.0.0.0
  --port 8001
  --dtype bfloat16
  --gpu-memory-utilization 0.88
  --max-model-len 8192
)

if [ -d "${ADAPTER}" ]; then
  echo "Loading LoRA Adapter: ${ADAPTER}"
  ARGS+=(--enable-lora --lora-modules "gemma4-learning=${ADAPTER}")
else
  echo "Adapter not found. Starting base Gemma4-12B."
fi

vllm serve "${ARGS[@]}"
