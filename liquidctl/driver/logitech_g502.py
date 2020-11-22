"""liquidctl drivers for the Logitech Hero G502 Mouse.

Supported devices:

- Logitech G502 Hero

Copyright (C) 2020–2020  Marshall Asch and contributors
SPDX-License-Identifier: GPL-3.0-or-later
"""

import itertools
import logging
import re

from enum import Enum, unique

from liquidctl.driver.usb import UsbHidDriver
from liquidctl.keyval import RuntimeStorage
from liquidctl.pmbus import compute_pec
from liquidctl.util import clamp, fraction_of_byte, u16le_from, normalize_profile
from liquidctl.error import NotSupportedByDevice

LOGGER = logging.getLogger(__name__)




class LogitechHero502(UsbHidDriver):
    """Logitech G502 Hero Mouse."""

    SUPPORTED_DEVICES = [
        (0x046D, 0xC08B, None, 'Logitech G502 Hero (experimental)', {}),
    ]

    def __init__(self, device, description, **kwargs):
        super().__init__(device, description, **kwargs)
        # the following fields are only initialized in connect()
        self._data = None

    def connect(self, **kwargs):
        """Connect to the device."""
        super().connect(**kwargs)
        ids = f'vid{self.vendor_id:04x}_pid{self.product_id:04x}'
        # must use the HID path because there is no serial number; however,
        # these can be quite long on Windows and macOS, so only take the
        # numbers, since they are likely the only parts that vary between two
        # devices of the same model
        loc = 'loc' + '_'.join(re.findall(r'\d+', self.address))
        self._data = RuntimeStorage(key_prefixes=[ids, loc])

    def initialize(self, pump_mode='balanced', **kwargs):
        """Initialize the device and set the pump mode.

        The device should be initialized every time it is powered on, including when
        the system resumes from suspending to memory.

        Valid values for `pump_mode` are 'quiet', 'balanced' and 'extreme'.
        Unconfigured fan channels may default to 100% duty.  Subsequent calls
        should leave the fan speeds unaffected.

        Returns a list of `(property, value, unit)` tuples.
        """
        
        return []

    def get_status(self, **kwargs):
        """Get a status report.

        Returns a list of `(property, value, unit)` tuples.
        """

        return []

    def set_fixed_speed(self, channel, duty, **kwargs):
        """Set fan or fans to a fixed speed duty.
        """
        raise NotSupportedByDevice()

    def set_speed_profile(self, channel, profile, **kwargs):
        """Set fan or fans to follow a speed duty profile.
        """
        raise NotSupportedByDevice()

    def set_color(self, channel, mode, colors, unsafe=None, **kwargs):
        """Set the color of each LED.

        In reality the device does not have the concept of different channels
        or modes, but this driver provides a few for convenience.  Animations
        still require successive calls to this API.

        The 'led' channel can be used to address individual LEDs, and supports
        the 'super-fixed', 'fixed' and 'off' modes.

        In 'super-fixed' mode, each color in `colors` is applied to one
        individual LED, successively.  LEDs for which no color has been
        specified default to off/solid black.  This is closest to how the
        device works.

        In 'fixed' mode, all LEDs are set to the first color taken from
        `colors`.  The `off` mode is equivalent to calling this function with
        'fixed' and a single solid black color in `colors`.

        The `colors` argument should be an iterable of one or more `[red, blue,
        green]` triples, where each red/blue/green component is a value in the
        range 0–255.

        The table bellow summarizes the available channels, modes, and their
        associated maximum number of colors for each device family.

        | Channel  | Mode        | LEDs         | Platinum | PRO XT |
        | -------- | ----------- | ------------ | -------- | ------ |
        | led      | off         | synchronized |        0 |      0 |
        | led      | fixed       | synchronized |        1 |      1 |
        | led      | super-fixed | independent  |       24 |     16 |

        Note: lighting control of PRO XT devices is experimental and requires
        the `pro_xt_lighting` constant to be supplied in the `unsafe` iterable.
        """

        channel = channel.lower()
        mode = mode.lower()
        colors = list(colors)

        if channel == 'dpi':
            channel = 0x00
        elif channel == 'logo':
            channel = 0x01
        else:
            raise ValueError(f'Channel {channel} invalid, must be one of ("dpi", "logo")')


        if mode == 'off':
            mode = 0x00
        elif mode == 'fixed':
            mode = 0x01
        elif mode == 'breathing':
            mode = 0x02
        elif mode == 'rainbow':
            mode = 0x03
        else:
            raise ValueError(f'Mode {mode} invalid, must be one of ("off", "fixed", "breathing", "rainbow")')



        if (mode == 'fixed' or mode == 'breathing') and len(colors) != 1:
            raise ValueError('One color must be given')

        color = (0,0,0) if len(colors) == 0 else colors[0]
        

        _REPORT_LENGTH = 20

        buf = bytearray(_REPORT_LENGTH + 1)

        buf[1] = 0x11
        buf[2] = 0xFF
        buf[3] = 0x02
        buf[4] = 0x3A
        buf[5] = channel 
        buf[6] = mode
        buf[7] = color[0]
        buf[8] = color[1]
        buf[9] = color[2]
        
        if mode == 0x01:
            buf[10] = 0x02
        
        self.device.clear_enqueued_reports()
        self.device.write(buf)
        
        buf = bytes(self.device.read(_REPORT_LENGTH))


