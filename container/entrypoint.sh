#!/usr/bin/env bash
set -euo pipefail

export HOME="${HOME:-/home/easygs}"
EASYGS_HOME="${EASYGS_HOME:-$HOME/.easygs}"
CONFIG_PATH="$EASYGS_HOME/config.json"

require_mount() {
  local target="$1"
  local description="$2"
  local host_hint="$3"

  if ! awk -v target="$target" '$5 == target { found = 1 } END { exit found ? 0 : 1 }' /proc/self/mountinfo; then
    cat >&2 <<EOF
ERROR: EasyGS container requires a mounted ${description}.

Mount ${description} to:
  ${target}

Example:
  -v ${host_hint}:${target}
EOF
    exit 64
  fi
}

require_mount "$EASYGS_HOME" "easygs-home directory" "/path/to/easygs-home"
require_mount "/data" "data directory" "/path/to/data"

if [ "$(id -u)" = "0" ] && [ "${EASYGS_ENTRYPOINT_READY:-0}" != "1" ]; then
  home_uid="$(stat -c '%u' "$EASYGS_HOME")"
  home_gid="$(stat -c '%g' "$EASYGS_HOME")"
  data_uid="$(stat -c '%u' /data)"
  data_gid="$(stat -c '%g' /data)"

  target_uid="${EASYGS_UID:-$home_uid}"
  target_gid="${EASYGS_GID:-$home_gid}"

  if [ "$target_uid" = "0" ] && [ "$data_uid" != "0" ]; then
    target_uid="$data_uid"
  fi
  if [ "$target_gid" = "0" ] && [ "$data_gid" != "0" ]; then
    target_gid="$data_gid"
  fi

  if [ "$target_uid" = "0" ]; then
    target_uid="$(id -u easygs)"
  fi
  if [ "$target_gid" = "0" ]; then
    target_gid="$(id -g easygs)"
  fi

  current_gid="$(id -g easygs)"
  if [ "$target_gid" != "$current_gid" ]; then
    if getent group "$target_gid" >/dev/null; then
      target_group="$(getent group "$target_gid" | cut -d: -f1)"
      usermod -g "$target_group" easygs
    else
      groupmod -g "$target_gid" easygs
    fi
  fi

  current_uid="$(id -u easygs)"
  if [ "$target_uid" != "$current_uid" ]; then
    usermod -u "$target_uid" easygs
  fi

  chown "$target_uid:$target_gid" "$EASYGS_HOME" /data /home/easygs

  export EASYGS_ENTRYPOINT_READY=1
  exec gosu easygs "$0" "$@"
fi

mkdir -p \
  "$EASYGS_HOME/workspace" \
  "$EASYGS_HOME/resources" \
  "$EASYGS_HOME/history" \
  "$EASYGS_HOME/run" \
  "$EASYGS_HOME/cron" \
  /data

if [ ! -f "$CONFIG_PATH" ]; then
  cat > "$CONFIG_PATH" <<'JSON'
{
  "agents": {
    "defaults": {
      "workspace": "~/.easygs/workspace",
      "researchMode": true
    }
  },
  "channels": {
    "websocket": {
      "enabled": true,
      "host": "127.0.0.1",
      "port": 25685,
      "path": "/",
      "websocketRequiresToken": true,
      "allowFrom": ["*"]
    }
  }
}
JSON
fi

python - "$CONFIG_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path
from typing import Any


def env_part_to_json_key(part: str) -> str:
    pieces = part.lower().split("_")
    return pieces[0] + "".join(piece.title() for piece in pieces[1:])


def parse_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def merge_path(target: dict[str, Any], parts: list[str], value: Any) -> None:
    cursor = target
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
        if not isinstance(cursor, dict):
            raise TypeError(f"Cannot merge into non-object key: {part}")
    cursor[parts[-1]] = value


path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))

for key, raw_value in os.environ.items():
    if not key.startswith("EASYGS_") or "__" not in key:
        continue
    if raw_value == "":
        continue
    nested = key.removeprefix("EASYGS_").split("__")
    if not nested:
        continue
    json_path = [env_part_to_json_key(part) for part in nested]
    merge_path(data, json_path, parse_value(raw_value))

path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

if [ "$#" -eq 0 ]; then
  exec easygs gateway --research-mode
fi

exec "$@"
