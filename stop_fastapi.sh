#!/bin/bash
# Stop CosyVoice FastAPI server started by start_fastapi.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${SCRIPT_DIR}/fastapi.pid"
PORT="${PORT:-56786}"

is_running() {
    local pid="$1"
    kill -0 "$pid" 2>/dev/null
}

stop_pid() {
    local pid="$1"
    echo "Stopping FastAPI (pid=${pid})..."
    kill "${pid}" 2>/dev/null || true

    for _ in $(seq 1 30); do
        if ! is_running "${pid}"; then
            echo "FastAPI stopped"
            return 0
        fi
        sleep 1
    done

    echo "Force killing pid=${pid}..."
    kill -9 "${pid}" 2>/dev/null || true
    sleep 1
}

stopped=0

if [[ -f "${PID_FILE}" ]]; then
    pid="$(cat "${PID_FILE}")"
    if is_running "${pid}"; then
        stop_pid "${pid}"
        stopped=1
    else
        echo "Stale pid file removed (pid=${pid} not running)"
    fi
    rm -f "${PID_FILE}"
fi

if [[ "${stopped}" -eq 0 ]] && command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti tcp:"${PORT}" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "${pids}" ]]; then
        for pid in ${pids}; do
            stop_pid "${pid}"
            stopped=1
        done
    fi
fi

if [[ "${stopped}" -eq 0 ]]; then
    echo "FastAPI is not running (port=${PORT})"
    exit 0
fi

echo "Done"
