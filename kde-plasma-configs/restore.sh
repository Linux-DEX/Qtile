#!/usr/bin/env bash
# Restore the saved Reddit-style Plasma layout onto this machine (run as the desktop user).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Backing up current Plasma config"
BACKUP="${HOME}/plasma-backup-before-restore-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
cp -a "${HOME}/.config/plasma-org.kde.plasma.desktop-appletsrc" \
  "${HOME}/.config/kdeglobals" \
  "${HOME}/.config/kwinrc" \
  "${HOME}/.config/plasmarc" \
  "${HOME}/.config/plasmashellrc" \
  "$BACKUP/" 2>/dev/null || true
echo "    backup: $BACKUP"

echo "==> Installing assets"
mkdir -p "${HOME}/.local/share/color-schemes" \
  "${HOME}/.local/share/plasma/desktoptheme" \
  "${HOME}/.local/share/icons" \
  "${HOME}/Pictures/Wallpapers"

cp -a "$ROOT/color-schemes/BreezeDarkCustom.colors" "${HOME}/.local/share/color-schemes/"
rm -rf "${HOME}/.local/share/plasma/desktoptheme/ROUNDED-COLOR"
cp -a "$ROOT/plasma/desktoptheme/ROUNDED-COLOR" "${HOME}/.local/share/plasma/desktoptheme/"
rm -rf "${HOME}/.local/share/icons/volantes_cursors"
cp -a "$ROOT/icons/volantes_cursors" "${HOME}/.local/share/icons/"
mkdir -p "${HOME}/.local/share/aurorae/themes"
rm -rf "${HOME}/.local/share/aurorae/themes/WhiteSur-dark-opaque"
cp -a "$ROOT/aurorae/WhiteSur-dark-opaque" "${HOME}/.local/share/aurorae/themes/"
[[ -f "$ROOT/config/breezerc" ]] && cp -a "$ROOT/config/breezerc" "${HOME}/.config/"
cp -a "$ROOT/wallpaper/reddit-plasma.jpg" "${HOME}/Pictures/Wallpapers/"

echo "==> Ensuring YAMIS + Papirus (icon inherit)"
if [[ ! -d "${HOME}/.local/share/icons/yet-another-monochrome-icon-set" ]]; then
  echo "    cloning YAMIS..."
  git clone --depth 1 https://bitbucket.org/dirn-typo/yet-another-monochrome-icon-set.git \
    "${HOME}/.local/share/icons/yet-another-monochrome-icon-set"
fi
if [[ ! -d "${HOME}/.local/share/icons/Papirus-Dark" ]]; then
  echo "    Papirus-Dark missing — install papirus-icon-theme (pacman) or clone Papirus into ~/.local/share/icons"
fi

echo "==> Writing Plasma config files"
cp -a "$ROOT/config/plasma-org.kde.plasma.desktop-appletsrc" "${HOME}/.config/"
cp -a "$ROOT/config/kdeglobals" "${HOME}/.config/"
cp -a "$ROOT/config/kwinrc" "${HOME}/.config/"
cp -a "$ROOT/config/plasmarc" "${HOME}/.config/"
cp -a "$ROOT/config/plasmashellrc" "${HOME}/.config/"
if [[ -d "$ROOT/config/kdedefaults" ]]; then
  mkdir -p "${HOME}/.config/kdedefaults"
  cp -a "$ROOT/config/kdedefaults/." "${HOME}/.config/kdedefaults/"
fi

# Fix wallpaper path to this user
if command -v sed >/dev/null; then
  sed -i "s|/home/[^/]*/Pictures/Wallpapers/reddit-plasma.jpg|${HOME}/Pictures/Wallpapers/reddit-plasma.jpg|g" \
    "${HOME}/.config/plasma-org.kde.plasma.desktop-appletsrc"
fi

echo "==> Applying look (needs active Plasma session)"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"
plasma-apply-colorscheme BreezeDarkCustom 2>/dev/null || true
plasma-apply-desktoptheme ROUNDED-COLOR 2>/dev/null || true
plasma-apply-cursortheme volantes_cursors 2>/dev/null || true
plasma-apply-wallpaperimage "${HOME}/Pictures/Wallpapers/reddit-plasma.jpg" 2>/dev/null || true
kwriteconfig6 --file kdeglobals --group Icons --key Theme "yet-another-monochrome-icon-set" 2>/dev/null || true
kwriteconfig6 --file kdeglobals --group General --key AccentColorFromWallpaper --type bool true 2>/dev/null || true

echo "==> Restarting plasmashell"
if command -v kquitapp6 >/dev/null; then
  kquitapp6 plasmashell 2>/dev/null || true
  sleep 2
  nohup plasmashell >/tmp/plasmashell-restore.log 2>&1 &
fi

echo "Done. Log out/in if panels look wrong."
