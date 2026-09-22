#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 jmlich

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)

LED = 22  # Physical pin 22 = GPIO25

GPIO.setup(LED, GPIO.OUT)

try:
    while True:
        GPIO.output(LED, GPIO.HIGH)
        time.sleep(1)

        GPIO.output(LED, GPIO.LOW)
        time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    GPIO.output(LED, GPIO.LOW)
    GPIO.cleanup()
