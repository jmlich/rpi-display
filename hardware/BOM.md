# Bill of materials

What goes into one box. The values come from `schematic/schema.fzz`.

| Qty | Part | Note |
|-----|------|------|
| 1 | Raspberry Pi 3 model B | the schematic says RPI-3-V1.2 |
| 1 | MAX7219 LED matrix, 32x8, FC-16 module | four 8x8 blocks, SPI |
| 1 | 40 pin ribbon cable, female to female | see the note below |
| 5 | PBS-18B pushbutton | `datasheets/pbs-18b-button-gme.pdf` |
| 1 | 100 mm arcade dome button with LED | pin 18, a 3.3 V LED inside |
| 1 | red LED, 5 mm | the one that blinks |
| 6 | resistor 4.7k | pull-down, one per button |
| 1 | resistor 100R | for the LED |
| 1 | KLS15-225-M12 connector | `datasheets/kls15-225-m12-connector.pdf` |
| 1 | printed case | `enclosure/radio-v3.f3d` |
| 1 | printed holder for the dome button | `enclosure/button.f3d` |
|   | wires, screws, M2.5 standoffs | |

The schematic draws only five pull-downs, the dome button has one too.

## The header

Everything is wired with jumper wires straight from the GPIO pins, so no
header is needed. A 2x20 female header is only for a board soldered on top of
the Pi. The ones in the shop are all for that:

- a stacking header has long pins that pass through the board, for a second
  board above it
- a 3.5 mm one is surface mount, it is soldered under a HAT
- a 90 degree one turns the board on edge

If a small board for the resistors is ever added, then a plain straight 2x20
female header is the right part.
