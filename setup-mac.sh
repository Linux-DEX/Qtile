#!/usr/bin/env bash
# Run on THIS Mac — adds `ssh arch` and installs your pubkey on the Arch laptop.
set -euo pipefail

REMOTE_USER="${REMOTE_USER:-linuxdex}"
REMOTE_HOST="${REMOTE_HOST:-archlinux.local}"
ALIAS="${ALIAS:-arch}"
KEY="${KEY:-$HOME/.ssh/id_ed25519}"
CONFIG="${CONFIG:-$HOME/.ssh/config}"

if [[ ! -f "${KEY}" ]]; then
  echo "No key at ${KEY}. Generate one first:"
  echo "  ssh-keygen -t ed25519 -f ${KEY} -C \"\$(whoami)@\$(hostname)\""
  exit 1
fi

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [[ -f "$CONFIG" ]] && grep -qE "^Host[[:space:]]+${ALIAS}([[:space:]]|$)" "$CONFIG"; then
  echo "Host '${ALIAS}' already exists in ${CONFIG} — skipping config edit."
else
  cat >> "$CONFIG" << EOF

Host ${ALIAS}
    HostName ${REMOTE_HOST}
    User ${REMOTE_USER}
    IdentityFile ${KEY}
    IdentitiesOnly yes
EOF
  echo "Added Host ${ALIAS} -> ${REMOTE_USER}@${REMOTE_HOST}"
fi

chmod 600 "$CONFIG" 2>/dev/null || true

echo "Copying pubkey to ${REMOTE_USER}@${REMOTE_HOST} ..."
echo "(enter password once if prompted)"
ssh-copy-id -i "${KEY}.pub" "${REMOTE_USER}@${REMOTE_HOST}"

echo
echo "Testing: ssh ${ALIAS}"
ssh -o BatchMode=yes -o ConnectTimeout=8 "${ALIAS}" "echo OK; whoami; hostname"
echo
echo "Done. Use:  ssh ${ALIAS}"
