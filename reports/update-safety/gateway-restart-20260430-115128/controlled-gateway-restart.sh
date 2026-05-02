#!/usr/bin/env bash
set -u
DIR="/home/hanuman3310/hermes-agent/reports/update-safety/gateway-restart-20260430-115128"
LOG="$DIR/restart.log"
mkdir -p "$DIR"
exec >>"$LOG" 2>&1
printf '# controlled gateway restart %s\n' "$(TZ=Asia/Bangkok date --iso-8601=seconds)"
printf 'rollback_live_policy=%s\n' '/home/hanuman3310/.hermes/backups/live-policy-sync-20260430-093832.tar.gz'
printf 'rollback_live_protected=%s\n' '/home/hanuman3310/.hermes/backups/live-protected-sync-20260430-094226.tar.gz'
printf 'runtime_sync_manifest=%s\n' '/home/hanuman3310/hermes-agent/reports/runtime-sync/live-protected-sync-20260430-094226.json'

echo '## before status'
systemctl --user status hermes-gateway --no-pager -l | sed -n '1,50p' || true

echo '## restart'
systemctl --user restart hermes-gateway
RESTART_EC=$?
echo "restart_exit=$RESTART_EC"
if [ "$RESTART_EC" -ne 0 ]; then
  echo 'RESULT=RESTART_COMMAND_FAILED'
  exit "$RESTART_EC"
fi

echo '## wait active'
OK=0
for i in $(seq 1 30); do
  if systemctl --user is-active --quiet hermes-gateway; then
    OK=1
    echo "active_after_seconds=$i"
    break
  fi
  sleep 1
done
if [ "$OK" -ne 1 ]; then
  echo 'RESULT=SERVICE_NOT_ACTIVE_AFTER_WAIT'
  systemctl --user status hermes-gateway --no-pager -l | sed -n '1,120p' || true
  exit 2
fi

echo '## after status'
systemctl --user status hermes-gateway --no-pager -l | sed -n '1,80p' || true

echo '## hermes os status smoke'
set +e
timeout 45 hermes-os status | sed -n '1,120p'
HERMES_STATUS_EXIT=${PIPESTATUS[0]}
set -e
echo "hermes_os_status_exit=$HERMES_STATUS_EXIT"
if [ "$HERMES_STATUS_EXIT" -ne 0 ]; then
  echo 'RESULT=HERMES_OS_STATUS_FAILED'
  exit 3
fi

echo '## policy live smoke'
PY=/home/hanuman3310/.hermes/hermes-agent/venv/bin/python3
if [ ! -x "$PY" ]; then PY=python3; fi
(cd /home/hanuman3310/.hermes/hermes-agent && "$PY" -m tools.merged_policy_validator website/docs/reference/merged-hard-gate-policy.yaml)
POLICY_EXIT=$?
echo "policy_exit=$POLICY_EXIT"
if [ "$POLICY_EXIT" -ne 0 ]; then
  echo 'RESULT=POLICY_FAILED'
  exit 4
fi

echo '## process evidence'
ps -eo pid,ppid,stat,lstart,cmd | grep -E 'hermes.*gateway|gateway/run.py' | grep -v grep || true

echo 'RESULT=OK'
printf 'completed_at=%s\n' "$(TZ=Asia/Bangkok date --iso-8601=seconds)"
