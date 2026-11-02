# Qtile config — standard keybindings (upstream defaults), X11-focused, stable.
# https://docs.qtile.org/en/latest/manual/config/lazy.html
import os
import subprocess

from libqtile import bar, hook, layout, qtile, widget
from libqtile.config import Click, Drag, Group, Key, Match, Screen
from libqtile.lazy import lazy
from libqtile.utils import guess_terminal

mod = "mod4"
terminal = guess_terminal()
cfg_dir = os.path.dirname(os.path.abspath(__file__))
wallpaper = os.path.join(cfg_dir, "wallpaper", "jujutsu.jpg")

keys = [
    # focus
    Key([mod], "h", lazy.layout.left(), desc="Focus left"),
    Key([mod], "l", lazy.layout.right(), desc="Focus right"),
    Key([mod], "j", lazy.layout.down(), desc="Focus down"),
    Key([mod], "k", lazy.layout.up(), desc="Focus up"),
    Key([mod], "space", lazy.layout.next(), desc="Focus next window"),
    # move
    Key([mod, "shift"], "h", lazy.layout.shuffle_left(), desc="Move window left"),
    Key([mod, "shift"], "l", lazy.layout.shuffle_right(), desc="Move window right"),
    Key([mod, "shift"], "j", lazy.layout.shuffle_down(), desc="Move window down"),
    Key([mod, "shift"], "k", lazy.layout.shuffle_up(), desc="Move window up"),
    # grow
    Key([mod, "control"], "h", lazy.layout.grow_left(), desc="Grow left"),
    Key([mod, "control"], "l", lazy.layout.grow_right(), desc="Grow right"),
    Key([mod, "control"], "j", lazy.layout.grow_down(), desc="Grow down"),
    Key([mod, "control"], "k", lazy.layout.grow_up(), desc="Grow up"),
    Key([mod], "n", lazy.layout.normalize(), desc="Normalize window sizes"),
    # layout / session
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
    # media / brightness (no mod — do not overlap WM binds)
    Key([], "XF86AudioRaiseVolume", lazy.spawn("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+")),
    Key([], "XF86AudioLowerVolume", lazy.spawn("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-")),
    Key([], "XF86AudioMute", lazy.spawn("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle")),
    Key([], "XF86MonBrightnessUp", lazy.spawn("brightnessctl -q s +10%")),
    Key([], "XF86MonBrightnessDown", lazy.spawn("brightnessctl -q s 10%-")),
]

# Wayland VT switching (no-op on X11 via .when)
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
)
extension_defaults = widget_defaults.copy()

screens = [
    Screen(
        top=bar.Bar(
            [
                widget.CurrentLayout(),
                widget.GroupBox(
                    highlight_method="line",
                    this_current_screen_border="#7aa2f7",
                    active="#c0caf5",
                    inactive="#565f89",
                    disable_drag=True,
                ),
                widget.Prompt(),
                widget.WindowName(foreground="#c0caf5"),
                widget.Chord(
                    chords_colors={"launch": ("#ff0000", "#ffffff")},
                    name_transform=lambda name: name.upper(),
                ),
                widget.Systray(padding=6),
                widget.Volume(fmt="vol {}", step=5),
                widget.Battery(
                    format="{char} {percent:2.0%}",
                    charge_char="↑",
                    discharge_char="↓",
                    full_char="=",
                    unknown_char="?",
                    update_interval=30,
                    show_short_text=False,
                ),
                widget.Clock(format="%Y-%m-%d %a %H:%M"),
                widget.QuickExit(default_text="[exit]", countdown_format="[{}]"),
            ],
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
wl_input_rules = None
wl_xcursor_theme = None
wl_xcursor_size = 24
wmname = "LG3D"


@hook.subscribe.startup_once
def _autostart():
    script = os.path.join(cfg_dir, "scripts", "autostart.sh")
    if os.path.isfile(script):
        subprocess.Popen(["/bin/bash", script])
