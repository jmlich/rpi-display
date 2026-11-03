#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 jmlich

import datetime
import json
import os
import queue
import subprocess
import threading
import time
import unicodedata

import RPi.GPIO as GPIO

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT

LED = 22  # Physical pin 22 = GPIO25

BUTTON_BLINK = 3     # turns blinking on and off
BUTTON_MODE = 5      # switches between time and counter
BUTTON_COUNTER = 18  # increments the counter
BUTTON_DECREMENT = 11  # decrements the counter
BUTTON_IP = 13       # scrolls the IP addresses
BUTTON_TALK = 15     # scrolls the next OpenAlt talk
BUTTONS = [3, 5, 11, 13, 15, 18]

# The blink thread runs all the time. It only blinks when this is set.
blink_enabled = threading.Event()
# Set on exit, so the blink thread knows it should finish.
stop_blinking = threading.Event()
# Pin 15 shows the rooms one after another.
talk_index = 0

# Messages waiting to be scrolled on the matrix.
messages = queue.Queue()

# The counter survives a restart, it is kept next to this script.
COUNTER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "counter.txt")
# Every press is written here. The clock of the Pi can be wrong before it
# gets the time from the network, so the line has the time since boot too.
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "buttons.csv")
# The OpenAlt talks, as the pretalx API gives them.
SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "openalt-2026_sessions.json")

try:
    counter = int(open(COUNTER_FILE).read())
except Exception:
    counter = 0

show_counter = False

# The buttons bounce, so one press can fire the callback several times.
# Presses closer together than this are ignored.
DEBOUNCE = 0.3
last_press = {}
# A long press chatters on release too, which is another rising edge.
# So a press counts only if the pin is still up after this long.
HOLD = 0.05


def blink_loop():
    while not stop_blinking.is_set():
        if blink_enabled.is_set():
            GPIO.output(LED, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(LED, GPIO.LOW)
            time.sleep(0.5)
        else:
            GPIO.output(LED, GPIO.LOW)
            time.sleep(0.1)


def log_press(channel):
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    boot = time.clock_gettime(time.CLOCK_BOOTTIME)
    line = f"{stamp},{boot:.2f},{channel}"
    print(line)
    new_file = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if new_file:
            f.write("time,boot,pin\n")
        f.write(line + "\n")


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


def next_talk(index):
    try:
        sessions = json.load(open(SESSIONS_FILE))
    except Exception:
        return "OpenAlt 2026"

    # The next talk in each room. There are five rooms, the index chooses
    # which one is shown.
    now = datetime.datetime.now().astimezone()
    rooms = {}
    for talk in sessions["results"]:
        slot = talk["slots"][0]
        # A talk without a time slot yet has no start and no room.
        if slot["start"] is None or slot["room"] is None:
            continue
        start = datetime.datetime.fromisoformat(slot["start"])
        if start < now:
            continue
        room = slot["room"]["name"]["en"]
        if room not in rooms or start < rooms[room][0]:
            rooms[room] = (start, talk["title"])

    if len(rooms) == 0:
        return "OpenAlt 2026"

    names = sorted(rooms)
    room = names[index % len(names)]
    start, title = rooms[room]
    # For example 4d7h3m, or just 45m when it is soon.
    minutes = int((start - now).total_seconds() // 60)
    days = minutes // (24 * 60)
    hours = minutes // 60 % 24
    left = ""
    if days > 0:
        left = left + f"{days}d"
    if days > 0 or hours > 0:
        left = left + f"{hours}h"
    left = left + f"{minutes % 60}m"
    message = f"{left} {room} {title}"

    # The font has no Czech letters, so the accents are dropped.
    message = unicodedata.normalize("NFKD", message)
    return message.encode("ascii", "ignore").decode()


def button_pressed(channel):
    global counter
    global show_counter
    global talk_index

    now = time.monotonic()
    if now - last_press.get(channel, 0) < DEBOUNCE:
        return

    time.sleep(HOLD)
    if GPIO.input(channel) != GPIO.HIGH:
        return
    last_press[channel] = now

    log_press(channel)

    if channel == BUTTON_BLINK:
        if blink_enabled.is_set():
            blink_enabled.clear()
        else:
            blink_enabled.set()
    elif channel == BUTTON_COUNTER:
        counter = counter + 1
        open(COUNTER_FILE, "w").write(str(counter))
    elif channel == BUTTON_DECREMENT:
        counter = counter - 1
        open(COUNTER_FILE, "w").write(str(counter))
    elif channel == BUTTON_MODE:
        show_counter = not show_counter
    elif channel == BUTTON_IP:
        messages.put(ip_addresses())
    elif channel == BUTTON_TALK:
        messages.put(next_talk(talk_index))
        talk_index = talk_index + 1
    else:
        messages.put(f"PIN {channel}")


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
    while True:
        try:
            message = messages.get_nowait()
        except queue.Empty:
            message = None

        # A button message takes over the matrix for a moment.
        if message is not None:
            show_message(device, message, fill="white",
                         font=proportional(CP437_FONT))
            continue

        if show_counter:
            msg = str(counter)
        else:
            msg = time.strftime("%H:%M", time.localtime())

        with canvas(device) as draw:
            text(draw, (0, 0), msg, fill="white", font=proportional(CP437_FONT))

        time.sleep(0.3)


def main():
    blink_thread = None

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
