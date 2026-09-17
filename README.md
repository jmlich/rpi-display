# LED panel

A small Raspberry Pi toy. It shows the time on an LED matrix, blinks an LED
and reacts to six buttons.

## Hardware

- MAX7219 LED matrix, 4 blocks, on SPI port 0
- LED on board pin 22 (GPIO25)
- Buttons on board pins 3, 5, 11, 13, 15 and 18, wired to 3V3

Pin numbers are BOARD numbers, not BCM.

## Run

    ./panel.py

Needs `RPi.GPIO` and `luma.led_matrix`. Stop it with Ctrl-C.

To make the Pi start it on its own, see `setup/README.md`.

## Buttons

| Pin | What it does                |
|-----|-----------------------------|
| 3   | turns blinking on and off   |
| 5   | switches time and counter   |
| 18  | adds one to the counter     |
| 11, 13, 15 | scroll their pin name |

The counter is kept in `counter.txt` next to the script, so it survives a
restart.

## Files

`panel.py` is the program. `examples/` holds the older demos it was built
from. They still run on their own. `hardware/` holds the wiring, the case and
the datasheets, see `hardware/README.md`.
