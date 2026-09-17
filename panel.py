#!/usr/bin/python3

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

counter = 0
show_counter = False


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

    print(f"Button on pin {channel} pressed")

    if channel == BUTTON_BLINK:
        if blink_enabled.is_set():
            blink_enabled.clear()
        else:
            blink_enabled.set()
    elif channel == BUTTON_COUNTER:
        counter = counter + 1
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
            bouncetime=50
        )


def make_device():
    serial = spi(port=0, device=0, gpio=noop())
    # rotate=2 because the matrix is mounted upside down
    device = max7219(serial, cascaded=4, block_orientation=-90, rotate=2)
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
    setup_gpio()
    device = make_device()

    blink_thread = threading.Thread(target=blink_loop)
    blink_thread.start()

    try:
        display_loop(device)
    except KeyboardInterrupt:
        pass
    finally:
        stop_blinking.set()
        blink_thread.join()
        GPIO.output(LED, GPIO.LOW)
        GPIO.cleanup()


if __name__ == "__main__":
    main()
