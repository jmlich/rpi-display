# LED panel

A small Raspberry Pi toy. It shows the time on an LED matrix, plays internet
streams and reacts to six buttons.

![The box and the dome button](hardware/finished-box.jpg)

A [short video](https://youtu.be/8XoVibW1V2M) shows it running.

## Hardware

- MAX7219 LED matrix, 4 blocks, on SPI port 0
- LED on board pin 22 (GPIO25)
- Creative Bluetooth Audio D1, a USB sound card, ALSA name `D1`
- Buttons on board pins 3, 5, 11, 13, 15 and 18, wired to 3V3

Pin numbers are BOARD numbers, not BCM.

## Run

    ./panel.py

Needs `luma.led_matrix`, `python3-dbus` and `rpi-lgpio`, the maintained
stand-in for `RPi.GPIO`. Stop it with Ctrl-C.

To make the Pi start it on its own, see `setup/README.md`.

## Buttons

| Pin | What it does                     |
|-----|----------------------------------|
| 18  | the big one, starts and stops the player |
| 3   | previous stream                  |
| 5   | next stream                      |
| 13  | volume up                        |
| 11  | volume down                      |
| 15  | scrolls the IPv4 addresses       |

Each press scrolls what it did, for example `NEXT Dvojka` or `VOL UP 50`.
The LED blinks while the player plays. Every press goes to the journal:

    journalctl -t panel

## Player

VLC plays the streams from `playlist.m3u`, started by
`setup/files/player.service`. It waits stopped until the big button. `panel.py`
controls it over MPRIS on the session bus, so it works with any MPRIS player.
The stream name and the volume scroll on the matrix. While it plays, the song
scrolls when it changes and once a minute. The volume is kept in `volume.txt`
next to the script, so it survives a restart.

## Alarms

`alarms.ini` next to the script starts the player at a set time, on the Pi
that is `/opt/panel/alarms.ini`. The file itself says how. An alarm plays the
last stream for `duration` minutes and then stops it, unless somebody presses
the big button. An alarm does nothing when the player already plays. A change
in the file counts from the next minute, no restart is needed.

## Files

`panel.py` is the program. `examples/` holds the older demos it was built
from. They still run on their own. `hardware/` holds the wiring, the case and
the datasheets, see `hardware/README.md`.

## Licensing and attribution

The code in this repository is licensed under the [GNU General Public License,
version 3 or later](LICENSE). The SPDX identifier is `GPL-3.0-or-later`.

Original project documentation, photographs, drawings, and other non-code
artifacts are intended to be distributed under [Creative Commons
Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).
See [LICENSES.md](LICENSES.md) for the scope of that recommendation.

Third-party assets retain their original licensing and attribution. In
particular, the Raspberry Pi 3 model in `hardware/parts/raspberry-pi-3/` is
based on the Thingiverse model by alexandre_willame:
https://www.thingiverse.com/thing:1701186

The manufacturer datasheets in `hardware/datasheets/` are included for
reference and should be treated as vendor-provided material. See
[ATTRIBUTIONS.md](ATTRIBUTIONS.md) for the original source references and
important reuse notes.
