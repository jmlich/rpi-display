# Bill of materials

What goes into one box. The values come from `schematic/schema.fzz`.

| Qty | Part | Note |
|-----|------|------|
| 1 | Raspberry Pi 3 model B | the schematic says RPI-3-V1.2 |
| 1 | MAX7219 LED matrix, 32x8, FC-16 module | four 8x8 blocks, SPI |
| 1 | [2x20 pin header extender](https://rpishop.cz/headery/127-stohovatelny-2x20-pinovy-nastavec.html) | see the note below |
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

The linked one is a stacking header, it has long pins that go through the
board so another board can sit on top. Nothing sits on top of this Pi, so a
plain 2x20 extender is enough. Buy the stacking one only if it is easier to
get.
