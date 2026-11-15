#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 jmlich
# Set up an existing Raspberry Pi OS installation to run panel.py.
#
#   sudo setup/setup.sh            runs every step
#   sudo setup/setup.sh enable_spi runs one step
#
# The steps can be run again, they do not break anything the second time.

set -e

PANEL_USER=panel
PANEL_DIR=/opt/panel
REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)  #"
STEPS="install_packages install_panel make_venv create_user enable_spi set_shell enable_autologin enable_player"

function log() {
    echo "==> $*"
}

function config_txt() {
    # Bookworm keeps it on /boot/firmware, older releases on /boot.
    if [ -f /boot/firmware/config.txt ]; then
        echo /boot/firmware/config.txt
    else
        echo /boot/config.txt
    fi
}

function install_packages() {
    log "installing packages"
    apt-get update
    # rpi-lgpio provides the same RPi.GPIO module, but through /dev/gpiochip0.
    # RPi.GPIO itself uses /sys/class/gpio, which kernel 6.6 renumbered, and
    # its add_event_detect fails there.
    apt-get install -y python3-rpi-lgpio python3-spidev python3-venv
    # VLC plays the playlist, panel.py talks to it over D-Bus (MPRIS).
    apt-get install -y --no-install-recommends vlc-bin vlc-plugin-base python3-dbus
}

function make_venv() {
    log "making the virtual environment"
    # luma is not packaged in Debian, so it comes from pip. The venv sees the
    # system packages, RPi.GPIO and spidev come from apt.
    if [ ! -d "$PANEL_DIR/venv" ]; then
        python3 -m venv --system-site-packages "$PANEL_DIR/venv"
    fi
    "$PANEL_DIR/venv/bin/pip" install --upgrade luma.led_matrix
}

function install_panel() {
    log "copying panel.py to $PANEL_DIR"
    mkdir -p "$PANEL_DIR"
    cp "$REPO_DIR/panel.py" "$PANEL_DIR/panel.py"
    cp "$REPO_DIR/playlist.m3u" "$PANEL_DIR/playlist.m3u"
    # The alarms are set on the Pi, so a second run keeps them.
    if [ ! -f "$PANEL_DIR/alarms.ini" ]; then
        cp "$REPO_DIR/alarms.ini" "$PANEL_DIR/alarms.ini"
    fi
    cp "$REPO_DIR/setup/files/panel-shell" "$PANEL_DIR/panel-shell"
    chmod 755 "$PANEL_DIR/panel.py" "$PANEL_DIR/panel-shell"
}

function create_user() {
    log "creating the user $PANEL_USER"
    if ! id "$PANEL_USER" >/dev/null 2>&1; then
        useradd --create-home --groups gpio,spi "$PANEL_USER"
    else
        usermod --append --groups gpio,spi "$PANEL_USER"
    fi
    # The panel user owns its program and its files.
    chown -R "$PANEL_USER:$PANEL_USER" "$PANEL_DIR"
}

function enable_spi() {
    local file
    file=$(config_txt)
    log "turning SPI on in $file"
    if ! grep -q "^dtparam=spi=on" "$file"; then
        echo "dtparam=spi=on" >> "$file"
    fi
}

function set_shell() {
    log "making panel-shell the login shell of $PANEL_USER"
    if ! grep -q "^$PANEL_DIR/panel-shell$" /etc/shells; then
        echo "$PANEL_DIR/panel-shell" >> /etc/shells
    fi
    chsh --shell "$PANEL_DIR/panel-shell" "$PANEL_USER"
}

function enable_autologin() {
    local dir=/etc/systemd/system/getty@tty1.service.d
    log "logging $PANEL_USER in on tty1"
    mkdir -p "$dir"
    cat > "$dir/autologin.conf" <<CONF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $PANEL_USER --noclear %I \$TERM
CONF
    systemctl daemon-reload
}

function enable_player() {
    local home
    local dir
    home=$(getent passwd "$PANEL_USER" | cut -d: -f6)
    dir="$home/.config/systemd/user"
    log "starting the player for $PANEL_USER"
    # Only for this user. A global unit would start a second VLC in every
    # other login and both would want the sound card.
    mkdir -p "$dir/default.target.wants"
    cp "$REPO_DIR/setup/files/player.service" "$dir/player.service"
    ln -sf ../player.service "$dir/default.target.wants/player.service"
    chown -R "$PANEL_USER:$PANEL_USER" "$home/.config"
}

function main() {
    if [ "$(id -u)" != "0" ]; then
        echo "run this as root"
        exit 1
    fi

    local steps="$*"
    if [ -z "$steps" ]; then
        steps="$STEPS"
    fi

    local step
    for step in $steps; do
        "$step"
    done

    log "done, reboot to try it"
}

main "$@"
