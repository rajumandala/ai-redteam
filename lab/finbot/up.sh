#!/bin/sh
# Start the pinned FinBot CTF locally, locked down. Run from anywhere.
# FinBot is intentionally vulnerable and has RCE challenges, so it runs in a container:
# reachable from this machine only, no Linux capabilities, capped memory and processes.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
sha=$(awk '$1=="finbot-ctf"{print $3}' "$repo/targets.lock")
image="finbot-ctf:$(echo "$sha" | cut -c1-7)"
envfile="$repo/targets/finbot.env"

if [ ! -f "$envfile" ]; then
  key=$(grep -s '^FINBOT_OPENAI_API_KEY=' "$repo/.env" | cut -d= -f2- || true)
  umask 077
  sed -e "s|^SECRET_KEY=.*|SECRET_KEY=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')|" \
      -e "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${key}|" \
      -e "s|^DEBUG=.*|DEBUG=false|" \
      "$repo/targets/finbot-ctf/.env.example" > "$envfile"
fi

docker network inspect finbot-net >/dev/null 2>&1 || docker network create finbot-net >/dev/null
docker run -d --name finbot-redis --network finbot-net --user redis \
  --cap-drop ALL --security-opt no-new-privileges --memory 256m \
  redis:7-alpine >/dev/null
docker run -d --name finbot-app --network finbot-net \
  -p 127.0.0.1:8000:8000 --env-file "$envfile" \
  -e REDIS_URL=redis://finbot-redis:6379 -e DATABASE_URL=sqlite://data/finbot.db \
  --cap-drop ALL --security-opt no-new-privileges --memory 2g --pids-limit 512 \
  -v finbot_data:/app/data -v finbot_uploads:/app/uploads \
  "$image" >/dev/null
echo "FinBot $image at http://127.0.0.1:8000 (logs: docker logs -f finbot-app)"
