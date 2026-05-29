#!/usr/bin/env bash
# pikppo-mcp 一键启动脚本
# 用法:
#   ./start.sh                  # 启动 server (streamable-http, 默认 :8000)
#   ./start.sh --inspect        # 同时启动 MCP Inspector 并自动预填连接参数
#   ./start.sh --transport sse  # 切换 transport (stdio | sse | streamable-http)
#   ./start.sh --port 9000      # 自定义端口
#   ./start.sh --no-open        # --inspect 时不自动打开浏览器

set -euo pipefail

cd "$(dirname "$0")"

TRANSPORT="streamable-http"
HOST="127.0.0.1"
PORT="8000"
INSPECT=0
OPEN_BROWSER=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --inspect) INSPECT=1; shift ;;
    --no-open) OPEN_BROWSER=0; shift ;;
    --transport) TRANSPORT="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" -c "import mcp, aiosqlite" 2>/dev/null; then
  echo "[setup] 安装依赖..."
  "$PYTHON" -m pip install -e ".[dev]"
fi

mkdir -p data

SERVER_PID=""
INSPECTOR_PID=""
cleanup() {
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
  [[ -n "$INSPECTOR_PID" ]] && kill "$INSPECTOR_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

url_encode() {
  "$PYTHON" -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=''))" "$1"
}

if [[ "$INSPECT" -eq 1 ]]; then
  echo "[server] $TRANSPORT 启动于 $HOST:$PORT"
  "$PYTHON" -m app --transport "$TRANSPORT" --host "$HOST" --port "$PORT" &
  SERVER_PID=$!

  case "$TRANSPORT" in
    sse)             MCP_URL="http://$HOST:$PORT/sse" ;;
    streamable-http) MCP_URL="http://$HOST:$PORT/mcp" ;;
    stdio)           MCP_URL="" ;;
  esac

  # 固定 proxy token, 避免 Inspector 随机生成后我们拿不到
  PROXY_TOKEN="${MCP_PROXY_AUTH_TOKEN:-pikppo-dev-$(date +%s)}"
  export MCP_PROXY_AUTH_TOKEN="$PROXY_TOKEN"

  INSPECTOR_PORT="${CLIENT_PORT:-6274}"

  if [[ -n "$MCP_URL" ]]; then
    ENC_URL="$(url_encode "$MCP_URL")"
    INSPECTOR_URL="http://127.0.0.1:${INSPECTOR_PORT}/?transport=${TRANSPORT}&serverUrl=${ENC_URL}&MCP_PROXY_AUTH_TOKEN=${PROXY_TOKEN}"
  else
    INSPECTOR_URL="http://127.0.0.1:${INSPECTOR_PORT}/?MCP_PROXY_AUTH_TOKEN=${PROXY_TOKEN}"
  fi

  echo "[inspector] 启动中..."
  echo "[inspector] 连接目标: ${MCP_URL:-stdio}"
  echo "[inspector] 打开此 URL 即可（已预填 transport / serverUrl / token）:"
  echo "            $INSPECTOR_URL"

  npx -y @modelcontextprotocol/inspector >/dev/null 2>&1 &
  INSPECTOR_PID=$!

  if [[ "$OPEN_BROWSER" -eq 1 ]]; then
    ( sleep 2
      if command -v open >/dev/null 2>&1; then
        open "$INSPECTOR_URL"
      elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$INSPECTOR_URL"
      fi
    ) &
  fi

  wait
else
  exec "$PYTHON" -m app --transport "$TRANSPORT" --host "$HOST" --port "$PORT"
fi
