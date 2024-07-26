
import os
import re
import socket
import subprocess
from typing import List  # noqa: F401
from libqtile import layout, bar, widget, hook, qtile
from libqtile.config import Click, Drag, Group, Key, Match, Screen, Rule, KeyChord
from libqtile.lazy import lazy
from libqtile.widget import Spacer
from qtile_extras import widget
from qtile_extras.widget.decorations import BorderDecoration
from libqtile.lazy import lazy
from libqtile.utils import guess_terminal
import arcobattery
from qtile_extras.widget.decorations import RectDecoration

#mod4 or mod = super key
mod = "mod4"
mod1 = "alt"
mod2 = "control"
home = os.path.expanduser('~')


@lazy.function
def window_to_prev_group(qtile):
    if qtile.currentWindow is not None:
        i = qtile.groups.index(qtile.currentGroup)
        qtile.currentWindow.togroup(qtile.groups[i - 1].name)

@lazy.function
def window_to_next_group(qtile):
    if qtile.currentWindow is not None:
        i = qtile.groups.index(qtile.currentGroup)
        qtile.currentWindow.togroup(qtile.groups[i + 1].name)

keys = [
    
    # Key([mod, "shift"], "m", minimize_all(), desc="Toggle hide/show all windows on current group"),



    # Most of our keybindings are in sxhkd file - except these
    Key([], "XF86MonBrightnessUp", lazy.spawn("brightnessctl -q s +10%")),
    Key([], "XF86MonBrightnessDown", lazy.spawn("brightnessctl -q s 10%-")),


    # SUPER + FUNCTION KEYS

    Key([mod], "f", lazy.window.toggle_fullscreen()),
    # Key([mod2], "space", lazy.layout.next(), desc="Move window focus to other window"),
    # Key([mod2], "n", lazy.layout.next(), desc="Move window focus to other window"),


    # SUPER + SHIFT KEYS

    Key([mod, "shift"], "c", lazy.window.kill()),
    Key([mod, "shift"], "r", lazy.restart()),

    # QTILE LAYOUT KEYS
    Key([mod], "n", lazy.layout.normalize()),
    Key([mod], "m", lazy.layout.maximize()),
    # Key([mod], "space", lazy.next_layout()),
    Key([mod], "tab", lazy.next_layout()),

    # CHANGE FOCUS
    Key([mod], "Up", lazy.layout.up()),
    Key([mod], "Down", lazy.layout.down()),
    Key([mod], "Left", lazy.layout.left()),
    Key([mod], "Right", lazy.layout.right()),
    Key([mod], "k", lazy.layout.up()),
    Key([mod], "j", lazy.layout.down()),
    Key([mod], "h", lazy.layout.left()),
    Key([mod], "l", lazy.layout.right()),


    # RESIZE UP, DOWN, LEFT, RIGHT
    Key([mod, "control"], "l",
        lazy.layout.grow_right(),
        lazy.layout.grow(),
        lazy.layout.increase_ratio(),
        lazy.layout.delete(),
        ),
    Key([mod, "control"], "Right",
        lazy.layout.grow_right(),
        lazy.layout.grow(),
        lazy.layout.increase_ratio(),
        lazy.layout.delete(),
        ),
    Key([mod, "control"], "h",
        lazy.layout.grow_left(),
        lazy.layout.shrink(),
        lazy.layout.decrease_ratio(),
        lazy.layout.add(),
        ),
    Key([mod, "control"], "Left",
        lazy.layout.grow_left(),
        lazy.layout.shrink(),
        lazy.layout.decrease_ratio(),
        lazy.layout.add(),
        ),
    Key([mod, "control"], "k",
        lazy.layout.grow_up(),
        lazy.layout.grow(),
        lazy.layout.decrease_nmaster(),
        ),
    Key([mod, "control"], "Up",
        lazy.layout.grow_up(),
        lazy.layout.grow(),
        lazy.layout.decrease_nmaster(),
        ),
    Key([mod, "control"], "j",
        lazy.layout.grow_down(),
        lazy.layout.shrink(),
        lazy.layout.increase_nmaster(),
        ),
    Key([mod, "control"], "Down",
        lazy.layout.grow_down(),
        lazy.layout.shrink(),
        lazy.layout.increase_nmaster(),
        ),

    # Switch focus of monitors
    Key([mod], "period", lazy.next_screen(),
        desc='Move focus to next monitor'),
    Key([mod], "comma", lazy.prev_screen(), desc='Move focus to prev monitor'),

    # screenshort
    Key([mod], "p", lazy.spawn("gnome-screenshot -a")),
    Key([], "Print", lazy.spawn("gnome-screenshot -i")),


    # FLIP LAYOUT FOR MONADTALL/MONADWIDE
    Key([mod, "shift"], "f", lazy.layout.flip()),

    # FLIP LAYOUT FOR BSP
    Key([mod, "mod1"], "k", lazy.layout.flip_up()),
    Key([mod, "mod1"], "j", lazy.layout.flip_down()),
    Key([mod, "mod1"], "l", lazy.layout.flip_right()),
    Key([mod, "mod1"], "h", lazy.layout.flip_left()),

    # MOVE WINDOWS UP OR DOWN BSP LAYOUT
    Key([mod, "shift"], "k", lazy.layout.shuffle_up()),
    Key([mod, "shift"], "j", lazy.layout.shuffle_down()),
    Key([mod, "shift"], "h", lazy.layout.shuffle_left()),
    Key([mod, "shift"], "l", lazy.layout.shuffle_right()),

    # MOVE WINDOWS UP OR DOWN MONADTALL/MONADWIDE LAYOUT
    Key([mod, "shift"], "Up", lazy.layout.shuffle_up()),
    Key([mod, "shift"], "Down", lazy.layout.shuffle_down()),
    Key([mod, "shift"], "Left", lazy.layout.swap_left()),
    Key([mod, "shift"], "Right", lazy.layout.swap_right()),

    # TOGGLE FLOATING LAYOUT
    # Key([mod, "shift"], "space", lazy.window.toggle_floating()),
    Key([mod], "t", lazy.window.toggle_floating(), desc='toggle floating'),

    # Grow/shrink windows left/right.
    # This is mainly for the 'monadtall' and 'monadwide' layouts
    # although it does also work in the 'bsp' and 'columns' layouts.
    Key([mod], "equal",
        lazy.layout.grow_left().when(layout=["bsp", "columns"]),
        lazy.layout.grow().when(layout=["monadtall", "monadwide"]),
        desc="Grow window to the left"
        ),
    Key([mod], "minus",
        lazy.layout.grow_right().when(layout=["bsp", "columns"]),
        lazy.layout.shrink().when(layout=["monadtall", "monadwide"]),
        desc="Grow window to the left"
        ),

    # Toggle between split and unsplit sides of stack.
    # Split = all windows displayed
    # Unsplit = 1 window displayed, like Max layout, but still with
    # multiple stack panes
    Key([mod, "shift"], "space", lazy.layout.toggle_split(),
        desc="Toggle between split and unsplit sides of stack"),
    ]

def window_to_previous_screen(qtile, switch_group=False, switch_screen=False):
    i = qtile.screens.index(qtile.current_screen)
    if i != 0:
        group = qtile.screens[i - 1].group.name
        qtile.current_window.togroup(group, switch_group=switch_group)
        if switch_screen == True:
            qtile.cmd_to_screen(i - 1)

def window_to_next_screen(qtile, switch_group=False, switch_screen=False):
    i = qtile.screens.index(qtile.current_screen)
    if i + 1 != len(qtile.screens):
        group = qtile.screens[i + 1].group.name
        qtile.current_window.togroup(group, switch_group=switch_group)
        if switch_screen == True:
            qtile.cmd_to_screen(i + 1)

# keys.extend([
#     # MOVE WINDOW TO NEXT SCREEN
#     Key([mod,"shift"], "Right", lazy.function(window_to_next_screen, switch_screen=True)),
#     Key([mod,"shift"], "Left", lazy.function(window_to_previous_screen, switch_screen=True)),
# ])

keys.extend([
    # MOVE WINDOW TO NEXT SCREEN
    Key([mod, "shift"], "Right", lazy.function(
        window_to_next_screen, switch_screen=True)),
    Key([mod, "shift"], "Left", lazy.function(
        window_to_previous_screen, switch_screen=True)),
    Key([mod, "shift"], "period", lazy.function(
        window_to_next_screen, switch_screen=True)),
    Key([mod, "shift"], "comma", lazy.function(
        window_to_previous_screen, switch_screen=True)),
])

groups = []

# FOR QWERTY KEYBOARDS
group_names = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0",]

# FOR AZERTY KEYBOARDS
#group_names = ["ampersand", "eacute", "quotedbl", "apostrophe", "parenleft", "section", "egrave", "exclam", "ccedilla", "agrave",]

group_labels = ["1 ", "2 ", "3 ", "4 ", "5 ", "6 ", "7 ", "8 ", "9 ", "0",]
# group_labels = ["", "", "", "", "", "", "", "", "", "",]
# group_labels = ["१ ", "२ ", "३ ", "४ ", "५ ", "६ ", "७ ", "८ ", "९ ", "० ",]
#group_labels = ["Web", "Edit/chat", "Image", "Gimp", "Meld", "Video", "Vb", "Files", "Mail", "Music",]

group_layouts = ["monadtall", "monadtall", "monadtall", "monadtall", "monadtall", "monadtall", "monadtall", "monadtall", "monadtall", "monadtall",]
#group_layouts = ["monadtall", "matrix", "monadtall", "bsp", "monadtall", "matrix", "monadtall", "bsp", "monadtall", "monadtall",]

for i in range(len(group_names)):
    groups.append(
        Group(
            name=group_names[i],
            layout=group_layouts[i].lower(),
            label=group_labels[i],
        ))

# for i in groups:
#     keys.extend([
#
# #CHANGE WORKSPACES
#         Key([mod], i.name, lazy.group[i.name].toscreen()),
#         Key([mod], "Tab", lazy.screen.next_group()),
#         Key([mod, "shift" ], "Tab", lazy.screen.prev_group()),
#         Key(["mod1"], "Tab", lazy.screen.next_group()),
#         Key(["mod1", "shift"], "Tab", lazy.screen.prev_group()),
#
# # MOVE WINDOW TO SELECTED WORKSPACE 1-10 AND STAY ON WORKSPACE
#         #Key([mod, "shift"], i.name, lazy.window.togroup(i.name)),
# # MOVE WINDOW TO SELECTED WORKSPACE 1-10 AND FOLLOW MOVED WINDOW TO WORKSPACE
#         Key([mod, "shift"], i.name, lazy.window.togroup(i.name) , lazy.group[i.name].toscreen()),
#     ])

for i in groups:
    keys.extend([

        # CHANGE WORKSPACES
        Key([mod], i.name, lazy.group[i.name].toscreen()),
        # Key([mod], "Tab", lazy.screen.next_group()),
        # Key([mod, "shift" ], "Tab", lazy.screen.prev_group()),
        # Key(["mod1"], "Tab", lazy.screen.next_group()),
        # Key(["mod1", "shift"], "Tab", lazy.screen.prev_group()),
        Key([mod, "control"], "period", lazy.screen.next_group()),
        Key([mod, "control"], "comma", lazy.screen.prev_group()),

        # MOVE WINDOW TO SELECTED WORKSPACE 1-10 AND STAY ON WORKSPACE
        # Key([mod, "shift"], i.name, lazy.window.togroup(i.name)),
        # MOVE WINDOW TO SELECTED WORKSPACE 1-10 AND FOLLOW MOVED WINDOW TO WORKSPACE
        Key([mod, "shift"], i.name, lazy.window.togroup(
            i.name), lazy.group[i.name].toscreen()),
    ])


def init_layout_theme():
    return {"margin":5,
            "border_width": 4,
            "border_focus": "#5A4FCF",
            "border_normal": "#002147"
            }

layout_theme = init_layout_theme()


layouts = [
     # layout.MonadTall(margin=8, border_width=2, border_focus="#5e81ac", border_normal="#4c566a"),
    layout.MonadTall(**layout_theme),
    layout.Columns(**layout_theme),
    # layout.MonadWide(margin=8, border_width=2, border_focus="#5e81ac", border_normal="#4c566a"),
    # layout.MonadWide(**layout_theme),
    # layout.Matrix(**layout_theme),
    # layout.Bsp(**layout_theme),
    # layout.Floating(**layout_theme),
    # layout.RatioTile(**layout_theme),
    layout.Max(**layout_theme),
    layout.TreeTab(
        fontsize=10,
        sections=["FIRST", "SECOND", "THIRD", "FOURTH"],
        section_fontsize=10,
        border_width=2,
        bg_color="1c1f24",
        active_bg="c678dd",
        active_fg="000000",
        inactive_bg="a9a1e1",
        inactive_fg="1c1f24",
        padding_left=0,
        padding_x=0,
        padding_y=5,
        section_top=10,
        section_bottom=20,
        level_shift=8,
        vspace=3,
        panel_width=180
    ),
    # layout.Tile(shift_windows=True, **layout_theme),
    # layout.Stack(**layout_theme, num_stacks=2),
    # layout.VerticalTile(**layout_theme),
    layout.Zoomy(**layout_theme),
]


def init_colors():
    return [["#24273A", "#24273A"],  # color 0
            ["#020403", "#020403"],  # color 1
            ["#5ea2ff", "#5ea2ff"],  # color 2
            ["#3d2aff", "#3d2aff"],  # color 3
            ["#28b9ff", "#28b9ff"],  # color 4
            ["#5ac8ff", "#5ac8ff"],  # color 5
            ["#a52aff", "#a52aff"],  # color 6
            ["#7129ff", "#7129ff"],  # color 7
            ["#bd93f9", "#bd93f9"],  # color 8
            ["#2b4fff", "#2b4fff"]]  # color 9


colors = init_colors()


# WIDGETS FOR THE BAR

def init_widgets_defaults():
    return dict(font="Noto Sans Bold",
                fontsize=16,
                padding=2,
                background=colors[1])


widget_defaults = init_widgets_defaults()

def init_widgets_list():
    prompt = "{0}@{1}: ".format(os.environ["USER"], socket.gethostname())
    widgets_list = [
                widget.Spacer(length=8),
                widget.CurrentLayoutIcon(
                    foreground=colors[1],
                    padding=2,
                    scale=0.9,
                ),
                widget.Sep(
                    linewidth=2,
                    padding=10,
                    foreground=colors[2],
                    background=colors[1]
                ),
               widget.GroupBox(font="Noto Sans Bold",
                    fontsize = 19,
                    margin = 2,
                    padding = 2,
                    borderwidth = 0,
                    disable_drag = True,
                    active = colors[9],
                    inactive = colors[5],
                    rounded = False,
                    highlight_method = "text",
                    this_current_screen_border = colors[8],
                    foreground = colors[2],
                    background = colors[1],
                    decorations = [
                        RectDecoration (
                            line_colour = colors[2],
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Sep(
                    linewidth=2,
                    padding=10,
                    foreground=colors[2],
                    background=colors[1]
                ),
                widget.WindowName(font="Noto Sans Bold",
                                  fontsize=17,
                                  foreground=colors[5],
                                  # background = colors[1],
                                  background=colors[1],
                                    decorations = [
                                        RectDecoration (
                                            line_colour = colors[5],
                                            line_width = 2,
                                            radius = 2,
                                            filled = True,
                                        ),
                                    ],
                                  ),
                # widget.Spacer(length=8),
                # widget.GenPollText(
                #     update_interval=300,
                #     func=lambda: subprocess.check_output(
                #         "printf $(uname -r)", shell=True, text=True),
                #     foreground="#6666ff",
                #     background=colors[1],
                #     fmt='   {}',
                # ),
                # widget.Spacer(length=8),
                # widget.TextBox(
                #     text="󰣇  󰚗  ",
                #     fontsize=27,
                #     padding=0,
                #     foreground="#ff5555"
                # ),
                widget.Spacer(length=8),
                # widget.Net(
                #     # format = 'Net: {down} ↓↑ {up}',
                #     foreground=colors[3],
                #     background=colors[1],
                #     padding=3,
                #     format='ᯤ : {down:.0f}{down_suffix} ↓↑ {up:.0f}{up_suffix}',
                #     width=135,
                # ),
                widget.Net(
                    # format = 'Net: {down} ↓↑ {up}',
                    foreground=colors[3],
                    background=colors[1],
                    padding=4,
                    format='ᯤ : {down:.0f}{down_suffix} ↓↑ {up:.0f}{up_suffix}',
                    width=135,
                    decorations = [
                        RectDecoration (
                            line_colour = colors[3],
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                # widget.Spacer(length=8),
                # widget.KeyboardLayout(
                #     foreground=colors[4],
                #     background=colors[1],
                #     fmt='⌨  Kbd: {}',
                # ),
                widget.Spacer(length=8),
                widget.DF(
                    update_interval=60,
                    padding=6,
                    foreground=colors[5],
                    background=colors[1],
                    mouse_callbacks={
                        'Button1': lambda: qtile.cmd_spawn(myTerm + ' -e df')},
                    partition='/',
                    # format = '[{p}] {uf}{m} ({r:.0f}%)',
                    format='{uf}{m} free',
                    fmt='🖴  : {}',
                    visible_on_warn=False,
                    decorations = [
                        RectDecoration (
                            line_colour = colors[5],
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Spacer(length=8),
                widget.Memory(
                    padding=6,
                    foreground=colors[8],
                    background=colors[1],
                    mouse_callbacks={
                        'Button1': lambda: qtile.cmd_spawn(myTerm + ' -e htop')},
                    format='{MemUsed: .0f}{mm}',
                    fmt='🖥: {} used',
                    decorations = [
                        RectDecoration (
                            line_colour = colors[8],
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Spacer(length=8),
                widget.Volume(
                    foreground=colors[7],
                    background=colors[1],
                    fmt='🕫 : {}',
                    padding=None,
                    decorations = [
                        RectDecoration (
                            line_colour = colors[7],
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Spacer(length=8),
                widget.CPU(
                    padding=6,
                    format='回 : {load_percent}%',
                    foreground=colors[6],
                    background=colors[1],
                    width=88,
                    decorations = [
                        RectDecoration (
                            line_colour = colors[6],
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Spacer(length=8),
                widget.NvidiaSensors(
                    padding=6,
                    background=colors[1],
                    # foreground="#F5A97F",
                    foreground="#5c78ff",
                    threshold=70,
                    fmt='🌡: {}',
                    decorations = [
                        RectDecoration (
                            line_colour = "#5c78ff",
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Spacer(length=8),
                widget.Clock(
                    foreground=colors[9],
                    background=colors[1],
                    format="⏱  %a, %b %d - %I:%M %p",
                    padding=None,
                    decorations = [
                        RectDecoration (
                            line_colour = colors[9],
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Spacer(length=8),
                arcobattery.BatteryIcon(
                    padding=0,
                    scale=0.7,
                    y_poss=2,
                    theme_path=home + "/.config/qtile/icons/battery_icons_horiz",
                    update_interval=5,
                    background=colors[1],
                    decorations = [
                        RectDecoration (
                            line_colour = "#8f00ff",
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Battery(
                    padding=4,
                    format = "{percent:0.1%}",
                    foreground = "#1CFFB7",
                    decorations = [
                        RectDecoration (
                            line_colour = "#1cffb7",
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
                ),
                widget.Spacer(length=8),
                widget.Systray(
                    padding=4,
                    decorations = [
                        RectDecoration (
                            line_colour = "#8f00ff",
                            line_width = 2,
                            radius = 2,
                            filled = True,
                        ),
                    ],
               ),
                widget.Spacer(length=8),
              ]
    return widgets_list

widgets_list = init_widgets_list()


def init_widgets_screen1():
    widgets_screen1 = init_widgets_list()
    return widgets_screen1

def init_widgets_screen2():
    widgets_screen2 = init_widgets_list()
    return widgets_screen2

widgets_screen1 = init_widgets_screen1()
widgets_screen2 = init_widgets_screen2()

def init_screens():
    return [Screen(
            top=bar.Bar(widgets=init_widgets_screen1(), size=26, opacity=0.7,)),
            Screen(top=bar.Bar(widgets=init_widgets_screen2(), size=22, opacity=0.7 )),
            Screen(top=bar.Bar(widgets=init_widgets_screen2(), size=20, opacity=0.7 ))]

screens = init_screens()

mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(),
         start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(),
         start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.bring_to_front()),
]

dgroups_key_binder = None
dgroups_app_rules = []

# ASSIGN APPLICATIONS TO A SPECIFIC GROUPNAME
# BEGIN

#########################################################
################ assgin apps to groups ##################
#########################################################
# @hook.subscribe.client_new
# def assign_app_group(client):
#     d = {}
#     #####################################################################################
#     ### Use xprop fo find  the value of WM_CLASS(STRING) -> First field is sufficient ###
#     #####################################################################################
#     d[group_names[0]] = ["Navigator", "Firefox", "Vivaldi-stable", "Vivaldi-snapshot", "Chromium", "Google-chrome", "Brave", "Brave-browser",
#               "navigator", "firefox", "vivaldi-stable", "vivaldi-snapshot", "chromium", "google-chrome", "brave", "brave-browser", ]
#     d[group_names[1]] = [ "Atom", "Subl", "Geany", "Brackets", "Code-oss", "Code", "TelegramDesktop", "Discord",
#                "atom", "subl", "geany", "brackets", "code-oss", "code", "telegramDesktop", "discord", ]
#     d[group_names[2]] = ["Inkscape", "Nomacs", "Ristretto", "Nitrogen", "Feh",
#               "inkscape", "nomacs", "ristretto", "nitrogen", "feh", ]
#     d[group_names[3]] = ["Gimp", "gimp" ]
#     d[group_names[4]] = ["Meld", "meld", "org.gnome.meld" "org.gnome.Meld" ]
#     d[group_names[5]] = ["Vlc","vlc", "Mpv", "mpv" ]
#     d[group_names[6]] = ["VirtualBox Manager", "VirtualBox Machine", "Vmplayer",
#               "virtualbox manager", "virtualbox machine", "vmplayer", ]
#     d[group_names[7]] = ["Thunar", "Nemo", "Caja", "Nautilus", "org.gnome.Nautilus", "Pcmanfm", "Pcmanfm-qt",
#               "thunar", "nemo", "caja", "nautilus", "org.gnome.nautilus", "pcmanfm", "pcmanfm-qt", ]
#     d[group_names[8]] = ["Evolution", "Geary", "Mail", "Thunderbird",
#               "evolution", "geary", "mail", "thunderbird" ]
#     d[group_names[9]] = ["Spotify", "Pragha", "Clementine", "Deadbeef", "Audacious",
#               "spotify", "pragha", "clementine", "deadbeef", "audacious" ]
#     ######################################################################################
#
# wm_class = client.window.get_wm_class()[0]
#
#     for i in range(len(d)):
#         if wm_class in list(d.values())[i]:
#             group = list(d.keys())[i]
#             client.togroup(group)
#             client.group.cmd_toscreen(toggle=False)

# END
# ASSIGN APPLICATIONS TO A SPECIFIC GROUPNAME

main = None

# hides the top bar when the archlinux-logout widget is opened
@hook.subscribe.client_new
def new_client(window):
    if window.name == "ArchLinux Logout":
        qtile.hide_show_bar()

# shows the top bar when the archlinux-logout widget is closed
@hook.subscribe.client_killed
def logout_killed(window):
    if window.name == "ArchLinux Logout":
        qtile.hide_show_bar()

@hook.subscribe.startup_once
def start_once():
    home = os.path.expanduser('~')
    subprocess.call([home + '/.config/qtile/scripts/autostart.sh'])

@hook.subscribe.startup
def start_always():
    # Set the cursor to something sane in X
    subprocess.Popen(['xsetroot', '-cursor_name', 'left_ptr'])

@hook.subscribe.client_new
def set_floating(window):
    if (window.window.get_wm_transient_for()
            or window.window.get_wm_type() in floating_types):
        window.floating = True

floating_types = ["notification", "toolbar", "splash", "dialog"]


follow_mouse_focus = True
bring_front_click = False
cursor_warp = False
floating_layout = layout.Floating(float_rules=[
    # Run the utility of `xprop` to see the wm class and name of an X client.
    *layout.Floating.default_float_rules,
    Match(wm_class='confirmreset'),  # gitk
    Match(wm_class='makebranch'),  # gitk
    Match(wm_class='maketag'),  # gitk
    Match(wm_class='ssh-askpass'),  # ssh-askpass
    Match(title='branchdialog'),  # gitk
    Match(title='pinentry'),  # GPG key password entry
    Match(wm_class='Arcolinux-welcome-app.py'),
    Match(wm_class='Arcolinux-calamares-tool.py'),
    Match(wm_class='confirm'),
    Match(wm_class='dialog'),
    Match(wm_class='download'),
    Match(wm_class='error'),
    Match(wm_class='file_progress'),
    Match(wm_class='notification'),
    Match(wm_class='splash'),
    Match(wm_class='toolbar'),
    Match(wm_class='Arandr'),
    Match(wm_class='feh'),
    Match(wm_class='Galculator'),
    Match(wm_class='archlinux-logout'),
    Match(wm_class='xfce4-terminal'),

],  fullscreen_border_width = 0, border_width = 0)
auto_fullscreen = True

focus_on_window_activation = "focus" # or smart

wmname = "LG3D"
