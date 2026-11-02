#!/bin/bash
# Soft-fail autostart — missing tools must not break the session.
# Wallpaper is set by config.py (Screen.wallpaper); no feh/sxhkd here.

run() {
  local bin
  bin="$(command -v "$1" 2>/dev/null)" || return 0
  shift
  if ! pgrep -x "$(basename "$bin" | cut -c1-15)" >/dev/null 2>&1; then
    "$bin" "$@" &
  fi
}

# compositor (X11); ignore if absent
if command -v picom >/dev/null 2>&1; then
  if [[ -f "$HOME/.config/qtile/scripts/picom.conf" ]]; then
    run picom --config "$HOME/.config/qtile/scripts/picom.conf"
  else
    run picom
  fi
fi

# network / power / polkit — only if installed
run nm-applet
run xfce4-power-manager

if [[ -x /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 ]]; then
  pgrep -f polkit-gnome-authentication-agent-1 >/dev/null 2>&1 \
    || /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 &
elif [[ -x /usr/lib/polkit-kde-authentication-agent-1 ]]; then
  pgrep -f polkit-kde-authentication-agent-1 >/dev/null 2>&1 \
    || /usr/lib/polkit-kde-authentication-agent-1 &
fi

# cursor theme for X11
command -v xsetroot >/dev/null 2>&1 && xsetroot -cursor_name left_ptr &
