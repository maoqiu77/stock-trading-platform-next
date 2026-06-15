#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

API_URL="http://127.0.0.1:8000/health"
WEB_URL="http://127.0.0.1:3000/"

echo "正在启动股票交易平台..."
echo "项目目录：$PWD"

if ! command -v python3 >/dev/null 2>&1; then
  echo "没有找到 python3。请先安装 Python 3。"
  read -r -p "按 Enter 退出。" _
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "没有找到 Node.js。请先安装 Node.js。"
  read -r -p "按 Enter 退出。" _
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "正在准备后端 Python 环境，第一次运行会稍慢..."
  python3 -m venv .venv
  .venv/bin/pip install -r apps/api/requirements.txt
fi

if [[ ! -d "apps/web/node_modules" ]]; then
  echo "正在准备网页端依赖，第一次运行会稍慢..."
  npm --prefix apps/web ci
fi

if [[ ! -f "apps/web/.next/standalone/server.js" ]]; then
  echo "正在构建网页端，第一次运行会稍慢..."
  npm --prefix apps/web run build
fi

rm -rf apps/web/.next/standalone/.next/static apps/web/.next/standalone/public
cp -R apps/web/.next/static apps/web/.next/standalone/.next/static
cp -R apps/web/public apps/web/.next/standalone/public

mkdir -p storage/local

export STOCK_APP_DATA_HOME="$PWD/storage/local"
export STOCK_APP_DB_PATH="$PWD/storage/local/app.db"
export STOCK_APP_TEMPLATE_HOME="$PWD/storage/templates"
export BACKEND_API_URL="http://127.0.0.1:8000"

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${WEB_PID:-}" ]]; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if curl -fsS "$API_URL" >/dev/null 2>&1 && curl -fsS "$WEB_URL" >/dev/null 2>&1; then
  echo "平台已经在运行，正在打开浏览器..."
  open "$WEB_URL"
  exit 0
fi

echo "正在启动后端服务..."
.venv/bin/python -m uvicorn app.main:app \
  --reload \
  --reload-dir apps/api \
  --app-dir apps/api \
  --host 127.0.0.1 \
  --port 8000 \
  > storage/local/api.log 2>&1 &
API_PID=$!

echo "正在启动网页端服务..."
HOSTNAME=127.0.0.1 PORT=3000 node apps/web/.next/standalone/server.js \
  > storage/local/web.log 2>&1 &
WEB_PID=$!

for _ in $(seq 1 90); do
  if curl -fsS "$API_URL" >/dev/null 2>&1 && curl -fsS "$WEB_URL" >/dev/null 2>&1; then
    echo "启动完成：$WEB_URL"
    open "$WEB_URL"
    echo "使用期间请不要关闭这个窗口。"
    read -r -p "按 Enter 关闭平台并退出。" _
    exit 0
  fi
  sleep 1
done

echo "启动超时。"
echo "后端日志：$PWD/storage/local/api.log"
echo "网页日志：$PWD/storage/local/web.log"
read -r -p "按 Enter 退出。" _
exit 1
