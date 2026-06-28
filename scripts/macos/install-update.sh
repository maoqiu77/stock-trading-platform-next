#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT=""
PACKAGE_ZIP=""
BACKUP_ZIP=""
LAUNCHER_PATH=""
API_PID=""
WEB_PID=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-root)
      INSTALL_ROOT="$2"
      shift 2
      ;;
    --package-zip)
      PACKAGE_ZIP="$2"
      shift 2
      ;;
    --backup-zip)
      BACKUP_ZIP="$2"
      shift 2
      ;;
    --launcher-path)
      LAUNCHER_PATH="$2"
      shift 2
      ;;
    --api-pid)
      API_PID="$2"
      shift 2
      ;;
    --web-pid)
      WEB_PID="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$INSTALL_ROOT" || -z "$PACKAGE_ZIP" || -z "$LAUNCHER_PATH" ]]; then
  echo "Missing required update arguments." >&2
  exit 2
fi

echo "Install root: $INSTALL_ROOT"
echo "Package zip: $PACKAGE_ZIP"
echo "Backup zip: $BACKUP_ZIP"
echo "Launcher: $LAUNCHER_PATH"
echo "Preserve: $INSTALL_ROOT/storage/local"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run only. No files will be changed."
  exit 0
fi

sleep 2

stop_pid() {
  local pid="$1"
  if [[ "$pid" =~ ^[0-9]+$ ]]; then
    kill "$pid" >/dev/null 2>&1 || true
  fi
}

stop_pid "$WEB_PID"
stop_pid "$API_PID"
sleep 1

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/stock-platform-update.XXXXXX")"
cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

unzip -q "$PACKAGE_ZIP" -d "$WORK_DIR"
shopt -s nullglob
entries=("$WORK_DIR"/*)
SOURCE_ROOT="$WORK_DIR"
if [[ "${#entries[@]}" -eq 1 && -d "${entries[0]}" ]]; then
  SOURCE_ROOT="${entries[0]}"
fi

if [[ ! -f "$SOURCE_ROOT/release.json" ]]; then
  echo "The downloaded package is missing release.json." >&2
  exit 1
fi

replace_path() {
  local name="$1"
  rm -rf "$INSTALL_ROOT/$name"
  cp -R "$SOURCE_ROOT/$name" "$INSTALL_ROOT/$name"
}

for item in "$SOURCE_ROOT"/*; do
  name="$(basename "$item")"
  if [[ "$name" == "storage" ]]; then
    mkdir -p "$INSTALL_ROOT/storage"
    if [[ -d "$SOURCE_ROOT/storage/templates" ]]; then
      rm -rf "$INSTALL_ROOT/storage/templates"
      cp -R "$SOURCE_ROOT/storage/templates" "$INSTALL_ROOT/storage/templates"
    fi
    continue
  fi
  replace_path "$name"
done

chmod +x "$INSTALL_ROOT/api/stock-platform-api" >/dev/null 2>&1 || true
chmod +x "$INSTALL_ROOT/runtime/node/node" >/dev/null 2>&1 || true
chmod +x "$INSTALL_ROOT/启动股票交易平台.command" >/dev/null 2>&1 || true
chmod +x "$INSTALL_ROOT/updater/install-update.sh" >/dev/null 2>&1 || true

if [[ -f "$LAUNCHER_PATH" ]]; then
  open "$LAUNCHER_PATH"
else
  open "$INSTALL_ROOT/启动股票交易平台.command"
fi
