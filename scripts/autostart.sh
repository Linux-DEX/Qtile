#!/bin/bash
# Soft-fail autostart for X11 and Wayland. Missing tools must not break the session.
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

# Expose vars to systemd user services (portals, tray, pipewire)
if command -v dbus-update-activation-environment >/dev/null 2>&1; then
  dbus-update-activation-environment --systemd \
    DISPLAY WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE 2>/dev/null || true
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE 2>/dev/null || true
fi

if ((is_wayland)); then
  # wlroots portal for screenshots/screencast (grim/slurp still used by keybind)
  run /usr/lib/xdg-desktop-portal-wlr
  run /usr/lib/xdg-desktop-portal
  # X11 apps under Wayland
  # (xorg-xwayland is pulled in by the compositor/session as needed)
else
  # X11 compositor + cursor
  if command -v picom >/dev/null 2>&1; then
    if [[ -f "$HOME/.config/qtile/scripts/picom.conf" ]]; then
      run picom --config "$HOME/.config/qtile/scripts/picom.conf"
    else
      run picom
    fi
  fi
  command -v xsetroot >/dev/null 2>&1 && xsetroot -cursor_name left_ptr &
fi

# Shared applets (StatusNotifier / AppIndicator)
run nm-applet --indicator
run xfce4-power-manager

if [[ -x /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 ]]; then
  pgrep -f polkit-gnome-authentication-agent-1 >/dev/null 2>&1 \
    || /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 &
elif [[ -x /usr/lib/polkit-kde-authentication-agent-1 ]]; then
  pgrep -f polkit-kde-authentication-agent-1 >/dev/null 2>&1 \
    || /usr/lib/polkit-kde-authentication-agent-1 &
fi
