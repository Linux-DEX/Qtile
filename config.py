# Qtile config — Catppuccin Mocha, Ghostty, Wayland/X11.
# https://docs.qtile.org/en/latest/manual/config/lazy.html
from __future__ import annotations

import os
import re
import shlex
import signal
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
def take_screenshot(qtile, full: bool = False):
    dest_dir = os.path.expanduser("~/Pictures")
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"shot-{int(time.time())}.png")
    if qtile.core.name == "wayland" and shutil.which("grim"):
        region = "" if full else (' -g "$(slurp)"' if shutil.which("slurp") else "")
        if shutil.which("wl-copy"):
            cmd = f'grim{region} - | tee "{path}" | wl-copy --type image/png'
        else:
            cmd = f'grim{region} "{path}"'
        if shutil.which("notify-send"):
            label = "Screenshot full" if full else "Screenshot"
            cmd += f' && notify-send -a qtile "{label}" "{path}"'
        subprocess.Popen(["sh", "-c", cmd])
    elif shutil.which("scrot"):
        args = ["scrot", path] if full else ["scrot", "-s", path]
        subprocess.Popen(args)
        _notify("Screenshot", path)
    elif shutil.which("flameshot"):
        subprocess.Popen(["flameshot", "gui" if not full else "full"])


def _volume_osd() -> None:
    """Brief OSD after media-key volume changes."""
    if not shutil.which("notify-send"):
        return
    try:
        if shutil.which("wpctl"):
            out = subprocess.check_output(
                ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            # "Volume: 0.50 [MUTED]" or "Volume: 0.50"
            muted = "[MUTED]" in out
            frac = float(out.split()[1])
            pct = int(round(frac * 100))
            body = "Muted" if muted else f"{pct}%"
        elif shutil.which("pactl"):
            mute = subprocess.check_output(
                ["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            muted = "yes" in mute
            vol = subprocess.check_output(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            # first percent in output
            m = re.search(r"(\d+)%", vol)
            pct = int(m.group(1)) if m else 0
            body = "Muted" if muted else f"{pct}%"
        else:
            return
        subprocess.Popen(
            ["notify-send", "-a", "qtile", "-r", "9910", "-t", "800", "Volume", body]
        )
    except (subprocess.CalledProcessError, ValueError, IndexError):
        pass


@lazy.function
def volume_adjust(qtile, delta: str):
    if shutil.which("wpctl"):
        if delta == "mute":
            subprocess.Popen(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
        else:
            subprocess.Popen(
                ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", delta]
            )
        _volume_osd()
        return
    if shutil.which("pactl"):
        if delta == "mute":
            subprocess.Popen(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
        elif delta.endswith("%+"):
            subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{delta[:-2]}%"])
        else:
            subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{delta[:-2]}%"])
        _volume_osd()
        return
    if shutil.which("amixer"):
        if delta == "mute":
            subprocess.Popen(["amixer", "-q", "set", "Master", "toggle"])
        elif delta.endswith("%+"):
            subprocess.Popen(["amixer", "-q", "set", "Master", f"{delta[:-2]}%+"])
        else:
            subprocess.Popen(["amixer", "-q", "set", "Master", f"{delta[:-2]}%-"])
        _volume_osd()


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
    # scratchpads
    Key([mod], "grave", lazy.group["scratchpad"].dropdown_toggle("term"), desc="Scratchpad terminal"),
    Key([mod, "shift"], "v", lazy.group["scratchpad"].dropdown_toggle("audio"), desc="Scratchpad volume"),
    # media / brightness / screenshots
    Key([], "Print", take_screenshot(), desc="Screenshot region"),
    Key(["shift"], "Print", take_screenshot(full=True), desc="Screenshot full"),
    Key([], "XF86AudioRaiseVolume", volume_adjust("5%+"), desc="Volume up"),
    Key([], "XF86AudioLowerVolume", volume_adjust("5%-"), desc="Volume down"),
    Key([], "XF86AudioMute", volume_adjust("mute"), desc="Volume mute"),
    Key([], "XF86AudioPlay", lazy.spawn("playerctl play-pause"), desc="Play/pause"),
    Key([], "XF86AudioNext", lazy.spawn("playerctl next"), desc="Next track"),
    Key([], "XF86AudioPrev", lazy.spawn("playerctl previous"), desc="Previous track"),
    Key([], "XF86MonBrightnessUp", lazy.spawn("brightnessctl -q s +10%"), desc="Brightness up"),
    Key([], "XF86MonBrightnessDown", lazy.spawn("brightnessctl -q s 10%-"), desc="Brightness down"),
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

# Keep names 1–9 for Super+N binds; labels are nerd-font icons in the bar.
groups = [
    Group(
        "1",
        label="󰖟",
        matches=[Match(wm_class=re.compile(r"brave|firefox|chromium|chrome|vivaldi", re.I))],
    ),
    Group(
        "2",
        label="󰨞",
        matches=[Match(wm_class=re.compile(r"code|cursor|jetbrains|zed|emacs|nvim", re.I))],
    ),
    Group(
        "3",
        label="",
        matches=[Match(wm_class=re.compile(r"ghostty|alacritty|wezterm|kitty|foot", re.I))],
    ),
    Group(
        "4",
        label="󰉋",
        matches=[Match(wm_class=re.compile(r"dolphin|thunar|nautilus|pcmanfm|nemo", re.I))],
    ),
    Group(
        "5",
        label="󰍩",
        matches=[Match(wm_class=re.compile(r"discord|slack|telegram|signal|element|zoom", re.I))],
    ),
    Group(
        "6",
        label="󰎈",
        matches=[Match(wm_class=re.compile(r"spotify|vlc|mpv|rhythmbox|elisa", re.I))],
    ),
    Group("7", label="󰃣"),
    Group(
        "8",
        label="󰈙",
        matches=[Match(wm_class=re.compile(r"libreoffice|soffice|evince|okular|zathura", re.I))],
    ),
    Group("9", label="󰀄"),
]

_scratch_dropdowns = [
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
    DropDown(
        "audio",
        "pavucontrol",
        opacity=0.95,
        width=0.5,
        height=0.6,
        x=0.25,
        y=0.15,
        on_focus_lost_hide=True,
    ),
]
_calc = next((c for c in ("kcalc", "qalculate-gtk", "gnome-calculator") if shutil.which(c)), None)
if _calc:
    _scratch_dropdowns.append(
        DropDown(
            "calc",
            _calc,
            opacity=0.95,
            width=0.35,
            height=0.45,
            x=0.325,
            y=0.2,
            on_focus_lost_hide=True,
        )
    )
    keys.append(
        Key(
            [mod, "shift"],
            "c",
            lazy.group["scratchpad"].dropdown_toggle("calc"),
            desc="Scratchpad calculator",
        )
    )
groups.append(ScratchPad("scratchpad", _scratch_dropdowns))

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


def _format_key(key: Key) -> str:
    names = {"mod4": "Super", "shift": "Shift", "control": "Ctrl", "mod1": "Alt"}
    parts = [names.get(m, m) for m in key.modifiers]
    parts.append(str(key.key))
    return "+".join(parts)


def keys_menu_cmd() -> str:
    theme = os.path.join(cfg_dir, "rofi", "catppuccin-mocha.rasi")
    theme_flag = f" -theme {theme}" if os.path.isfile(theme) else ""
    lines = [f"{_format_key(k)}\t{k.desc}" for k in keys if getattr(k, "desc", None)]
    body = "\n".join(lines)
    # ponytail: static snapshot at config load; reload after keybind edits
    script = (
        f"printf %s {shlex.quote(body)} | {rofi_bin()} -dmenu -i -p keys{theme_flag} >/dev/null"
    )
    return "sh -c " + repr(script)


keys.append(Key([mod], "F1", lazy.spawn(keys_menu_cmd()), desc="Keybind cheatsheet"))

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
FONT_SIZE = 14
ICON_SIZE = FONT_SIZE + 2
BAR_SIZE = 32

widget_defaults = dict(
    font=FONT,
    fontsize=FONT_SIZE,
    padding=6,
    foreground=colors["fg"],
    background=colors["bg"],
)
extension_defaults = widget_defaults.copy()


def _chip(colour: str | None = None):
    """Rounded surface behind a widget cluster (qtile-extras)."""
    try:
        from qtile_extras.widget.decorations import RectDecoration
    except ImportError:
        return []
    return [
        RectDecoration(
            colour=colour or colors["surface"],
            radius=9,
            filled=True,
            padding_y=5,
            padding_x=3,
            group=True,
        )
    ]


def _gap(width: int = 8):
    return widget.Spacer(length=width)


def _icon(text: str, colour: str, **kwargs):
    return widget.TextBox(
        text=text,
        foreground=colour,
        background=colors["bg"],
        padding=kwargs.pop("padding", 4),
        fontsize=ICON_SIZE,
        **kwargs,
    )


def _pipe():
    return widget.TextBox(
        text="󰇙",
        foreground=colors["overlay"],
        background=colors["bg"],
        padding=8,
        fontsize=FONT_SIZE - 2,
    )


def _tray():
    # Stock StatusNotifier has no DBus menus. nm-applet exposes only a menu
    # (no Activate), so clicks do nothing without qtile-extras.
    try:
        from qtile_extras.widget import StatusNotifier as Tray
    except ImportError:
        return widget.StatusNotifier(background=colors["bg"], padding=4)
    tray = Tray(
        background=colors["bg"],
        padding=6,
        icon_size=18,
        menu_font=FONT,
        menu_fontsize=FONT_SIZE,
        menu_background=colors["bg"],
        menu_foreground=colors["fg"],
        menu_foreground_disabled=colors["overlay"],
        menu_foreground_highlighted=colors["peach"],
        menu_border=colors["surface"],
        menu_border_width=0,
        highlight_colour=colors["surface"],
        separator_colour=colors["overlay"],
        # Wayland: default 0.5s auto-hide closes before pointer reaches the popup
        hide_after=5,
        decorations=_chip(),
    )
    # add_callbacks() is lower-priority and won't replace Button1=activate
    tray.mouse_callbacks["Button1"] = tray.show_menu
    return tray


def _volume():
    cbs = {
        "Button1": lazy.spawn("pavucontrol"),
        "Button3": volume_adjust("mute"),
        "Button4": volume_adjust("5%+"),
        "Button5": volume_adjust("5%-"),
    }
    kwargs = dict(
        update_interval=1,
        foreground=colors["green"],
        background=colors["bg"],
        padding=4,
        mouse_callbacks=cbs,
        mute_format="mute",
        unmute_format="{volume}%",
        decorations=_chip(),
    )
    # Prefer Pulse/PipeWire so the bar matches wpctl/pactl keybinds.
    # Qtile returns ImportErrorWidget instead of raising — check deps first.
    try:
        import pulsectl  # noqa: F401
        import pulsectl_asyncio  # noqa: F401
    except ImportError:
        return widget.Volume(step=5, **kwargs)
    return widget.PulseVolume(**kwargs)


class Battery(widget.Battery):
    """Battery widget using kernel capacity % and distinct charge-hold icon.

    Stock Qtile uses energy_now/energy_full (can lag). ASUS often reports
    status=Not charging near full while AC is connected — that is not a
    discharge, and percent will not rise until charging resumes.
    """

    def _capacity_status(self, status):
        try:
            name = f"BAT{self.battery}" if isinstance(self.battery, int) else str(self.battery)
            path = f"/sys/class/power_supply/{name}/capacity"
            if not os.path.isfile(path):
                path = "/sys/class/power_supply/BAT0/capacity"
            cap = int(open(path).read().strip())
            return status._replace(percent=max(0.0, min(cap / 100.0, 1.0)))
        except (OSError, ValueError):
            return status

    def build_string(self, status):
        return widget.Battery.build_string(self, self._capacity_status(status))


def _battery():
    return Battery(
        format="{char} {percent:2.0%}",
        charge_char="󰂄",
        discharge_char="󰁹",
        full_char="󰁹",
        empty_char="󰂎",
        unknown_char="󰂑",
        # plugged in but charge held (ASUS near-full) — not the discharge icon
        not_charging_char="󰚥",
        update_interval=10,
        show_short_text=False,
        low_percentage=0.2,
        low_foreground=colors["red"],
        foreground=colors["peach"],
        charging_foreground=colors["green"],
        background=colors["bg"],
        padding=4,
        fontsize=FONT_SIZE,
        decorations=_chip(),
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
        padding=4,
        decorations=_chip(),
    )


def _temp():
    try:
        import psutil  # noqa: F401
    except ImportError:
        return widget.TextBox("")
    temps = {}
    try:
        temps = psutil.sensors_temperatures() or {}
    except Exception:
        return widget.TextBox("")
    if not temps:
        return widget.TextBox("")
    # Prefer AMD CPU package temp when present
    tag = None
    for name, entries in temps.items():
        for entry in entries:
            label = (entry.label or "").strip()
            if label == "Tctl" or (name == "k10temp" and label):
                tag = label or None
                break
        if tag:
            break
    return widget.ThermalSensor(
        format="{temp:.0f}{unit}",
        tag_sensor=tag,
        threshold=80,
        foreground=colors["red"],
        foreground_alert=colors["red"],
        background=colors["bg"],
        padding=4,
        update_interval=2,
        decorations=_chip(),
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
        padding=4,
        decorations=_chip(),
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
            padding=4,
            change_command="brightnessctl set {0}%",
            decorations=_chip(),
        )
    except Exception:
        return widget.TextBox("")


class Awake(widget.TextBox):
    """Coffee icon: click keeps the screen on and blocks sleep; click again allows both."""

    def __init__(self, **config):
        config.setdefault("text", "\U000f0eb4")
        config.setdefault("fontsize", ICON_SIZE)
        config.setdefault("padding", 10)
        config.setdefault("foreground", colors["overlay"])
        config.setdefault("background", colors["bg"])
        config.setdefault("decorations", _chip())
        super().__init__(**config)
        self._pid = None
        self.add_callbacks({"Button1": self.toggle})

    def _pidfile(self) -> str:
        return os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "qtile-awake.pid")

    def _live_pid(self) -> int | None:
        try:
            pid = int(open(self._pidfile()).read().strip())
        except (OSError, ValueError):
            return None
        try:
            os.kill(pid, 0)
        except OSError:
            return None
        return pid

    def _configure(self, qtile, bar):
        widget.TextBox._configure(self, qtile, bar)
        self._restore()

    def _paint(self, on: bool) -> None:
        if on:
            self.text = "\U000f0176"  # coffee
            self.foreground = colors["bg"]
            self.background = colors["green"]
        else:
            self.text = "\U000f0eb4"  # coffee off
            self.foreground = colors["overlay"]
            self.background = colors["surface"]
        if self.layout:
            self.layout.colour = self.foreground
            self.layout.text = self.text
        if self.bar:
            self.bar.draw()

    def _restore(self):
        self._pid = self._live_pid()
        if self._pid:
            self._hold(True)
        self._paint(bool(self._pid))

    def _hold(self, on: bool) -> None:
        mgr = getattr(self.qtile.core, "idle_inhibitor_manager", None)
        if mgr is not None:
            (mgr.add_global_inhibitor if on else mgr.remove_global_inhibitor)()
        # ponytail: SIGSTOP swayidle so the 5-minute lock cannot fire while this is on.
        # Ceiling: only the autostart swayidle. Drop the signal if a compositor inhibitor alone pauses it.
        subprocess.run(["pkill", "-STOP" if on else "-CONT", "-x", "swayidle"], check=False)

    def toggle(self):
        if self._live_pid():
            self._off()
        else:
            self._on()

    def _on(self):
        self._hold(True)
        proc = subprocess.Popen(
            [
                "systemd-inhibit",
                "--what=idle:sleep:handle-lid-switch",
                "--who=Awake",
                "--why=Keep screen on",
                "--mode=block",
                "sleep",
                "infinity",
            ],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._pid = proc.pid
        with open(self._pidfile(), "w") as fh:
            fh.write(str(proc.pid))
        self._paint(True)

    def _off(self):
        self._hold(False)
        pid = self._pid or self._live_pid()
        if pid:
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
        self._pid = None
        try:
            os.remove(self._pidfile())
        except OSError:
            pass
        self._paint(False)


def _awake():
    return Awake()


def init_widgets():
    return [
        _gap(6),
        _icon("", colors["blue"], padding=6, decorations=_chip(colors["surface"])),
        widget.CurrentLayout(
            fmt="{}",
            foreground=colors["blue"],
            background=colors["bg"],
            padding=6,
            decorations=_chip(),
        ),
        _gap(10),
        widget.GroupBox(
            font=FONT,
            fontsize=ICON_SIZE,
            margin_y=3,
            margin_x=2,
            padding_y=4,
            padding_x=8,
            borderwidth=2,
            disable_drag=True,
            rounded=True,
            highlight_method="block",
            highlight_color=[colors["surface"], colors["surface"]],
            this_current_screen_border=colors["peach"],
            this_screen_border=colors["surface"],
            other_current_screen_border=colors["lavender"],
            other_screen_border=colors["surface"],
            urgent_border=colors["red"],
            urgent_text=colors["bg"],
            active=colors["fg"],
            inactive=colors["overlay"],
            background=colors["bg"],
            foreground=colors["fg"],
            block_highlight_text_color=colors["bg"],
            hide_unused=True,
            spacing=4,
        ),
        widget.Prompt(foreground=colors["green"], background=colors["bg"], padding=8),
        _gap(10),
        _icon("", colors["teal"], decorations=_chip()),
        widget.WindowName(
            foreground=colors["fg"],
            background=colors["bg"],
            max_chars=42,
            padding=6,
            decorations=_chip(),
        ),
        widget.Spacer(),
        _icon("󰍛", colors["mauve"], decorations=_chip()),
        _cpu(),
        _gap(6),
        _icon("󰔏", colors["red"], decorations=_chip()),
        _temp(),
        _gap(6),
        _icon("󰘚", colors["teal"], decorations=_chip()),
        _mem(),
        _gap(6),
        _icon("󰃠", colors["yellow"], decorations=_chip()),
        _backlight(),
        _gap(6),
        _icon("󰕾", colors["green"], decorations=_chip()),
        _volume(),
        _gap(6),
        _battery(),
        _gap(6),
        _icon("󰃭", colors["blue"], decorations=_chip()),
        widget.Clock(
            format="%d %b",
            foreground=colors["blue"],
            background=colors["bg"],
            padding=4,
            decorations=_chip(),
        ),
        _gap(6),
        _icon("", colors["lavender"], decorations=_chip()),
        widget.Clock(
            format="%I:%M %p",
            foreground=colors["lavender"],
            background=colors["bg"],
            padding=6,
            decorations=_chip(),
        ),
        _gap(8),
        _awake(),
        _gap(6),
        _tray(),
        _gap(6),
        widget.QuickExit(
            default_text="󰐥",
            countdown_format="{}",
            foreground=colors["red"],
            background=colors["bg"],
            padding=10,
            fontsize=ICON_SIZE,
            decorations=_chip(),
        ),
        _gap(8),
    ]


def make_screen():
    return Screen(
        top=bar.Bar(
            init_widgets(),
            BAR_SIZE,
            background=colors["bg"],
            margin=[4, 8, 0, 8],
            border_width=[0, 0, 0, 0],
            border_color=[colors["bg"], colors["bg"], colors["bg"], colors["bg"]],
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
