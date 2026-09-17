# Setup

`setup.sh` turns a normal Raspberry Pi OS installation into the panel. Copy
the repository to the Pi and run:

    sudo setup/setup.sh

It does these steps, in this order:

| Step | What it does |
|------|--------------|
| `install_packages` | apt: `python3-rpi.gpio`, `python3-spidev`, `python3-venv` |
| `install_panel` | copies `panel.py` and `files/panel-shell` to `/opt/panel` |
| `make_venv` | a venv in `/opt/panel/venv` with `luma.led_matrix` from pip |
| `create_user` | user `panel` in the `gpio` and `spi` groups |
| `enable_spi` | adds `dtparam=spi=on` to `config.txt` |
| `set_shell` | makes `/opt/panel/panel-shell` the login shell of `panel` |
| `enable_autologin` | logs `panel` in on tty1 |

Give a step name to run only that one, for example:

    sudo setup/setup.sh enable_spi

Running a step again is safe.

## How it starts

The `panel` user has no normal shell. Its login shell is `panel-shell`, which
only runs `panel.py`. Getty logs the user in on tty1 and starts the shell, so
when `panel.py` ends, getty logs the user in again and it starts over.

After `install_panel` the program runs from `/opt/panel/panel.py`. Run that
step again after changing the code.

## Later: a whole image

The plan is a [pi-gen](https://github.com/RPi-Distro/pi-gen) stage, like
[stage4.5-cutiepi](https://github.com/cutiepi-io/pi-gen_stage4.5-cutiepi),
that builds an SD card image with all of this already done. The steps above
are the content of such a stage, so they can move there later.
