"""Constants for the Brink Flair integration."""

from datetime import timedelta
from typing import Final

from brink_flair_modbus import ModbusSpeed

DOMAIN: Final = "brink_flair"

CONF_UNIT_ID: Final = "unit_id"
DEFAULT_UNIT_ID: Final = 20  # the unit's default Modbus station address

# Transport selection (stored under homeassistant.const.CONF_TYPE).
CONNECTION_TCP: Final = "tcp"
CONNECTION_SERIAL: Final = "serial"

# How this integration reaches the unit. These describe the connection only:
# they are never written to the device, so they have to match the unit's own
# line settings, which are changed with Brink's service menu.
CONF_BAUDRATE: Final = "baudrate"
CONF_PARITY: Final = "parity"

DEFAULT_PORT: Final = 502
DEFAULT_BAUDRATE: Final = 19200  # the unit's factory line setting
DEFAULT_PARITY: Final = "E"  # even, as shipped

# ``ModbusSpeed`` values are register indices (0-7), so the rate comes from the name.
BAUDRATES: Final = tuple(
    int(member.name.removeprefix("BAUD_")) for member in ModbusSpeed
)
# Shown as SelectOptionDict labels: translation keys must be lower-case, codes not.
PARITY_LABELS: Final = {"N": "None", "E": "Even", "O": "Odd"}

# Reading a unit costs one Modbus request per register group, and a ventilation
# unit is usually one of several devices on a shared, slow bus. A minute is short
# enough to react to a changed setting, long enough to keep the bus quiet.
SCAN_INTERVAL: Final = timedelta(seconds=60)
