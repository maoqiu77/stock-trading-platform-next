#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

API_BIN="./api/stock-platform-api"
NODE_BIN="./runtime/node/node"
WEB_SERVER="./web/server.js"

if [[ ! -x "$API_BIN" ]]; then
  osascript -e 'display dialog "没有找到内置 API 程序。请重新下载 macOS 压缩包并完整解压。" buttons {"好"} default button "好"'
  exit 1
fi

if [[ ! -x "$NODE_BIN" ]]; then
  osascript -e 'display dialog "没有找到内置 Node.js。请重新下载 macOS 压缩包并完整解压。" buttons {"好"} default button "好"'
  exit 1
fi

if [[ ! -f "$WEB_SERVER" ]]; then
  osascript -e 'display dialog "没有找到网页端程序。请重新下载 macOS 压缩包并完整解压。" buttons {"好"} default button "好"'
  exit 1
fi

mkdir -p storage/local

export STOCK_APP_DATA_HOME="$PWD/storage/local"
export STOCK_APP_DB_PATH="$PWD/storage/local/app.db"
export STOCK_APP_TEMPLATE_HOME="$PWD/storage/templates"
export STOCK_APP_API_HOST="127.0.0.1"
export STOCK_APP_API_PORT="8000"
export BACKEND_API_URL="http://127.0.0.1:8000"
export HOSTNAME="0.0.0.0"
export PORT="3000"

"$API_BIN" > storage/local/api.log 2>&1 &
API_PID=$!
"$NODE_BIN" "$WEB_SERVER" > storage/local/web.log 2>&1 &
WEB_PID=$!

cleanup() {
  kill "$API_PID" "$WEB_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1 && \
     curl -fsS "http://127.0.0.1:3000/" >/dev/null 2>&1; then
    open "http://127.0.0.1:3000/"
    echo "股票交易平台已启动：http://127.0.0.1:3000/"
    echo "使用期间请不要关闭这个窗口。"
    read -r -p "按 Enter 关闭服务并退出。" _
    exit 0
  fi
  sleep 1
done

echo "启动超时。请查看 storage/local/api.log 和 storage/local/web.log。"
read -r -p "按 Enter 退出。" _
exit 1
