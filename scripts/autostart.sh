#!/bin/bash
# Soft-fail autostart for X11 and Wayland. No picom.
# Wallpaper comes from config.py (Screen.wallpaper).

run() {
  local bin
  bin="$(command -v "$1" 2>/dev/null)" || return 0
  shift
  if ! pgrep -x "$(basename "$bin" | cut -c1-15)" >/dev/null 2>&1; then
    "$bin" "$@" &
  fi
}

export XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-qtile}"

is_wayland=0
if [[ "${XDG_SESSION_TYPE:-}" == "wayland" || -n "${WAYLAND_DISPLAY:-}" ]]; then
  is_wayland=1
  export XDG_SESSION_TYPE=wayland
else
  export XDG_SESSION_TYPE=x11
fi

if command -v dbus-update-activation-environment >/dev/null 2>&1; then
  dbus-update-activation-environment --systemd \
    DISPLAY WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE 2>/dev/null || true
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE 2>/dev/null || true
fi

if ((is_wayland)); then
  run /usr/lib/xdg-desktop-portal-wlr
  run /usr/lib/xdg-desktop-portal
  # notifications
  run mako
  # clipboard history daemon
  if command -v wl-paste >/dev/null && command -v cliphist >/dev/null; then
    pgrep -f "wl-paste --watch cliphist" >/dev/null 2>&1 \
      || wl-paste --type text --watch cliphist store &
    pgrep -f "wl-paste --type image" >/dev/null 2>&1 \
      || wl-paste --type image --watch cliphist store &
  fi
  # idle lock (5 min)
  if command -v swayidle >/dev/null && command -v swaylock >/dev/null; then
    pgrep -x swayidle >/dev/null 2>&1 || swayidle -w \
      timeout 300 'swaylock -f -c 1e1e2e' \
      before-sleep 'swaylock -f -c 1e1e2e' &
  fi
else
  command -v xsetroot >/dev/null 2>&1 && xsetroot -cursor_name left_ptr &
  run dunst
fi

# tray applets
run nm-applet --indicator
run blueman-applet
run xfce4-power-manager

if [[ -x /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 ]]; then
  pgrep -f polkit-gnome-authentication-agent-1 >/dev/null 2>&1 \
    || /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 &
elif [[ -x /usr/lib/polkit-kde-authentication-agent-1 ]]; then
  pgrep -f polkit-kde-authentication-agent-1 >/dev/null 2>&1 \
    || /usr/lib/polkit-kde-authentication-agent-1 &
fi
