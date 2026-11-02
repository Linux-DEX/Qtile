#!/usr/bin/env bash
# Full Qtile setup for Arch/CachyOS (alongside Plasma — does not remove it).
# Safe to re-run. No picom.
#
# Usage (on the Arch machine, as your user):
#   bash setup.sh
#   SKIP_SESSIONS=1 bash setup.sh          # packages + configs only
#   QTILE_SRC=/path/to/this/repo bash setup.sh
#
# Called from ssh-arch/post-install.sh when SKIP_QTILE is not set.
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Run as your normal user (with sudo), not root."
  exit 1
fi

if ! command -v pacman >/dev/null 2>&1; then
  echo "pacman not found — Arch/CachyOS only."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QTILE_SRC="${QTILE_SRC:-$SCRIPT_DIR}"
TARGET_QTILE="${HOME}/.config/qtile"
TARGET_GHOSTTY="${HOME}/.config/ghostty"
TARGET_MAKO="${HOME}/.config/mako"

echo "==> Qtile setup"
echo "    source: $QTILE_SRC"
echo "    target: $TARGET_QTILE"

# ---------------------------------------------------------------------------
# packages
# ---------------------------------------------------------------------------
ROOT_SCRIPT="$(mktemp /tmp/qtile-setup-root-XXXXXX.sh)"
cleanup() { rm -f "$ROOT_SCRIPT"; }
trap cleanup EXIT

cat > "$ROOT_SCRIPT" << 'ROOT'
#!/usr/bin/env bash
set -euo pipefail

pacman -S --needed --noconfirm \
  qtile \
  python-dbus-fast \
  python-psutil \
  python-pyxdg \
  python-pywayland \
  xorg-server \
  xorg-xinit \
  xorg-xwayland \
  xdg-desktop-portal-wlr \
  grim \
  slurp \
  brightnessctl \
  wl-clipboard \
  cliphist \
  rofi \
  ghostty \
  mako \
  dunst \
  network-manager-applet \
  blueman \
  swaylock \
  swayidle \
  playerctl \
  pavucontrol \
  libnotify \
  dolphin \
  noto-fonts \
  ttf-jetbrains-mono-nerd

mkdir -p /usr/share/wayland-sessions /usr/share/xsessions

# Drop package duplicate session entries
rm -f /usr/share/wayland-sessions/qtile-generic.desktop
rm -f /usr/share/xsessions/qtile-generic.desktop

cat > /usr/share/wayland-sessions/qtile-wayland.desktop << 'EOF'
[Desktop Entry]
Name=Qtile (Wayland)
Comment=Qtile tiling window manager on Wayland
Exec=qtile start -b wayland
TryExec=qtile
Type=Application
DesktopNames=qtile
Keywords=tiling;wm;wayland;
EOF

cat > /usr/share/xsessions/qtile.desktop << 'EOF'
[Desktop Entry]
Name=Qtile (X11)
Comment=Qtile tiling window manager on X11
Exec=qtile start
TryExec=qtile
Type=Application
DesktopNames=qtile
Keywords=tiling;wm;x11;
EOF

# Greeter default stays Plasma when present
if [[ -f /etc/plasmalogin.conf ]] && grep -qE '^Session=' /etc/plasmalogin.conf; then
  sed -i 's/^Session=.*/Session=plasma/' /etc/plasmalogin.conf
fi

echo "ROOT_OK"
ROOT
chmod 700 "$ROOT_SCRIPT"

echo "==> Installing packages + login sessions (sudo)"
sudo bash "$ROOT_SCRIPT"

# ---------------------------------------------------------------------------
# deploy this repo → ~/.config/qtile
# ---------------------------------------------------------------------------
echo "==> Deploying Qtile config → $TARGET_QTILE"
if [[ "$TARGET_QTILE" == "$QTILE_SRC" ]]; then
  echo "    already running from $TARGET_QTILE — skip copy"
else
  mkdir -p "$TARGET_QTILE"
  rsync -a \
    --exclude '.git/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    "$QTILE_SRC"/ "$TARGET_QTILE"/
fi

chmod +x "$TARGET_QTILE"/setup.sh 2>/dev/null || true
chmod +x "$TARGET_QTILE"/install-on-arch.sh 2>/dev/null || true
chmod +x "$TARGET_QTILE"/scripts/*.sh 2>/dev/null || true

# ---------------------------------------------------------------------------
# Ghostty (linux-dex theme — same as Mac)
# ---------------------------------------------------------------------------
if [[ -d "$QTILE_SRC/ghostty" ]]; then
  echo "==> Deploying Ghostty config"
  mkdir -p "$TARGET_GHOSTTY/themes"
  cp -f "$QTILE_SRC/ghostty/config" "$TARGET_GHOSTTY/config"
  cp -f "$QTILE_SRC/ghostty/themes/"* "$TARGET_GHOSTTY/themes/" 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# Mako notifications
# ---------------------------------------------------------------------------
if [[ -f "$QTILE_SRC/scripts/mako/config" ]]; then
  echo "==> Deploying mako config"
  mkdir -p "$TARGET_MAKO"
  cp -f "$QTILE_SRC/scripts/mako/config" "$TARGET_MAKO/config"
fi

# Rofi theme discoverable by name
mkdir -p "${HOME}/.local/share/rofi/themes" "${HOME}/.config/rofi"
if [[ -f "$TARGET_QTILE/rofi/catppuccin-mocha.rasi" ]]; then
  cp -f "$TARGET_QTILE/rofi/catppuccin-mocha.rasi" "${HOME}/.local/share/rofi/themes/"
fi
if [[ -f "$TARGET_QTILE/rofi/config.rasi" ]]; then
  ln -sfn "$TARGET_QTILE/rofi/config.rasi" "${HOME}/.config/rofi/config.rasi"
fi

# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
echo "==> Validate"
python -c "import libqtile; print('libqtile OK')"
test -f "$TARGET_QTILE/config.py"
[[ -f /usr/share/wayland-sessions/qtile-wayland.desktop ]] || true
[[ -f /usr/share/xsessions/qtile.desktop ]] || true

# Keep plasma if present
if [[ -f /usr/share/wayland-sessions/plasma.desktop ]]; then
  echo "    plasma.desktop present (untouched)"
fi

echo
echo "Done."
echo "  Config:   $TARGET_QTILE"
echo "  Ghostty:  $TARGET_GHOSTTY"
echo "  Sessions: Plasma (Wayland) | Qtile (Wayland) | Qtile (X11)"
echo "  Log out → pick session in the greeter."
echo "  Close window: Super+q | Search: Super+Space | Terminal: Super+Return (Ghostty)"
