#!/usr/bin/env bash
# Run ON the Arch/CachyOS laptop as the user you SSH into (e.g. linuxdex).
# Ensures sshd + mDNS (.local) are ready and ~/.ssh perms are correct.
set -euo pipefail

USER_NAME="$(whoami)"
HOME_DIR="$(eval echo "~${USER_NAME}")"

echo "==> Installing openssh + avahi (mDNS for *.local) if missing"
if command -v pacman >/dev/null 2>&1; then
  sudo pacman -S --needed --noconfirm openssh avahi nss-mdns
else
  echo "pacman not found — install openssh, avahi, nss-mdns yourself"
  exit 1
fi

echo "==> Enabling sshd"
sudo systemctl enable --now sshd

echo "==> Enabling avahi (archlinux.local)"
sudo systemctl enable --now avahi-daemon

# Ensure mdns is in nsswitch hosts line
if [[ -f /etc/nsswitch.conf ]] && ! grep -q 'mdns' /etc/nsswitch.conf; then
  echo "WARN: /etc/nsswitch.conf hosts line may lack mdns_minimal — check Arch wiki 'Avahi'"
fi

echo "==> Preparing ~/.ssh"
mkdir -p "${HOME_DIR}/.ssh"
chmod 700 "${HOME_DIR}/.ssh"
touch "${HOME_DIR}/.ssh/authorized_keys"
chmod 600 "${HOME_DIR}/.ssh/authorized_keys"

# Optional: paste a pubkey as first argument, or via stdin
if [[ $# -ge 1 ]]; then
  KEY="$1"
  grep -qxF "$KEY" "${HOME_DIR}/.ssh/authorized_keys" || echo "$KEY" >> "${HOME_DIR}/.ssh/authorized_keys"
  echo "Added provided pubkey to authorized_keys"
elif [[ ! -t 0 ]]; then
  KEY="$(cat)"
  if [[ -n "$KEY" ]]; then
    grep -qxF "$KEY" "${HOME_DIR}/.ssh/authorized_keys" || echo "$KEY" >> "${HOME_DIR}/.ssh/authorized_keys"
    echo "Added pubkey from stdin to authorized_keys"
  fi
else
  echo "No pubkey passed. On the Mac run:"
  echo "  ssh-copy-id -i ~/.ssh/id_ed25519.pub ${USER_NAME}@$(hostname).local"
  echo "Or re-run this script with the pubkey:"
  echo "  ./setup-arch.sh \"\$(cat ~/.ssh/id_ed25519.pub)\""
fi

echo
echo "Status:"
systemctl is-active sshd
systemctl is-active avahi-daemon
echo "User: ${USER_NAME}"
echo "Hostname: $(hostname)"
echo "Reachable as: ${USER_NAME}@$(hostname).local"
echo "authorized_keys lines: $(wc -l < "${HOME_DIR}/.ssh/authorized_keys")"
echo
echo "Done on Arch side."
