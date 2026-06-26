#!/bin/bash
# Start CosyVoice FastAPI server in background (nohup).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"
FASTAPI_DIR="${REPO_ROOT}/runtime/python/fastapi"

PID_FILE="${SCRIPT_DIR}/fastapi.pid"
LOG_FILE="${SCRIPT_DIR}/fastapi.log"

PORT="${PORT:-56786}"
MODEL_DIR="${MODEL_DIR:-${REPO_ROOT}/pretrained_models/CosyVoice-300M}"
CONDA_ENV="${CONDA_ENV:-tts}"

is_running() {
    local pid="$1"
    kill -0 "$pid" 2>/dev/null
}

if [[ -f "${PID_FILE}" ]]; then
    old_pid="$(cat "${PID_FILE}")"
    if is_running "${old_pid}"; then
        echo "FastAPI already running in background (pid=${old_pid}, port=${PORT})"
        echo "Log: ${LOG_FILE}"
        exit 0
    fi
    rm -f "${PID_FILE}"
fi

if [[ ! -d "${MODEL_DIR}" ]]; then
    echo "Model directory not found: ${MODEL_DIR}"
    exit 1
fi

if [[ -f "${HOME}/miniforge3/etc/profile.d/conda.sh" ]]; then
    # shellcheck disable=SC1091
    source "${HOME}/miniforge3/etc/profile.d/conda.sh"
elif command -v conda >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
else
    echo "conda not found; please run this script in bash with conda initialized"
    exit 1
fi
conda activate "${CONDA_ENV}"

export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/third_party/Matcha-TTS:${PYTHONPATH:-}"

cd "${FASTAPI_DIR}"
nohup python3 server.py \
    --port "${PORT}" \
    --model_dir "${MODEL_DIR}" \
    > "${LOG_FILE}" 2>&1 &

echo $! > "${PID_FILE}"
sleep 1

pid="$(cat "${PID_FILE}")"
if ! is_running "${pid}"; then
    echo "Failed to start FastAPI. Check log: ${LOG_FILE}"
    tail -n 20 "${LOG_FILE}" || true
    rm -f "${PID_FILE}"
    exit 1
fi

echo "CosyVoice FastAPI started in background"
echo "  pid:       ${pid}"
echo "  port:      ${PORT}"
echo "  model_dir: ${MODEL_DIR}"
echo "  conda env: ${CONDA_ENV}"
echo "  log:       ${LOG_FILE}"
echo "  docs:      http://0.0.0.0:${PORT}/docs"
echo "Stop with: ${SCRIPT_DIR}/stop_fastapi.sh"
