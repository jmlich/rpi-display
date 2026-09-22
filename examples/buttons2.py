#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 jmlich

import RPi.GPIO as GPIO
import time

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

BUTTONS = [3, 5, 11, 13, 15, 18]

for pin in BUTTONS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


def button_pressed(channel):
    print(f"Button on pin {channel} pressed")


for pin in BUTTONS:
    GPIO.add_event_detect(
        pin,
        GPIO.RISING,
        callback=button_pressed,
        bouncetime=50
    )

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
