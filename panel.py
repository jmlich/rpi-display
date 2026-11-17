#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 jmlich

import configparser
import datetime
import os
import queue
import subprocess
import syslog
import threading
import time
import unicodedata

import dbus
import RPi.GPIO as GPIO

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT

LED = 22  # Physical pin 22 = GPIO25

BUTTON_ALARM = 3      # turns the alarms off and on
BUTTON_NEXT = 5       # next stream
BUTTON_PLAY = 18      # the big button, starts and stops the player
BUTTON_VOLUME_DOWN = 11
BUTTON_VOLUME_UP = 13
BUTTON_IP = 15        # scrolls the IP addresses
BUTTONS = [3, 5, 11, 13, 15, 18]

# Set on exit, so the blink thread knows it should finish.
stop_blinking = threading.Event()

# Messages waiting to be scrolled on the matrix.
messages = queue.Queue()

# The player is a separate program, VLC started by player.service. It is
# controlled over MPRIS, so any player with MPRIS on the session bus works.
MPRIS_PREFIX = "org.mpris.MediaPlayer2."
MPRIS_PATH = "/org/mpris/MediaPlayer2"
PLAYER = "org.mpris.MediaPlayer2.Player"
VOLUME_STEP = 0.1
# The player forgets the volume when it restarts, so panel.py keeps it here
# and sets it before every Play.
VOLUME_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "volume.txt")
# While it plays, the display checks the song this often. It scrolls the song
# when it changes, and again every SONG_EVERY seconds.
SONG_CHECK = 2
SONG_EVERY = 60
# The alarms start the player at a set time, see alarms.ini.
ALARMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "alarms.ini")
# While this file exists, the alarms do nothing. Pin 3 makes and removes it.
ALARMS_OFF_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "alarms_off")
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
# When an alarm started the player, it stops at this time.monotonic().
# None when nothing is to stop.
stop_at = None

# The buttons bounce, so one press can fire the callback several times.
# Presses closer together than this are ignored.
DEBOUNCE = 0.3
last_press = {}
# A long press chatters on release too, which is another rising edge.
# So a press counts only if the pin is still up after this long.
HOLD = 0.05
# When the last button callback finished. All callbacks run one after another
# in one thread, so an edge that comes during a slow callback waits for it.
callback_end = 0


def mpris_player():
    # A new proxy every time, so a restarted player is found again.
    bus = dbus.SessionBus()
    for name in bus.list_names():
        if name.startswith(MPRIS_PREFIX):
            return bus.get_object(name, MPRIS_PATH)
    return None


def ascii_only(message):
    # The font has no Czech letters, so the accents are dropped.
    message = unicodedata.normalize("NFKD", message)
    return message.encode("ascii", "ignore").decode()


def is_playing():
    try:
        proxy = mpris_player()
        if proxy is None:
            return False
        status = proxy.Get(PLAYER, "PlaybackStatus",
                           dbus_interface=dbus.PROPERTIES_IFACE)
        return status == "Playing"
    except dbus.DBusException:
        return False


def track_title():
    # The name of the playlist item, the stream name from playlist.m3u.
    proxy = mpris_player()
    metadata = proxy.Get(PLAYER, "Metadata",
                         dbus_interface=dbus.PROPERTIES_IFACE)
    return ascii_only(str(metadata.get("xesam:title", "?")))


def song():
    # What the stream plays now, or "" when nothing plays.
    if not is_playing():
        return ""
    try:
        proxy = mpris_player()
        metadata = proxy.Get(PLAYER, "Metadata",
                             dbus_interface=dbus.PROPERTIES_IFACE)
    except dbus.DBusException:
        return ""
    # VLC puts the song of a stream, usually "artist - title", in
    # vlc:nowplaying. Other players put it in xesam:title.
    name = str(metadata.get("vlc:nowplaying", ""))
    if name == "":
        name = str(metadata.get("xesam:title", ""))
    return ascii_only(name)


def play(proxy, action, volume=None):
    # Without a volume it plays at the saved one.
    if volume is None:
        try:
            volume = float(open(VOLUME_FILE).read())
        except (OSError, ValueError):
            pass
    if volume is not None:
        proxy.Set(PLAYER, "Volume", dbus.Double(volume),
                  dbus_interface=dbus.PROPERTIES_IFACE)
    proxy.Play(dbus_interface=PLAYER)
    time.sleep(1)
    messages.put(action + " " + track_title())


def control_player(channel):
    global stop_at

    proxy = mpris_player()
    if proxy is None:
        messages.put("NO PLAYER")
        return

    if channel == BUTTON_PLAY:
        # A play from the button is not stopped by an alarm.
        stop_at = None
        # Stop, not Pause. A paused stream is old when it goes on again,
        # Play after Stop opens it again.
        if is_playing():
            syslog.syslog(f"pin {channel} sends Stop")
            proxy.Stop(dbus_interface=PLAYER)
            messages.put("STOP")
        else:
            syslog.syslog(f"pin {channel} sends Play")
            play(proxy, "PLAY")
    elif channel == BUTTON_NEXT:
        proxy.Next(dbus_interface=PLAYER)
        # The player needs a moment to switch the metadata.
        time.sleep(1)
        messages.put("NEXT " + track_title())
    else:
        volume = proxy.Get(PLAYER, "Volume",
                           dbus_interface=dbus.PROPERTIES_IFACE)
        if channel == BUTTON_VOLUME_UP:
            volume = min(1.0, volume + VOLUME_STEP)
            action = "VOL UP"
        else:
            volume = max(0.0, volume - VOLUME_STEP)
            action = "VOL DOWN"
        proxy.Set(PLAYER, "Volume", dbus.Double(volume),
                  dbus_interface=dbus.PROPERTIES_IFACE)
        open(VOLUME_FILE, "w").write(str(volume))
        messages.put(f"{action} {round(volume * 100)}")


def due_alarm(now):
    # The alarm that goes off now, otherwise None.
    config = configparser.ConfigParser()
    # A missing file is no alarms.
    config.read(ALARMS_FILE)
    for name in config.sections():
        alarm = config[name]
        if not alarm.getboolean("enabled", False):
            continue
        if alarm.getint("hour") != now.hour or alarm.getint("minute") != now.minute:
            continue
        # Without days it goes off every day.
        days = alarm.get("days", "").split()
        if len(days) > 0 and DAYS[now.weekday()] not in days:
            continue
        if alarm.getboolean("one_shot", False):
            alarm["enabled"] = "false"
            with open(ALARMS_FILE, "w") as f:
                config.write(f)
        return alarm
    return None


def run_alarms():
    global stop_at

    # Checked before due_alarm(), so a one_shot alarm stays for later.
    if os.path.exists(ALARMS_OFF_FILE):
        return
    try:
        alarm = due_alarm(datetime.datetime.now())
        if alarm is None:
            return
        minutes = alarm.getint("duration", 60)
        volume = None
        if "volume" in alarm:
            volume = alarm.getint("volume") / 100
    except (ValueError, configparser.Error) as e:
        syslog.syslog(syslog.LOG_ERR, f"alarms.ini: {e}")
        return
    syslog.syslog(f"alarm, plays {minutes} minutes")
    try:
        proxy = mpris_player()
        if proxy is None:
            messages.put("NO PLAYER")
            return
        # When it already plays, somebody listens, so it is left alone.
        if is_playing():
            return
        play(proxy, "ALARM", volume)
    except dbus.DBusException as e:
        syslog.syslog(syslog.LOG_ERR, str(e))
        messages.put("PLAYER ERROR")
        return
    # 0 means it plays until somebody stops it.
    if minutes > 0:
        stop_at = time.monotonic() + minutes * 60


def stop_alarm():
    global stop_at

    if stop_at is None or time.monotonic() < stop_at:
        return
    stop_at = None
    syslog.syslog("alarm over")
    try:
        proxy = mpris_player()
        if proxy is not None and is_playing():
            proxy.Stop(dbus_interface=PLAYER)
            messages.put("STOP")
    except dbus.DBusException as e:
        syslog.syslog(syslog.LOG_ERR, str(e))


def blink_loop():
    # The LED blinks while the player plays.
    # It checks the player every second, so it also logs a short play that the
    # song check in display_loop() misses.
    was_playing = False
    while not stop_blinking.is_set():
        playing = is_playing()
        if playing != was_playing:
            syslog.syslog("player plays" if playing else "player does not play")
            was_playing = playing
        if playing:
            GPIO.output(LED, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(LED, GPIO.LOW)
            time.sleep(0.5)
        else:
            GPIO.output(LED, GPIO.LOW)
            time.sleep(0.5)


def ip_addresses():
    out = subprocess.run(["hostname", "-I"], capture_output=True,
                         text=True).stdout
    # Only IPv4, the long IPv6 addresses do not read well on the matrix.
    ipv4 = []
    for address in out.split():
        if ":" not in address:
            ipv4.append(address)
    if len(ipv4) == 0:
        return "NO IP"
    return " ".join(ipv4)


def button_pressed(channel):
    global callback_end

    now = time.monotonic()
    # Every edge goes to the journal, the ignored ones too. Close to 0 s after
    # the last callback means the edge waited for it.
    details = (f"{now - last_press.get(channel, 0):.2f} s after the last press, "
               f"{now - callback_end:.2f} s after the last callback")
    try:
        if now - last_press.get(channel, 0) < DEBOUNCE:
            syslog.syslog(f"pin {channel} ignored, bounce, {details}")
            return

        time.sleep(HOLD)
        if GPIO.input(channel) != GPIO.HIGH:
            syslog.syslog(f"pin {channel} ignored, low after {HOLD} s, {details}")
            return
        last_press[channel] = now
        # journald keeps the syslog messages, see them with journalctl -t panel.
        syslog.syslog(f"pin {channel}, {details}")

        if channel == BUTTON_IP:
            messages.put("IP " + ip_addresses())
            return

        if channel == BUTTON_ALARM:
            if os.path.exists(ALARMS_OFF_FILE):
                os.remove(ALARMS_OFF_FILE)
                action = "ALARM ON"
            else:
                open(ALARMS_OFF_FILE, "w").close()
                action = "ALARM OFF"
            syslog.syslog(action.lower())
            messages.put(action)
            return

        try:
            control_player(channel)
        except dbus.DBusException as e:
            syslog.syslog(syslog.LOG_ERR, str(e))
            messages.put("PLAYER ERROR")
    finally:
        callback_end = time.monotonic()


def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(LED, GPIO.OUT)

    for pin in BUTTONS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.add_event_detect(
            pin,
            GPIO.RISING,
            callback=button_pressed,
            bouncetime=200
        )


def make_device():
    serial = spi(port=0, device=0, gpio=noop())
    # rotate=2 because the matrix is mounted upside down
    device = max7219(serial, cascaded=4, block_orientation=-90, rotate=2)
    # 40, not the full 255. The first box had no window over the matrix
    # and lit up the whole room at night. A light sensor could set this
    # from the light in the room instead of a fixed number.
    device.contrast(40)
    return device


def display_loop(device):
    last_check = 0
    last_shown = 0
    last_song = ""
    last_minute = ""

    while True:
        # The alarms are checked once a minute.
        minute = time.strftime("%H:%M")
        if minute != last_minute:
            last_minute = minute
            run_alarms()
        stop_alarm()

        now = time.monotonic()
        if now - last_check >= SONG_CHECK:
            last_check = now
            current = song()
            # In the journal too, so a stop nobody asked for has a time.
            if current != last_song:
                if current == "":
                    syslog.syslog("stopped")
                else:
                    syslog.syslog(f"song {current}")
            if current != "":
                if current != last_song or now - last_shown >= SONG_EVERY:
                    messages.put(current)
                    last_shown = now
            last_song = current

        try:
            message = messages.get_nowait()
        except queue.Empty:
            message = None

        # A button message takes over the matrix for a moment.
        if message is not None:
            show_message(device, message, fill="white",
                         font=proportional(CP437_FONT))
            continue

        msg = time.strftime("%H:%M", time.localtime())

        with canvas(device) as draw:
            text(draw, (0, 0), msg, fill="white", font=proportional(CP437_FONT))
            # The bottom-left pixel says the alarms are off. The clock never
            # uses the bottom row.
            if os.path.exists(ALARMS_OFF_FILE):
                draw.point((0, 7), fill="white")

        time.sleep(0.3)


def main():
    blink_thread = None

    syslog.openlog("panel")
    try:
        setup_gpio()
        device = make_device()

        blink_thread = threading.Thread(target=blink_loop)
        blink_thread.start()

        display_loop(device)
    except KeyboardInterrupt:
        pass
    finally:
        stop_blinking.set()
        if blink_thread is not None:
            blink_thread.join()
            GPIO.output(LED, GPIO.LOW)
        # setup_gpio() is inside the try, so a failed start still gets here
        # and gives the pins back. Otherwise the next start fails too.
        GPIO.cleanup()


if __name__ == "__main__":
    main()
