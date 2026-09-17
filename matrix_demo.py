#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2017-18 Richard Hull and contributors
# See LICENSE.rst for details.

import re
import time
import argparse
import time

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT


def demo():
    # create matrix device
    serial = spi(port=0, device=0, gpio=noop())
    device = max7219(serial, cascaded=4, block_orientation=-90, rotate=0)

    device.contrast(40)
    print(device.height, device.width)
    virtual = viewport(device, width=device.width, height=device.height)


    i = 0
    while True:
        try:
            lines = [line.strip() for line in open('/tmp/data.txt')]
        except:
            lines = []

        with canvas(virtual) as draw:
            if (int(time.time()) % 30) == 0 and len(lines) > 0:
                msg=lines[i]
                i = (i + 1) % len(lines)
                print(msg)
                show_message(device, msg, fill="white", font=proportional(CP437_FONT))
                show_message(device, msg, fill="white", font=proportional(CP437_FONT))
            msg = time.strftime("%H:%M", time.localtime())
#            msg = time.strftime("%M:%S", time.localtime())
            print(msg)
            text(draw, (0,0), msg, fill="white", font=proportional(CP437_FONT))
            time.sleep(0.3)


#    # start demo
#    while True:
#        show_message(device, msg, fill="white", font=proportional(CP437_FONT))
#        text(device, msg, fill="white", font=proportional(CP437_FONT))
#        time.sleep(1)


if __name__ == "__main__":
    try:
       demo()
    except KeyboardInterrupt:
        pass
