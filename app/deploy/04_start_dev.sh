#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-/opt/gemma4_learning_agent}"
if [ -d "${PROJECT_ROOT}/app/backend" ]; then
  PROJECT_DIR="${PROJECT_ROOT}/app"
else
  PROJECT_DIR="${PROJECT_ROOT}"
fi
source /root/miniconda3/etc/profile.d/conda.sh
conda activate gemma4_web
cd "${PROJECT_DIR}/backend"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
