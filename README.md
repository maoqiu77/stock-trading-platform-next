# 股票交易平台 Next

一个新的独立项目骨架，当前 Streamlit 项目不参与改动。

## 技术栈

- `apps/web`: Next.js + TypeScript + shadcn/ui + Tailwind CSS v4
- `apps/api`: FastAPI + SQLite + yfinance 可选行情源
- `storage/templates`: 可提交到 GitHub 的公开示例数据
- `storage/local`: 本地私有数据目录，已被 `.gitignore` 忽略

## 第一版范围

- 日K、周K、月K、1日分时、五日分时
- 自选股列表
- 行情报价接口
- 本地私有数据和公开模板数据分离

## 本地运行

```bash
cd /Users/yaochengzhi/Documents/股票交易平台-next
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
npm --prefix apps/web install
```

两个终端分别启动：

```bash
npm run dev:api
npm run dev:web
```

默认访问：

- Web: http://localhost:3000
- API: http://127.0.0.1:8000/health

手机或同一局域网设备访问时，用电脑的局域网地址打开 Web 端，例如：

```text
http://<电脑局域网 IP>:3000
```

前端默认通过同源 `/api` 访问后端，Next.js 会代理到本机 FastAPI。也可以设置 `BACKEND_API_URL` 覆盖代理目标。

## Windows 一键启动

Release 包会包含 `Start-StockPlatform.ps1`，并通过 GitHub Actions 构建
`StockTradingPlatform-Launcher.exe`。

在 Windows 上把 release zip 解压后，把 `.exe` 放在项目根目录并双击。启动器会：

- 检查 Node.js、npm、Python；缺失时优先用 `winget` 安装。
- 创建 `.venv` 并安装 `apps/api/requirements.txt`。
- 执行 `npm --prefix apps/web install`。
- 启动 FastAPI 和 Next.js，然后打开 `http://127.0.0.1:3000/`。

如果电脑没有 `winget` 或安装权限，启动器会打开对应下载页，需要手动安装 Node.js LTS 和 Python 3。

## 隐私边界

可以提交到 GitHub：

- `apps/**`
- `storage/templates/**`
- `docs/**`
- `.env.example`

不能提交：

- `storage/local/**`
- `.env`、`.env.local`、`.env.*`
- `*.db`、`*.sqlite`
- `config.local.*`

提交前可运行：

```bash
npm run check:public-safety
npm run check:release-readiness
```

创建公开源码压缩包：

```bash
npm run release:archive -- v0.1.0
```
