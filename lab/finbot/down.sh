#!/bin/sh
# Stop FinBot. Add --wipe to delete its data volumes as well (a fresh CTF next time).
docker rm -f finbot-app finbot-redis >/dev/null 2>&1 || true
if [ "${1:-}" = "--wipe" ]; then
  docker volume rm finbot_data finbot_uploads >/dev/null 2>&1 || true
fi
echo "FinBot stopped"
