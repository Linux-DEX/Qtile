# Qtile config — upstream standard keybindings, X11 + Wayland.
# Start:  qtile start          (X11)
#         qtile start -b wayland
# https://docs.qtile.org/en/latest/manual/config/lazy.html
# https://docs.qtile.org/en/latest/manual/wayland.html
from __future__ import annotations

import os
import shutil
import subprocess
import time

from libqtile import bar, hook, layout, qtile, widget
from libqtile.config import Click, Drag, Group, Key, Match, Screen
from libqtile.lazy import lazy
from libqtile.utils import guess_terminal

mod = "mod4"
terminal = guess_terminal()
cfg_dir = os.path.dirname(os.path.abspath(__file__))
wallpaper = os.path.join(cfg_dir, "wallpaper", "jujutsu.jpg")

# ---------------------------------------------------------------------------
# backend helpers
# ---------------------------------------------------------------------------

def is_wayland() -> bool:
    """Prefer live core name; fall back to env (config parse / early hooks)."""
    try:
        return qtile.core.name == "wayland"
    except Exception:
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            return True
        return bool(os.environ.get("WAYLAND_DISPLAY"))


@lazy.function
def take_screenshot(qtile):
    dest_dir = os.path.expanduser("~/Pictures")
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"shot-{int(time.time())}.png")
    if qtile.core.name == "wayland":
        if shutil.which("grim") and shutil.which("slurp"):
            subprocess.Popen(["sh", "-c", f'grim -g "$(slurp)" "{path}"'])
        elif shutil.which("grim"):
            subprocess.Popen(["grim", path])
    else:
        if shutil.which("scrot"):
            subprocess.Popen(["scrot", "-s", path])
        elif shutil.which("flameshot"):
            subprocess.Popen(["flameshot", "gui"])


@lazy.function
def volume_adjust(qtile, delta: str):
    """PipeWire (wpctl) → pactl → amixer."""
    if shutil.which("wpctl"):
        if delta == "mute":
            subprocess.Popen(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
        else:
            subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", delta])
        return
    if shutil.which("pactl"):
        if delta == "mute":
            subprocess.Popen(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
        elif delta.endswith("%+"):
            subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{delta[:-2]}%"])
        else:
            subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{delta[:-2]}%"])
        return
    if shutil.which("amixer"):
        if delta == "mute":
            subprocess.Popen(["amixer", "-q", "set", "Master", "toggle"])
        elif delta.endswith("%+"):
            subprocess.Popen(["amixer", "-q", "set", "Master", f"{delta[:-2]}%+"])
        else:
            subprocess.Popen(["amixer", "-q", "set", "Master", f"{delta[:-2]}%-"])


# ---------------------------------------------------------------------------
# keys — upstream defaults + safe extras (no sxhkd)
# ---------------------------------------------------------------------------

keys = [
    Key([mod], "h", lazy.layout.left(), desc="Focus left"),
    Key([mod], "l", lazy.layout.right(), desc="Focus right"),
    Key([mod], "j", lazy.layout.down(), desc="Focus down"),
    Key([mod], "k", lazy.layout.up(), desc="Focus up"),
    Key([mod], "space", lazy.layout.next(), desc="Focus next window"),
    Key([mod, "shift"], "h", lazy.layout.shuffle_left(), desc="Move window left"),
    Key([mod, "shift"], "l", lazy.layout.shuffle_right(), desc="Move window right"),
    Key([mod, "shift"], "j", lazy.layout.shuffle_down(), desc="Move window down"),
    Key([mod, "shift"], "k", lazy.layout.shuffle_up(), desc="Move window up"),
    Key([mod, "control"], "h", lazy.layout.grow_left(), desc="Grow left"),
    Key([mod, "control"], "l", lazy.layout.grow_right(), desc="Grow right"),
    Key([mod, "control"], "j", lazy.layout.grow_down(), desc="Grow down"),
    Key([mod, "control"], "k", lazy.layout.grow_up(), desc="Grow up"),
    Key([mod], "n", lazy.layout.normalize(), desc="Normalize window sizes"),
    Key(
        [mod, "shift"],
        "Return",
        lazy.layout.toggle_split(),
        desc="Toggle split/unsplit stack",
    ),
    Key([mod], "Return", lazy.spawn(terminal), desc="Launch terminal"),
    Key([mod], "Tab", lazy.next_layout(), desc="Next layout"),
    Key([mod], "w", lazy.window.kill(), desc="Kill focused window"),
    Key([mod], "f", lazy.window.toggle_fullscreen(), desc="Toggle fullscreen"),
    Key([mod], "t", lazy.window.toggle_floating(), desc="Toggle floating"),
    Key([mod, "control"], "r", lazy.reload_config(), desc="Reload config"),
    Key([mod, "control"], "q", lazy.shutdown(), desc="Shutdown Qtile"),
    Key([mod], "r", lazy.spawncmd(), desc="Spawn command prompt"),
    Key([], "Print", take_screenshot(), desc="Screenshot"),
    Key([], "XF86AudioRaiseVolume", volume_adjust("5%+")),
    Key([], "XF86AudioLowerVolume", volume_adjust("5%-")),
    Key([], "XF86AudioMute", volume_adjust("mute")),
    Key([], "XF86MonBrightnessUp", lazy.spawn("brightnessctl -q s +10%")),
    Key([], "XF86MonBrightnessDown", lazy.spawn("brightnessctl -q s 10%-")),
]

for vt in range(1, 8):
    keys.append(
        Key(
            ["control", "mod1"],
            f"f{vt}",
            lazy.core.change_vt(vt).when(func=lambda: qtile.core.name == "wayland"),
            desc=f"Switch to VT{vt}",
        )
    )

groups = [Group(i) for i in "123456789"]

for i in groups:
    keys.extend(
        [
            Key(
                [mod],
                i.name,
                lazy.group[i.name].toscreen(),
                desc=f"Switch to group {i.name}",
            ),
            Key(
                [mod, "shift"],
                i.name,
                lazy.window.togroup(i.name, switch_group=True),
                desc=f"Move focused window to group {i.name}",
            ),
        ]
    )

layouts = [
    layout.Columns(
        border_focus="#7aa2f7",
        border_normal="#1a1b26",
        border_width=2,
        margin=4,
        border_on_single=False,
    ),
    layout.Max(),
    layout.MonadTall(
        border_focus="#7aa2f7",
        border_normal="#1a1b26",
        border_width=2,
        margin=4,
    ),
]

widget_defaults = dict(
    font="sans",
    fontsize=13,
    padding=4,
    foreground="#c0caf5",
)
extension_defaults = widget_defaults.copy()

# ---------------------------------------------------------------------------
# widgets — prefer backends that work on both X11 and Wayland
# ---------------------------------------------------------------------------

def _sep():
    return widget.Sep(linewidth=1, padding=8, foreground="#565f89")


def _tray():
    # StatusNotifier works on Wayland and X11 (needs python-dbus-fast).
    # Systray is X11-only and crashes under Wayland — never use it here.
    return widget.StatusNotifier()


def _volume():
    # PulseVolume talks to PipeWire/Pulse via libpulse; Volume falls back to ALSA.
    if hasattr(widget, "PulseVolume"):
        return widget.PulseVolume(
            fmt="vol {}",
            update_interval=0.2,
            step=5,
            limit_max_volume=True,
        )
    return widget.Volume(fmt="vol {}", step=5)


def _battery():
    # No crash on desktops without a battery — widget shows empty/hidden.
    return widget.Battery(
        format="{char}{percent:2.0%}",
        charge_char="↑",
        discharge_char="↓",
        full_char="",
        empty_char="!",
        unknown_char="?",
        update_interval=30,
        show_short_text=False,
        not_charging_char="",
    )


def _cpu():
    try:
        import psutil  # noqa: F401
    except ImportError:
        return widget.TextBox("")
    return widget.CPU(format="cpu {load_percent}%", update_interval=2)


def _mem():
    try:
        import psutil  # noqa: F401
    except ImportError:
        return widget.TextBox("")
    return widget.Memory(format="mem {MemUsed:.0f}{mm}", measure_mem="G", update_interval=2)


def init_widgets():
    return [
        widget.CurrentLayout(fmt="[{}]"),
        widget.GroupBox(
            highlight_method="line",
            this_current_screen_border="#7aa2f7",
            this_screen_border="#3d59a1",
            other_current_screen_border="#bb9af7",
            other_screen_border="#414868",
            active="#c0caf5",
            inactive="#565f89",
            disable_drag=True,
            rounded=False,
            borderwidth=2,
        ),
        widget.Prompt(foreground="#9ece6a"),
        widget.WindowName(foreground="#c0caf5", max_chars=60),
        widget.Chord(
            chords_colors={"launch": ("#f7768e", "#1a1b26")},
            name_transform=lambda name: name.upper(),
        ),
        widget.Spacer(),
        _sep(),
        _cpu(),
        _mem(),
        _sep(),
        _volume(),
        _sep(),
        _battery(),
        _sep(),
        _tray(),
        widget.Clock(format="%Y-%m-%d %a %H:%M"),
        widget.QuickExit(default_text="[exit]", countdown_format="[{}]", foreground="#f7768e"),
    ]


screens = [
    Screen(
        top=bar.Bar(
            init_widgets(),
            28,
            background="#1a1b26",
            margin=[4, 4, 0, 4],
        ),
        wallpaper=wallpaper if os.path.isfile(wallpaper) else None,
        wallpaper_mode="fill",
    ),
]

mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(), start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(), start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.bring_to_front()),
]

dgroups_key_binder = None
dgroups_app_rules = []
follow_mouse_focus = True
bring_front_click = False
floats_kept_above = True
cursor_warp = False
floating_layout = layout.Floating(
    float_rules=[
        *layout.Floating.default_float_rules,
        Match(wm_class="confirmreset"),
        Match(wm_class="makebranch"),
        Match(wm_class="maketag"),
        Match(wm_class="ssh-askpass"),
        Match(wm_class="pinentry"),
        Match(wm_class="pinentry-gtk-2"),
        Match(wm_class="pinentry-qt"),
        Match(title="branchdialog"),
        Match(title="pinentry"),
    ],
    border_focus="#7aa2f7",
    border_normal="#1a1b26",
    border_width=2,
)
auto_fullscreen = True
focus_on_window_activation = "smart"
reconfigure_screens = True
auto_minimize = True
wmname = "LG3D"

# Wayland input (touchpad tap, etc.). Safe no-op if backend bits missing.
try:
    from libqtile.backend.wayland import InputConfig

    wl_input_rules = {
        "type:touchpad": InputConfig(tap=True, natural_scroll=True),
        "type:keyboard": InputConfig(kb_layout="us"),
    }
except ImportError:
    wl_input_rules = None

wl_xcursor_theme = None
wl_xcursor_size = 24


@hook.subscribe.startup_once
def _autostart():
    # Help portals / tray apps know the session type early.
    os.environ.setdefault("XDG_CURRENT_DESKTOP", "qtile")
    if is_wayland():
        os.environ.setdefault("XDG_SESSION_TYPE", "wayland")
    else:
        os.environ.setdefault("XDG_SESSION_TYPE", "x11")

    script = os.path.join(cfg_dir, "scripts", "autostart.sh")
    if os.path.isfile(script):
        subprocess.Popen(["/bin/bash", script])
