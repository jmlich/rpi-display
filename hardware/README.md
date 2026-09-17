# Hardware

Everything physical about the box. The program that runs on it is `panel.py`
in the top folder.

`BOM.md` lists the parts. `finished-box.jpg` is a photo of the built box.

## schematic/

`schema.fzz` is a [Fritzing](https://fritzing.org/) sketch of the wiring:
a Raspberry Pi 3, the MAX7219 matrix, six buttons (S1 to S6) with a pull-down
resistor each, and one LED with a resistor. `schema_bb.png` is the breadboard
view exported from it.

Board pins used, the same numbers as in `panel.py`:

| Pin | Part                     |
|-----|--------------------------|
| 19, 23, 24 | matrix, SPI port 0 |
| 22  | LED                      |
| 3, 5, 11, 13, 15 | small buttons |
| 18  | big dome button, see below |

## enclosure/

The case, designed in Fusion 360.

- `radio-v3.f3d` is the current version.
- `button.f3d` is a separate case for the big dome button on pin 18. The
  button is a 100 mm [arcade dome button](https://www.odkarla.cz/eg-starts-4-100mm-big-dome-12v-led-podsvicene-tlacitko-s-mikrospinacem-pro-dily-arcade-machine~p1507340).
  It is sold with a 12 V LED inside, ours has a 3.3 V one.
- The window over the LED matrix is a piece of plexiglass, cut by hand to
  fit the cutout in the case. There is no drawing for it, measure it off the
  printed part. The first box had no window and the bare matrix was too
  bright at night. The plexiglass softens it and `panel.py` keeps the
  contrast well under the maximum.
- `drawings/` holds screenshots of the sketches with the measurements:
  - `bottom-plate-dimensions.png` — the plate is 142 x 90 mm
  - `bottom-plate-standoffs.png` — the standoffs that hold the Pi
  - `side-wall-cutouts.png` — the hole and the cutouts in the side wall
  - `front-wall-cutouts.png` — the openings in the front wall
  - `top-plate-mounting-holes.png` — the screw holes in the top plate

## parts/

Models of the bought parts, drawn by other people. They are here so the case
can be designed around them. Do not edit them.

- `raspberry-pi-3/` — from [Thingiverse](https://www.thingiverse.com/thing:1701186),
  see its own `README.txt` and `LICENSE.txt`
- `max7219-matrix/` — the 32x8 matrix module, four 8x8 blocks
- `pbs-18b-button/` — the PBS-18B button in four colours

## datasheets/

- `pbs-18b-button-gme.pdf` and `pbs-18b-button-tru-components.pdf` — the same
  button from two sellers
- `kls15-225-m12-connector.pdf` — the M12 connector in the case wall
