# Qtile config — Catppuccin Mocha, Ghostty, Wayland/X11.
# https://docs.qtile.org/en/latest/manual/config/lazy.html
from __future__ import annotations

import os
import shutil
import subprocess
import time

from libqtile import bar, hook, layout, qtile, widget
from libqtile.config import (
    Click,
    Drag,
    DropDown,
    Group,
    Key,
    Match,
    ScratchPad,
    Screen,
)
from libqtile.lazy import lazy
from libqtile.utils import guess_terminal

mod = "mod4"
terminal = "ghostty" if shutil.which("ghostty") else guess_terminal()
file_manager = "dolphin" if shutil.which("dolphin") else "thunar"
cfg_dir = os.path.dirname(os.path.abspath(__file__))
wallpaper = os.path.join(cfg_dir, "wallpaper", "jujutsu.jpg")
rofi_config = os.path.join(cfg_dir, "rofi", "config.rasi")

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def is_wayland() -> bool:
    try:
        return qtile.core.name == "wayland"
    except Exception:
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            return True
        return bool(os.environ.get("WAYLAND_DISPLAY"))


def rofi_bin() -> str:
    if is_wayland() and shutil.which("rofi-wayland"):
        return "rofi-wayland"
    if shutil.which("rofi"):
        return "rofi"
    return "rofi-wayland"


def rofi_cmd(mode: str = "combi") -> str:
    parts = [rofi_bin(), "-show", mode]
    if mode == "combi":
        parts.extend(["-modes", "combi", "-combi-modes", "drun,run,window,filebrowser"])
    theme = os.path.join(cfg_dir, "rofi", "catppuccin-mocha.rasi")
    if os.path.isfile(rofi_config):
        parts.extend(["-config", rofi_config])
    if os.path.isfile(theme):
        parts.extend(["-theme", theme])
    return " ".join(parts)


def lock_cmd() -> str:
    if shutil.which("swaylock"):
        return "swaylock -f -c 1e1e2e"
    if shutil.which("hyprlock"):
        return "hyprlock"
    return "loginctl lock-session"


def clipboard_cmd() -> str:
    # cliphist + rofi picker when available
    if shutil.which("cliphist") and shutil.which(rofi_bin()):
        theme = os.path.join(cfg_dir, "rofi", "catppuccin-mocha.rasi")
        return (
            "sh -c "
            + repr(
                f"cliphist list | {rofi_bin()} -dmenu -p clip -theme {theme} | cliphist decode | wl-copy"
            )
        )
    return "true"


def power_menu_cmd() -> str:
    theme = os.path.join(cfg_dir, "rofi", "catppuccin-mocha.rasi")
    theme_flag = f" -theme {theme}" if os.path.isfile(theme) else ""
    # ponytail: one-shot rofi case; ceiling is fixed action list
    script = f"""
choice=$(printf 'lock\\nlogout\\nreboot\\nshutdown' | {rofi_bin()} -dmenu -p power{theme_flag}) || exit 0
case "$choice" in
  lock) {lock_cmd()} ;;
  logout) qtile cmd-obj -o cmd -f shutdown ;;
  reboot) systemctl reboot ;;
  shutdown) systemctl poweroff ;;
esac
"""
    return "sh -c " + repr(script.strip())


def _notify(summary: str, body: str = "") -> None:
    if shutil.which("notify-send"):
        subprocess.Popen(["notify-send", "-a", "qtile", summary, body])


@lazy.function
def take_screenshot(qtile):
    dest_dir = os.path.expanduser("~/Pictures")
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"shot-{int(time.time())}.png")
    if qtile.core.name == "wayland" and shutil.which("grim"):
        region = ' -g "$(slurp)"' if shutil.which("slurp") else ""
        if shutil.which("wl-copy"):
            cmd = f'grim{region} - | tee "{path}" | wl-copy --type image/png'
        else:
            cmd = f'grim{region} "{path}"'
        if shutil.which("notify-send"):
            cmd += f' && notify-send -a qtile Screenshot "{path}"'
        subprocess.Popen(["sh", "-c", cmd])
    elif shutil.which("scrot"):
        subprocess.Popen(["scrot", "-s", path])
        _notify("Screenshot", path)
    elif shutil.which("flameshot"):
        subprocess.Popen(["flameshot", "gui"])


@lazy.function
def volume_adjust(qtile, delta: str):
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
# keys
# ---------------------------------------------------------------------------

keys = [
    # focus
    Key([mod], "h", lazy.layout.left(), desc="Focus left"),
    Key([mod], "l", lazy.layout.right(), desc="Focus right"),
    Key([mod], "j", lazy.layout.down(), desc="Focus down"),
    Key([mod], "k", lazy.layout.up(), desc="Focus up"),
    Key([mod], "Left", lazy.layout.left(), desc="Focus left"),
    Key([mod], "Right", lazy.layout.right(), desc="Focus right"),
    Key([mod], "Down", lazy.layout.down(), desc="Focus down"),
    Key([mod], "Up", lazy.layout.up(), desc="Focus up"),
    Key([mod, "shift"], "space", lazy.layout.next(), desc="Focus next window"),
    # move
    Key([mod, "shift"], "h", lazy.layout.shuffle_left(), desc="Move window left"),
    Key([mod, "shift"], "l", lazy.layout.shuffle_right(), desc="Move window right"),
    Key([mod, "shift"], "j", lazy.layout.shuffle_down(), desc="Move window down"),
    Key([mod, "shift"], "k", lazy.layout.shuffle_up(), desc="Move window up"),
    Key([mod, "shift"], "Left", lazy.layout.swap_left(), desc="Swap left (MonadTall)"),
    Key([mod, "shift"], "Right", lazy.layout.swap_right(), desc="Swap right (MonadTall)"),
    Key([mod, "shift"], "Down", lazy.layout.shuffle_down(), desc="Move window down"),
    Key([mod, "shift"], "Up", lazy.layout.shuffle_up(), desc="Move window up"),
    # grow — multi-action so Columns + MonadTall both respond
    Key(
        [mod, "control"], "h",
        lazy.layout.grow_left(),
        lazy.layout.shrink(),
        lazy.layout.decrease_ratio(),
        lazy.layout.add(),
        desc="Grow/shrink left",
    ),
    Key(
        [mod, "control"], "l",
        lazy.layout.grow_right(),
        lazy.layout.grow(),
        lazy.layout.increase_ratio(),
        lazy.layout.delete(),
        desc="Grow/shrink right",
    ),
    Key(
        [mod, "control"], "j",
        lazy.layout.grow_down(),
        lazy.layout.shrink(),
        lazy.layout.increase_nmaster(),
        desc="Grow/shrink down",
    ),
    Key(
        [mod, "control"], "k",
        lazy.layout.grow_up(),
        lazy.layout.grow(),
        lazy.layout.decrease_nmaster(),
        desc="Grow/shrink up",
    ),
    Key(
        [mod, "control"], "Left",
        lazy.layout.grow_left(),
        lazy.layout.shrink(),
        lazy.layout.decrease_ratio(),
        lazy.layout.add(),
        desc="Grow/shrink left",
    ),
    Key(
        [mod, "control"], "Right",
        lazy.layout.grow_right(),
        lazy.layout.grow(),
        lazy.layout.increase_ratio(),
        lazy.layout.delete(),
        desc="Grow/shrink right",
    ),
    Key(
        [mod, "control"], "Down",
        lazy.layout.grow_down(),
        lazy.layout.shrink(),
        lazy.layout.increase_nmaster(),
        desc="Grow/shrink down",
    ),
    Key(
        [mod, "control"], "Up",
        lazy.layout.grow_up(),
        lazy.layout.grow(),
        lazy.layout.decrease_nmaster(),
        desc="Grow/shrink up",
    ),
    Key([mod], "n", lazy.layout.normalize(), desc="Normalize sizes"),
    Key([mod], "m", lazy.layout.maximize(), desc="Maximize focused"),
    Key([mod, "shift"], "f", lazy.layout.flip(), desc="Flip master side"),
    Key(
        [mod], "equal",
        lazy.layout.grow_left().when(layout=["bsp", "columns"]),
        lazy.layout.grow().when(layout=["monadtall", "monadwide"]),
        desc="Grow (layout-aware)",
    ),
    Key(
        [mod], "minus",
        lazy.layout.grow_right().when(layout=["bsp", "columns"]),
        lazy.layout.shrink().when(layout=["monadtall", "monadwide"]),
        desc="Shrink (layout-aware)",
    ),
    Key(
        [mod, "shift"], "Return",
        lazy.layout.toggle_split(),
        desc="Toggle split/unsplit",
    ),
    # windows / session
    Key([mod], "Return", lazy.spawn(terminal), desc="Terminal"),
    Key([mod], "Tab", lazy.next_layout(), desc="Next layout"),
    Key([mod], "q", lazy.window.kill(), desc="Close window"),
    Key([mod], "f", lazy.window.toggle_fullscreen(), desc="Fullscreen"),
    Key([mod], "t", lazy.window.toggle_floating(), desc="Floating"),
    Key([mod], "b", lazy.hide_show_bar(), desc="Toggle bar"),
    Key([mod, "control"], "r", lazy.reload_config(), desc="Reload config"),
    Key([mod, "shift"], "e", lazy.spawn(power_menu_cmd()), desc="Power menu"),
    Key([mod], "r", lazy.spawncmd(), desc="Bar command prompt"),
    # launchers / apps
    Key([mod], "space", lazy.spawn(rofi_cmd("combi")), desc="Search everything"),
    Key([mod], "d", lazy.spawn(rofi_cmd("drun")), desc="Apps"),
    Key([mod, "shift"], "d", lazy.spawn(rofi_cmd("run")), desc="Run command"),
    Key([mod], "slash", lazy.spawn(rofi_cmd("window")), desc="Windows"),
    Key([mod], "e", lazy.spawn(file_manager), desc="File manager"),
    Key([mod], "Escape", lazy.spawn(lock_cmd()), desc="Lock screen"),
    Key([mod], "v", lazy.spawn(clipboard_cmd()), desc="Clipboard history"),
    Key([mod], "period", lazy.next_screen(), desc="Next monitor"),
    Key([mod], "comma", lazy.prev_screen(), desc="Prev monitor"),
    # scratchpad dropdown terminal
    Key([mod], "grave", lazy.group["scratchpad"].dropdown_toggle("term"), desc="Scratchpad terminal"),
    # media / brightness
    Key([], "Print", take_screenshot(), desc="Screenshot"),
    Key([], "XF86AudioRaiseVolume", volume_adjust("5%+")),
    Key([], "XF86AudioLowerVolume", volume_adjust("5%-")),
    Key([], "XF86AudioMute", volume_adjust("mute")),
    Key([], "XF86AudioPlay", lazy.spawn("playerctl play-pause")),
    Key([], "XF86AudioNext", lazy.spawn("playerctl next")),
    Key([], "XF86AudioPrev", lazy.spawn("playerctl previous")),
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
groups.append(
    ScratchPad(
        "scratchpad",
        [
            DropDown(
                "term",
                terminal,
                opacity=0.95,
                width=0.7,
                height=0.55,
                x=0.15,
                y=0.1,
                on_focus_lost_hide=True,
            ),
        ],
    )
)

for i in groups:
    if isinstance(i, ScratchPad):
        continue
    keys.extend(
        [
            Key([mod], i.name, lazy.group[i.name].toscreen(), desc=f"Group {i.name}"),
            Key(
                [mod, "shift"],
                i.name,
                lazy.window.togroup(i.name, switch_group=True),
                desc=f"Move to group {i.name}",
            ),
            Key(
                [mod, "control"],
                i.name,
                lazy.window.togroup(i.name, switch_group=False),
                desc=f"Send to group {i.name}",
            ),
        ]
    )

# Palette — Catppuccin Mocha
colors = {
    "bg": "#1e1e2e",
    "fg": "#cdd6f4",
    "blue": "#89b4fa",
    "teal": "#94e2d5",
    "lavender": "#b4befe",
    "peach": "#fab387",
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "mauve": "#cba6f7",
    "overlay": "#6c7086",
    "surface": "#313244",
}

layouts = [
    layout.Columns(
        border_focus=colors["peach"],
        border_normal=colors["overlay"],
        border_width=2,
        margin=6,
        border_on_single=False,
    ),
    layout.Max(margin=6),
    layout.MonadTall(
        border_focus=colors["peach"],
        border_normal=colors["overlay"],
        border_width=2,
        margin=6,
    ),
]

FONT = "JetBrainsMono Nerd Font"
FONT_SIZE = 13

widget_defaults = dict(
    font=FONT,
    fontsize=FONT_SIZE,
    padding=4,
    foreground=colors["fg"],
    background=colors["bg"],
)
extension_defaults = widget_defaults.copy()


def _pipe():
    return widget.TextBox(
        text="│",
        foreground=colors["overlay"],
        background=colors["bg"],
        padding=6,
        fontsize=FONT_SIZE,
    )


def _tray():
    return widget.StatusNotifier(background=colors["bg"], padding=4)


def _volume():
    cbs = {
        "Button1": lazy.spawn("pavucontrol"),
        "Button3": volume_adjust("mute"),
        "Button4": volume_adjust("5%+"),
        "Button5": volume_adjust("5%-"),
    }
    kwargs = dict(
        fmt="{}",
        update_interval=1,
        foreground=colors["green"],
        background=colors["bg"],
        padding=2,
        mouse_callbacks=cbs,
    )
    # Prefer Pulse/PipeWire so the bar matches wpctl/pactl keybinds
    try:
        return widget.PulseVolume(**kwargs)
    except Exception:
        return widget.Volume(step=5, **kwargs)


def _battery():
    return widget.Battery(
        format="{char} {percent:2.0%}",
        charge_char="󰂄",
        discharge_char="󰁹",
        full_char="󰁹",
        empty_char="󰂎",
        unknown_char="󰂑",
        not_charging_char="󰁹",
        update_interval=30,
        show_short_text=False,
        low_percentage=0.2,
        low_foreground=colors["red"],
        foreground=colors["peach"],
        background=colors["bg"],
        padding=2,
    )


def _cpu():
    try:
        import psutil  # noqa: F401
    except ImportError:
        return widget.TextBox("")
    return widget.CPU(
        format="{load_percent:2.0f}%",
        update_interval=2,
        foreground=colors["mauve"],
        background=colors["bg"],
        padding=2,
    )


def _mem():
    try:
        import psutil  # noqa: F401
    except ImportError:
        return widget.TextBox("")
    return widget.Memory(
        format="{MemUsed:.1f}{mm}",
        measure_mem="G",
        update_interval=2,
        foreground=colors["teal"],
        background=colors["bg"],
        padding=2,
    )


def _backlight():
    # Soft-fail if no backlight device
    backlight_dir = "/sys/class/backlight"
    if not os.path.isdir(backlight_dir) or not os.listdir(backlight_dir):
        return widget.TextBox("")
    try:
        return widget.Backlight(
            backlight_name=os.listdir(backlight_dir)[0],
            format="{percent:2.0%}",
            foreground=colors["yellow"],
            background=colors["bg"],
            padding=2,
            change_command="brightnessctl set {0}%",
        )
    except Exception:
        return widget.TextBox("")


def init_widgets():
    return [
        widget.TextBox(
            text=" ",
            foreground=colors["blue"],
            background=colors["bg"],
            padding=4,
            fontsize=FONT_SIZE + 1,
        ),
        widget.CurrentLayout(fmt="{}", foreground=colors["blue"], background=colors["bg"], padding=2),
        _pipe(),
        widget.GroupBox(
            font=FONT,
            fontsize=FONT_SIZE,
            margin_y=2,
            margin_x=0,
            padding_y=2,
            padding_x=6,
            borderwidth=1,
            disable_drag=True,
            rounded=False,
            highlight_method="line",
            highlight_color=[colors["bg"], colors["bg"]],
            this_current_screen_border=colors["peach"],
            this_screen_border=colors["peach"],
            other_current_screen_border=colors["lavender"],
            other_screen_border=colors["overlay"],
            urgent_border=colors["red"],
            urgent_text=colors["red"],
            active=colors["peach"],
            inactive=colors["blue"],
            background=colors["bg"],
            foreground=colors["fg"],
            hide_unused=True,
            spacing=2,
        ),
        widget.Prompt(foreground=colors["green"], background=colors["bg"], padding=6),
        _pipe(),
        widget.TextBox(text="", foreground=colors["teal"], background=colors["bg"], padding=4),
        widget.WindowName(foreground=colors["teal"], background=colors["bg"], max_chars=40, padding=2),
        widget.Spacer(),
        widget.TextBox(text="󰍛", foreground=colors["mauve"], background=colors["bg"], padding=2),
        _cpu(),
        _pipe(),
        widget.TextBox(text="󰘚", foreground=colors["teal"], background=colors["bg"], padding=2),
        _mem(),
        _pipe(),
        widget.TextBox(text="󰃠", foreground=colors["yellow"], background=colors["bg"], padding=2),
        _backlight(),
        _pipe(),
        widget.TextBox(text="󰕾", foreground=colors["green"], background=colors["bg"], padding=2),
        _volume(),
        _pipe(),
        _battery(),
        _pipe(),
        widget.TextBox(text="󰃭", foreground=colors["blue"], background=colors["bg"], padding=2),
        widget.Clock(format="%d-%m-%Y", foreground=colors["blue"], background=colors["bg"], padding=2),
        _pipe(),
        widget.TextBox(text="", foreground=colors["lavender"], background=colors["bg"], padding=2),
        widget.Clock(format="%I:%M %p", foreground=colors["lavender"], background=colors["bg"], padding=4),
        _pipe(),
        _tray(),
        widget.QuickExit(
            default_text="󰐥",
            countdown_format="{}",
            foreground=colors["red"],
            background=colors["bg"],
            padding=8,
            fontsize=FONT_SIZE + 2,
        ),
        widget.TextBox(text=" ", background=colors["bg"], padding=2),
    ]


def make_screen():
    return Screen(
        top=bar.Bar(
            init_widgets(),
            26,
            background=colors["bg"],
            margin=0,
            border_width=[0, 0, 1, 0],
            border_color=[colors["bg"], colors["bg"], colors["surface"], colors["bg"]],
        ),
        wallpaper=wallpaper if os.path.isfile(wallpaper) else None,
        wallpaper_mode="fill",
    )


# ponytail: fixed pool; qtile ignores extras, empty monitors get no bar if under-counted
screens = [make_screen() for _ in range(3)]

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
        Match(wm_class="pavucontrol"),
        Match(wm_class="blueman-manager"),
        Match(wm_class="blueman-adapters"),
        Match(wm_class="nm-connection-editor"),
        Match(wm_class="PictureWindow"),
        Match(title="branchdialog"),
        Match(title="pinentry"),
        Match(title="Picture-in-Picture"),
    ],
    border_focus=colors["peach"],
    border_normal=colors["overlay"],
    border_width=2,
)
auto_fullscreen = True
focus_on_window_activation = "smart"
reconfigure_screens = True
auto_minimize = True
wmname = "LG3D"

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
    os.environ.setdefault("XDG_CURRENT_DESKTOP", "qtile")
    if is_wayland():
        os.environ.setdefault("XDG_SESSION_TYPE", "wayland")
    else:
        os.environ.setdefault("XDG_SESSION_TYPE", "x11")

    # mako config path (Wayland notifications)
    mako_src = os.path.join(cfg_dir, "scripts", "mako", "config")
    mako_dst = os.path.expanduser("~/.config/mako/config")
    if os.path.isfile(mako_src):
        os.makedirs(os.path.dirname(mako_dst), exist_ok=True)
        if not os.path.isfile(mako_dst):
            shutil.copy2(mako_src, mako_dst)

    script = os.path.join(cfg_dir, "scripts", "autostart.sh")
    if os.path.isfile(script):
        subprocess.Popen(["/bin/bash", script])
