#!/usr/bin/env bash
# Run on the Arch laptop as your user (linuxdex).
# Adds Qtile sessions next to Plasma. Does not remove or disable Plasma.
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Run as your normal user, not root."
  exit 1
fi

ROOT_SCRIPT="$(mktemp /tmp/qtile-root-XXXXXX.sh)"
trap 'rm -f "$ROOT_SCRIPT"' EXIT

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
  picom \
  wl-clipboard \
  noto-fonts \
  ttf-jetbrains-mono-nerd

mkdir -p /usr/share/wayland-sessions /usr/share/xsessions

# Package ships qtile-generic.desktop in BOTH session dirs → duplicate menu entries.
# Drop those; keep one clearly named Wayland + one X11 entry only.
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

# Keep greeter default on Plasma; never delete plasma.desktop
if [[ -f /etc/plasmalogin.conf ]] && grep -qE '^Session=' /etc/plasmalogin.conf; then
  sed -i 's/^Session=.*/Session=plasma/' /etc/plasmalogin.conf
fi

test -f /usr/share/wayland-sessions/plasma.desktop
echo "ROOT_OK"
ROOT
chmod 700 "$ROOT_SCRIPT"

echo "==> Installing packages + session files (sudo password once)"
sudo bash "$ROOT_SCRIPT"

if [[ ! -f "$HOME/.config/qtile/config.py" ]]; then
  mkdir -p "$HOME/.config"
  git clone https://github.com/Linux-DEX/Qtile.git "$HOME/.config/qtile"
fi
chmod +x "$HOME/.config/qtile/scripts/"*.sh 2>/dev/null || true

python -c "import libqtile; print('libqtile OK')"
test -f /usr/share/wayland-sessions/plasma.desktop
test -f /usr/share/wayland-sessions/qtile-wayland.desktop
test -f /usr/share/xsessions/qtile.desktop

echo
echo "Sessions:"
ls -la /usr/share/wayland-sessions/ /usr/share/xsessions/
echo
echo "Done. Default remains Plasma (Wayland)."
echo "Log out → session menu → pick Plasma / Qtile (Wayland) / Qtile (X11)."
