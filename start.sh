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
TAIL_PID=""
cleanup() {
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true
  [[ -n "$INSPECTOR_PID" ]] && kill "$INSPECTOR_PID" 2>/dev/null || true
  [[ -n "$TAIL_PID" ]] && kill "$TAIL_PID" 2>/dev/null || true
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

  INSPECTOR_PORT="${CLIENT_PORT:-6274}"
  INSPECTOR_LOG="$(mktemp -t pikppo-mcp-inspector)"

  echo "[inspector] 启动中..."
  # 用 Python pty.spawn 给 Inspector 假装一个 TTY, 否则 Node 检测到非 TTY 会块缓冲
  # stdout, 拿不到它实时生成的 proxy token。pty 输出同时写日志文件。
  "$PYTHON" -u -c "
import os, pty, sys
log = open(sys.argv[1], 'wb', buffering=0)
def read_cb(fd):
    data = os.read(fd, 1024)
    log.write(data)
    return data
pty.spawn(['npx', '-y', '@modelcontextprotocol/inspector'], read_cb)
" "$INSPECTOR_LOG" </dev/null >/dev/null 2>&1 &
  INSPECTOR_PID=$!
  tail -f "$INSPECTOR_LOG" &
  TAIL_PID=$!

  # 等 Inspector 打印它自己生成的 token (它忽略 MCP_PROXY_AUTH_TOKEN 这个 env var)
  # `|| true` 避免 grep 未匹配时 errexit 把整个脚本干掉
  PROXY_TOKEN=""
  for _ in $(seq 1 60); do
    PROXY_TOKEN="$(grep -oE 'MCP_PROXY_AUTH_TOKEN=[0-9a-fA-F]+' "$INSPECTOR_LOG" 2>/dev/null | head -1 | cut -d= -f2 || true)"
    [[ -n "$PROXY_TOKEN" ]] && break
    sleep 0.5
  done

  if [[ -z "$PROXY_TOKEN" ]]; then
    echo "[inspector] 警告: 未能从 Inspector 输出中提取 proxy token, 请查看上方日志手动复制" >&2
  fi

  if [[ -n "$MCP_URL" ]]; then
    ENC_URL="$(url_encode "$MCP_URL")"
    INSPECTOR_URL="http://127.0.0.1:${INSPECTOR_PORT}/?transport=${TRANSPORT}&serverUrl=${ENC_URL}"
    [[ -n "$PROXY_TOKEN" ]] && INSPECTOR_URL="${INSPECTOR_URL}&MCP_PROXY_AUTH_TOKEN=${PROXY_TOKEN}"
  else
    INSPECTOR_URL="http://127.0.0.1:${INSPECTOR_PORT}/"
    [[ -n "$PROXY_TOKEN" ]] && INSPECTOR_URL="${INSPECTOR_URL}?MCP_PROXY_AUTH_TOKEN=${PROXY_TOKEN}"
  fi

  echo
  echo "================ 连接信息 ================"
  echo "MCP server:   ${MCP_URL:-stdio}"
  echo "Proxy token:  ${PROXY_TOKEN:-<未获取到, 见上方 Inspector 日志>}"
  echo "Inspector:    $INSPECTOR_URL"
  echo "==========================================="
  echo

  if [[ "$OPEN_BROWSER" -eq 1 && -n "$PROXY_TOKEN" ]]; then
    if command -v open >/dev/null 2>&1; then
      open "$INSPECTOR_URL"
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$INSPECTOR_URL"
    fi
  fi

  wait
else
  exec "$PYTHON" -m app --transport "$TRANSPORT" --host "$HOST" --port "$PORT"
fi
