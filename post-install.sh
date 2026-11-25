#!/usr/bin/env bash
# CachyOS / Arch post-install — mirrors ROG Zephyrus G14 (GA401IH) setup:
#   AMD Renoir iGPU + NVIDIA GTX 1650 Max-Q, btrfs + zram, docker,
#   hybrid NVIDIA open modules, CLI/dev toolchain from host "arch".
#   (no browsers, no desktop environment)
#
# Run as a normal wheel user AFTER base install + first boot.
#   curl / scp this file onto the machine, then:  bash post-install.sh
#
# Env knobs:
#   SKIP_AUR=1          skip paru + AUR packages
#   SKIP_NVIDIA=1       skip NVIDIA stack (AMD-only)
#   SKIP_CACHYOS=1      treat as vanilla Arch (skip cachyos-* packages)
#   SKIP_QTILE=1        skip Qtile WM setup (packages + config + sessions)
#   QTILE_SRC=/path     local Qtile repo (default: sibling ../Qtile or GitHub clone)
#   EXTRA_PKGS="..."    space-separated extra pacman packages
#   PAC_OVERWRITE=0     set to disable --overwrite '*' on file conflicts
set -euo pipefail

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Run as a normal user with sudo, not as root."
  exit 1
fi

if ! command -v pacman >/dev/null 2>&1; then
  echo "pacman not found — this script is for Arch/CachyOS."
  exit 1
fi

SUDO="sudo"
IS_CACHYOS=0
if [[ "${SKIP_CACHYOS:-0}" != "1" ]] && { pacman -Qq cachyos-keyring &>/dev/null || grep -q '\[cachyos' /etc/pacman.conf 2>/dev/null; }; then
  IS_CACHYOS=1
fi

FAILED_PKGS=()
RESOLVED_CONFLICTS=()

echo "==> Host: $(hostname) | CachyOS=${IS_CACHYOS} | user=$(whoami)"

# ---------------------------------------------------------------------------
# helpers — conflict-aware installs (never abort the whole script)
# ---------------------------------------------------------------------------

# Drop installed pkgs that target Conflicts With / Replaces (and common rivals).
resolve_conflicts_for() {
  local pkg="$1"
  local info conflicts replaces rival
  local -a drop=()

  info="$(pacman -Si "$pkg" 2>/dev/null || true)"
  [[ -z "$info" ]] && return 0

  conflicts="$(awk -F: '/^Conflicts With/{sub(/^[^:]*:[[:space:]]*/,""); print; exit}' <<<"$info")"
  replaces="$(awk -F: '/^Replaces/{sub(/^[^:]*:[[:space:]]*/,""); print; exit}' <<<"$info")"

  for rival in $conflicts $replaces; do
    [[ "$rival" == "None" || -z "$rival" ]] && continue
    rival="${rival%%[<>=]*}"
    if pacman -Qq "$rival" &>/dev/null; then
      drop+=("$rival")
    fi
  done

  # known provider/rival pairs not always listed as Conflicts With
  case "$pkg" in
    pipewire-pulse|pipewire-alsa|pipewire-jack)
      pacman -Qq pulseaudio &>/dev/null && drop+=(pulseaudio)
      pacman -Qq pulseaudio-bluetooth &>/dev/null && drop+=(pulseaudio-bluetooth)
      ;;
    paru-bin) pacman -Qq paru &>/dev/null && drop+=(paru) ;;
    linux-cachyos-nvidia-open)
      pacman -Qq linux-cachyos-nvidia &>/dev/null && drop+=(linux-cachyos-nvidia)
      ;;
    linux-cachyos-lts-nvidia-open)
      pacman -Qq linux-cachyos-lts-nvidia &>/dev/null && drop+=(linux-cachyos-lts-nvidia)
      ;;
    nvidia-open|nvidia-open-dkms|nvidia-open-lts)
      pacman -Qq nvidia &>/dev/null && drop+=(nvidia)
      pacman -Qq nvidia-dkms &>/dev/null && drop+=(nvidia-dkms)
      pacman -Qq nvidia-lts &>/dev/null && drop+=(nvidia-lts)
      ;;
  esac

  ((${#drop[@]})) || return 0

  # unique
  local -A seen=()
  local -a uniq=()
  local d
  for d in "${drop[@]}"; do
    [[ -n "${seen[$d]:-}" ]] && continue
    seen[$d]=1
    uniq+=("$d")
  done

  echo "  conflict: removing ${uniq[*]} for $pkg"
  RESOLVED_CONFLICTS+=("$pkg<-${uniq[*]}")
  # -Rdd: drop without pulling reverse deps; targets replace them
  ${SUDO} pacman -Rdd --noconfirm "${uniq[@]}" 2>/dev/null || \
    ${SUDO} pacman -R --noconfirm "${uniq[@]}" 2>/dev/null || true
}

pac_install() {
  local -a args=(-S --needed --noconfirm)
  if [[ "${PAC_OVERWRITE:-1}" == "1" ]]; then
    args+=(--overwrite='*')
  fi
  ${SUDO} pacman "${args[@]}" "$@"
}

install_one() {
  local pkg="$1"
  local log

  if pacman -Qq "$pkg" &>/dev/null; then
    return 0
  fi
  if ! pacman -Si "$pkg" &>/dev/null; then
    echo "  skip (not in repos): $pkg"
    return 0
  fi

  resolve_conflicts_for "$pkg"

  if log="$(pac_install "$pkg" 2>&1)"; then
    return 0
  fi

  # file-conflict / partial — retry once after overwrite + conflict resolve
  echo "$log" | tail -n 20
  resolve_conflicts_for "$pkg"
  if PAC_OVERWRITE=1 pac_install "$pkg" 2>/dev/null; then
    echo "  ok after conflict resolve: $pkg"
    return 0
  fi

  echo "  FAIL: $pkg"
  FAILED_PKGS+=("$pkg")
  return 0
}

install_pkgs() {
  local -a pkgs=("$@")
  local -a avail=()
  local -a need=()
  local p log

  for p in "${pkgs[@]}"; do
    [[ -z "$p" ]] && continue
    if pacman -Si "$p" &>/dev/null || pacman -Qi "$p" &>/dev/null; then
      avail+=("$p")
    else
      echo "  skip (not in repos): $p"
    fi
  done
  ((${#avail[@]})) || return 0

  for p in "${avail[@]}"; do
    pacman -Qq "$p" &>/dev/null || need+=("$p")
  done
  ((${#need[@]})) || return 0

  # pre-clear conflicts for the whole batch
  for p in "${need[@]}"; do
    resolve_conflicts_for "$p"
  done

  if log="$(pac_install "${need[@]}" 2>&1)"; then
    return 0
  fi

  echo "  batch hit issues — installing one-by-one"
  echo "$log" | tail -n 25
  for p in "${need[@]}"; do
    install_one "$p"
  done
}

enable_now() {
  local u
  for u in "$@"; do
    ${SUDO} systemctl enable --now "$u" 2>/dev/null || echo "  warn: could not enable $u"
  done
}

# ---------------------------------------------------------------------------
# 0. sync + base tooling
# ---------------------------------------------------------------------------
echo "==> Syncing package databases"
${SUDO} pacman -Sy

echo "==> base-devel + essentials"
install_pkgs \
  base-devel git wget curl sudo \
  reflector pacman-contrib pkgfile \
  man-db man-pages texinfo \
  which less most tree unzip zip unrar 7zip \
  rsync stow pv duf plocate \
  openssh avahi nss-mdns \
  ufw ufw-extras \
  smartmontools hdparm lsscsi sg3_utils \
  dosfstools exfatprogs e2fsprogs xfsprogs btrfs-progs \
  f2fs-tools nilfs-utils jfsutils ntfs-3g \
  mtools fsarchiver \
  efibootmgr efitools \
  cryptsetup device-mapper lvm2 mdadm dmraid \
  inetutils bind ethtool usbutils usb_modeswitch \
  dmidecode hwinfo mesa-utils \
  logrotate lsb-release sysfsutils

# ---------------------------------------------------------------------------
# 1. firmware / microcode / kernels (CachyOS kernels when available)
# ---------------------------------------------------------------------------
echo "==> firmware + microcode"
install_pkgs linux-firmware amd-ucode sof-firmware alsa-firmware alsa-utils alsa-plugins

if ((IS_CACHYOS)); then
  echo "==> CachyOS repos + kernels + NVIDIA open modules"
  install_pkgs \
    cachyos-keyring \
    cachyos-mirrorlist cachyos-v3-mirrorlist cachyos-v4-mirrorlist \
    linux-cachyos linux-cachyos-headers \
    linux-cachyos-lts linux-cachyos-lts-headers \
    linux-cachyos-nvidia-open linux-cachyos-lts-nvidia-open \
    cachyos-settings cachyos-hooks cachyos-hello \
    cachyos-kernel-manager cachyos-packageinstaller \
    cachyos-rate-mirrors cachyos-micro-settings \
    chwd hwdetect mkinitcpio \
    ananicy-cpp cachyos-ananicy-rules \
    zram-generator scx-scheds scx-manager \
    shelly
else
  echo "==> vanilla Arch kernels"
  install_pkgs linux linux-headers linux-lts linux-lts-headers mkinitcpio zram-generator
  if [[ "${SKIP_NVIDIA:-0}" != "1" ]]; then
    install_pkgs nvidia-open nvidia-open-lts
  fi
fi

# ---------------------------------------------------------------------------
# 2. graphics — AMD Renoir + NVIDIA GTX 1650 hybrid
# ---------------------------------------------------------------------------
echo "==> AMD + Vulkan"
install_pkgs \
  xf86-video-amdgpu \
  vulkan-radeon lib32-vulkan-radeon \
  vulkan-icd-loader lib32-vulkan-icd-loader \
  egl-wayland

if [[ "${SKIP_NVIDIA:-0}" != "1" ]]; then
  echo "==> NVIDIA userspace + PRIME"
  install_pkgs \
    nvidia-utils lib32-nvidia-utils \
    opencl-nvidia lib32-opencl-nvidia \
    nvidia-settings nvidia-prime \
    libva-nvidia-driver \
    nvidia-container-toolkit \
    switcheroo-control
fi

# ---------------------------------------------------------------------------
# 3. audio / bluetooth / power
# ---------------------------------------------------------------------------
echo "==> pipewire + bluetooth + power"
install_pkgs \
  pipewire-pulse pipewire-alsa wireplumber \
  pavucontrol \
  bluez bluez-utils bluez-libs bluez-obex bluez-hid2hci \
  upower power-profiles-daemon cpupower \
  realtime-privileges

# ---------------------------------------------------------------------------
# 4. networking
# ---------------------------------------------------------------------------
echo "==> networking"
install_pkgs \
  networkmanager networkmanager-openvpn \
  iwd wpa_supplicant dnsmasq modemmanager \
  nfs-utils xl2tpd netctl

# ---------------------------------------------------------------------------
# 5. fonts (terminal / CLI)
# ---------------------------------------------------------------------------
echo "==> fonts"
install_pkgs \
  noto-fonts noto-fonts-cjk noto-fonts-emoji \
  ttf-dejavu ttf-liberation ttf-bitstream-vera ttf-opensans \
  ttf-jetbrains-mono-nerd ttf-meslo-nerd \
  cantarell-fonts awesome-terminal-fonts

# ---------------------------------------------------------------------------
# 6. terminals + shell UX
# ---------------------------------------------------------------------------
echo "==> terminals + shell"
install_pkgs \
  zsh fish bash-completion \
  alacritty kitty ghostty wezterm \
  starship zoxide yazi zellij \
  nano nano-syntax-highlighting neovim vim micro \
  fastfetch btop nvtop glances \
  xdg-user-dirs wl-clipboard xclip

if ((IS_CACHYOS)); then
  install_pkgs cachyos-zsh-config cachyos-fish-config cachy-update cachyos-grub-theme
fi

# ---------------------------------------------------------------------------
# 7. CLI / devops tools
# ---------------------------------------------------------------------------
echo "==> CLI + devops"
install_pkgs \
  ripgrep git-delta lazygit meld \
  docker docker-compose \
  kubectl \
  go rust nodejs npm \
  python python-pip python-pipx python-packaging python-defusedxml \
  uv \
  tor torsocks nyx \
  keyd \
  fwupd \
  rebuild-detector \
  tree-sitter-cli \
  tesseract-data-eng \
  gst-libav gst-plugins-bad gst-plugins-ugly \
  gst-plugin-pipewire gst-plugin-va \
  libdvdcss libgsf libopenraw poppler-glib \
  perl s-nail diffutils

# ---------------------------------------------------------------------------
# 8. btrfs helpers + snapper + grub-btrfs (layout reference below)
# ---------------------------------------------------------------------------
echo "==> btrfs tooling"
install_pkgs snapper btrfs-assistant grub-btrfs-support grub grub-hook os-prober

# Expected disk layout (Zephyrus G14 512G NVMe) — informational only:
#   nvme0n1p1  512M  vfat  /boot/efi
#   nvme0n1p2  rest  btrfs subvols:
#     @ /   @home /home   @root /root   @srv /srv
#     @cache /var/cache   @tmp /var/tmp   @log /var/log
#   zram0 swap (zstd, size=ram) via systemd-zram-generator
# fstab options: defaults,noatime,compress=zstd:1

# ---------------------------------------------------------------------------
# 9. AUR helper + foreign packages (paru)
# ---------------------------------------------------------------------------
if [[ "${SKIP_AUR:-0}" != "1" ]]; then
  if ! command -v paru >/dev/null 2>&1; then
    echo "==> bootstrap paru-bin"
    resolve_conflicts_for paru-bin
    if pacman -Si paru-bin &>/dev/null; then
      install_one paru-bin
    else
      tmp="$(mktemp -d)"
      if git clone --depth 1 https://aur.archlinux.org/paru-bin.git "$tmp/paru-bin" \
        && (cd "$tmp/paru-bin" && makepkg -si --noconfirm); then
        :
      else
        echo "  FAIL: paru-bin bootstrap"
        FAILED_PKGS+=("paru-bin")
      fi
      rm -rf "$tmp"
    fi
  fi
  if command -v paru >/dev/null 2>&1; then
    echo "==> AUR packages"
    for p in hunk-bin qtile-extras; do
      if pacman -Qq "$p" &>/dev/null; then
        continue
      fi
      if ! paru -S --needed --noconfirm --overwrite '*' "$p"; then
        echo "  FAIL (aur): $p — retry alone"
        if ! paru -S --needed --noconfirm --overwrite '*' "$p"; then
          FAILED_PKGS+=("$p")
        fi
      fi
    done
  else
    echo "  warn: paru unavailable — skipped AUR pkgs"
  fi
fi

# optional extras
if [[ -n "${EXTRA_PKGS:-}" ]]; then
  # shellcheck disable=SC2086
  install_pkgs ${EXTRA_PKGS}
fi

# ---------------------------------------------------------------------------
# 10. user groups
# ---------------------------------------------------------------------------
echo "==> groups for $(whoami)"
for g in wheel docker video audio storage lp network rfkill realtime; do
  if getent group "$g" >/dev/null; then
    ${SUDO} usermod -aG "$g" "$(whoami)" || true
  fi
done

# ---------------------------------------------------------------------------
# 10b. system polish (locale, pacman, grub, zram, nsswitch)
# ---------------------------------------------------------------------------
echo "==> locale / timezone (match host: en_IN + Asia/Kolkata)"
${SUDO} timedatectl set-timezone Asia/Kolkata || true
${SUDO} localectl set-locale LANG=en_IN.UTF-8 2>/dev/null \
  || ${SUDO} localectl set-locale LANG=en_IN 2>/dev/null \
  || true
${SUDO} localectl set-keymap us || true

if [[ -f /etc/pacman.conf ]]; then
  echo "==> pacman.conf quality-of-life"
  ${SUDO} sed -i 's/^#Color/Color/' /etc/pacman.conf
  ${SUDO} sed -i 's/^#VerbosePkgLists/VerbosePkgLists/' /etc/pacman.conf
  grep -q '^ILoveCandy' /etc/pacman.conf || ${SUDO} sed -i '/^Color$/a ILoveCandy' /etc/pacman.conf
  if grep -q '^#ParallelDownloads' /etc/pacman.conf; then
    ${SUDO} sed -i 's/^#ParallelDownloads.*/ParallelDownloads = 10/' /etc/pacman.conf
  elif ! grep -q '^ParallelDownloads' /etc/pacman.conf; then
    ${SUDO} sed -i '/^\[options\]/a ParallelDownloads = 10' /etc/pacman.conf
  fi
fi

# zram (host: zstd, size=ram) — only write if missing
if [[ ! -f /etc/systemd/zram-generator.conf ]] && [[ ! -f /usr/lib/systemd/zram-generator.conf ]]; then
  echo "==> zram-generator.conf"
  ${SUDO} tee /etc/systemd/zram-generator.conf >/dev/null <<'ZRAM'
[zram0]
compression-algorithm = zstd
zram-size = ram
swap-priority = 100
fs-type = swap
ZRAM
elif [[ ! -f /etc/systemd/zram-generator.conf ]]; then
  ${SUDO} tee /etc/systemd/zram-generator.conf >/dev/null <<'ZRAM'
[zram0]
compression-algorithm = zstd
zram-size = ram
swap-priority = 100
fs-type = swap
ZRAM
fi

# grub cmdline used on host
if [[ -f /etc/default/grub ]]; then
  echo "==> grub defaults"
  ${SUDO} sed -i "s|^GRUB_CMDLINE_LINUX_DEFAULT=.*|GRUB_CMDLINE_LINUX_DEFAULT='nowatchdog nvme_load=YES splash loglevel=3'|" /etc/default/grub
  ${SUDO} sed -i "s|^#\\?GRUB_DISABLE_OS_PROBER=.*|GRUB_DISABLE_OS_PROBER='false'|" /etc/default/grub
  if [[ -f /usr/share/grub/themes/cachyos/theme.txt ]]; then
    if grep -q '^GRUB_THEME=' /etc/default/grub; then
      ${SUDO} sed -i "s|^GRUB_THEME=.*|GRUB_THEME='/usr/share/grub/themes/cachyos/theme.txt'|" /etc/default/grub
    else
      echo "GRUB_THEME='/usr/share/grub/themes/cachyos/theme.txt'" | ${SUDO} tee -a /etc/default/grub >/dev/null
    fi
  fi
  if command -v grub-mkconfig >/dev/null; then
    ${SUDO} grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true
  fi
fi

# mDNS for *.local (ssh arch / archlinux.local)
if [[ -f /etc/nsswitch.conf ]] && ! grep -Eq 'hosts:.*mdns' /etc/nsswitch.conf; then
  echo "==> nsswitch mdns_minimal"
  ${SUDO} sed -i 's/^hosts:.*/hosts: mymachines mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return] files myhostname dns/' /etc/nsswitch.conf
fi

# ---------------------------------------------------------------------------
# 11. services
# ---------------------------------------------------------------------------
echo "==> enable services"
enable_now NetworkManager
enable_now bluetooth
enable_now sshd
enable_now avahi-daemon
enable_now ufw
enable_now docker
enable_now systemd-timesyncd
enable_now systemd-resolved
enable_now systemd-oomd
enable_now fstrim.timer
enable_now snapper-cleanup.timer

if [[ "${SKIP_NVIDIA:-0}" != "1" ]]; then
  enable_now nvidia-powerd.service || true
  enable_now switcheroo-control || true
fi

if systemctl list-unit-files keyd.service &>/dev/null; then
  # Backspace-as-delete remap used on host — only write if missing
  if [[ ! -f /etc/keyd/default.conf ]]; then
    echo "==> keyd default.conf (delete -> backspace)"
    ${SUDO} tee /etc/keyd/default.conf >/dev/null <<'KEYD'
[ids]
*

[main]
delete = backspace
KEYD
  fi
  enable_now keyd
fi

if ((IS_CACHYOS)); then
  enable_now ananicy-cpp.service || true
  enable_now cachyos-rate-mirrors.timer || true
  enable_now grub-btrfs-snapper.path || true
fi

# ufw baseline — SSH allowed (do not lock yourself out)
if command -v ufw >/dev/null; then
  ${SUDO} ufw allow OpenSSH >/dev/null || ${SUDO} ufw allow 22/tcp >/dev/null || true
  ${SUDO} ufw --force enable >/dev/null || true
fi

# shell default
if command -v zsh >/dev/null && [[ "$(getent passwd "$(whoami)" | cut -d: -f7)" != "$(command -v zsh)" ]]; then
  echo "==> set login shell to zsh"
  chsh -s "$(command -v zsh)" || true
fi

# snapper root config if missing and / is btrfs
if command -v snapper >/dev/null && ! snapper list-configs 2>/dev/null | grep -q root; then
  if findmnt -n -o FSTYPE / | grep -q btrfs; then
    echo "==> snapper create-config root"
    ${SUDO} snapper -c root create-config / || true
  fi
fi

# pkgfile db
${SUDO} pkgfile --update >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# Qtile (Wayland/X11) — alongside Plasma; does not remove DE
# ---------------------------------------------------------------------------
if [[ "${SKIP_QTILE:-0}" != "1" ]]; then
  echo "==> Qtile setup"
  _POST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  _QTILE_SETUP=""
  if [[ -n "${QTILE_SRC:-}" && -f "${QTILE_SRC}/setup.sh" ]]; then
    _QTILE_SETUP="${QTILE_SRC}/setup.sh"
  elif [[ -f "${_POST_DIR}/../Qtile/setup.sh" ]]; then
    _QTILE_SETUP="$(cd "${_POST_DIR}/../Qtile" && pwd)/setup.sh"
  else
    _QTILE_TMP="$(mktemp -d /tmp/qtile-src-XXXXXX)"
    if git clone --depth 1 https://github.com/Linux-DEX/Qtile.git "${_QTILE_TMP}/Qtile"; then
      _QTILE_SETUP="${_QTILE_TMP}/Qtile/setup.sh"
    else
      echo "WARN: could not fetch Qtile repo — skip (set QTILE_SRC=... or SKIP_QTILE=1)"
      FAILED_PKGS+=("qtile-setup")
    fi
  fi
  if [[ -n "${_QTILE_SETUP}" ]]; then
    if ! bash "${_QTILE_SETUP}"; then
      echo "WARN: Qtile setup failed"
      FAILED_PKGS+=("qtile-setup")
    fi
  fi
  unset _POST_DIR _QTILE_SETUP _QTILE_TMP
fi

# ---------------------------------------------------------------------------
# done
# ---------------------------------------------------------------------------
echo
echo "Done."
if ((${#RESOLVED_CONFLICTS[@]})); then
  echo "Conflicts resolved:"
  printf '  - %s\n' "${RESOLVED_CONFLICTS[@]}"
fi
if ((${#FAILED_PKGS[@]})); then
  echo "FAILED packages (re-run or install manually):"
  printf '  - %s\n' "${FAILED_PKGS[@]}"
else
  echo "All requested packages installed (or already present)."
fi

cat <<EOF

Reboot recommended (new kernel / NVIDIA / groups).
After reboot:
  groups          # should include docker,wheel,video,...
  nvidia-smi      # if NVIDIA kept
  docker ps
  ssh $(whoami)@$(hostname).local
  # Qtile: log out → greeter → Qtile (Wayland) / Qtile (X11)
  # SKIP_QTILE=1 to skip next time

Disk layout reference (this machine):
  /dev/nvme0n1  Micron 512G
    p1 512M vfat  -> /boot/efi
    p2 rest btrfs -> @ @home @root @srv @cache @tmp @log
  zram swap (zstd, ram-sized)

Skip flags: SKIP_AUR=1 SKIP_NVIDIA=1 SKIP_CACHYOS=1 SKIP_QTILE=1 EXTRA_PKGS="..." PAC_OVERWRITE=0
EOF

# non-zero if anything failed, but only after finishing the full run
((${#FAILED_PKGS[@]} == 0))
