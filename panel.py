#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 jmlich

import os
import queue
import threading
import time

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
BUTTONS = [3, 5, 11, 13, 15, 18]

# The blink thread runs all the time. It only blinks when this is set.
blink_enabled = threading.Event()
# Set on exit, so the blink thread knows it should finish.
stop_blinking = threading.Event()

# Messages waiting to be scrolled on the matrix.
messages = queue.Queue()

# The counter survives a restart, it is kept next to this script.
COUNTER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "counter.txt")

try:
    counter = int(open(COUNTER_FILE).read())
except Exception:
    counter = 0

show_counter = False

# The buttons bounce, so one press can fire the callback several times.
# Presses closer together than this are ignored.
DEBOUNCE = 0.3
last_press = {}


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


def button_pressed(channel):
    global counter
    global show_counter

    now = time.monotonic()
    if now - last_press.get(channel, 0) < DEBOUNCE:
        return
    last_press[channel] = now

    print(f"Button on pin {channel} pressed")

    if channel == BUTTON_BLINK:
        if blink_enabled.is_set():
            blink_enabled.clear()
        else:
            blink_enabled.set()
    elif channel == BUTTON_COUNTER:
        counter = counter + 1
        open(COUNTER_FILE, "w").write(str(counter))
    elif channel == BUTTON_MODE:
        show_counter = not show_counter
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
