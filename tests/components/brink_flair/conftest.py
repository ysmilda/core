"""Common fixtures for the Brink Flair tests."""

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

from brink_flair_modbus import (
    BypassMode,
    BypassStatus,
    ControlMode,
    FanStatus,
    FrostStatus,
    ModbusParity,
    ModbusSpeed,
    OperatingMode,
    PreheaterStatus,
    VentilationLevel,
    VentilationMode,
)
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.brink_flair.const import (
    CONF_UNIT_ID,
    CONNECTION_TCP,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TYPE
from homeassistant.core import HomeAssistant

TCP_DATA: dict[str, Any] = {
    CONF_TYPE: CONNECTION_TCP,
    CONF_HOST: "127.0.0.1",
    CONF_PORT: DEFAULT_PORT,
    CONF_UNIT_ID: DEFAULT_UNIT_ID,
}
TCP_UNIQUE_ID = "tcp-127.0.0.1-502_20"

# Input registers of a running Flair 300 (device type 24).
INPUT_REGISTERS: dict[int, int] = {
    4000: ord("S") << 8 | 1,  # software S1
    4001: 0x0102,  # software minor 01, fix 02
    4002: 7,  # software build
    4003: 0x0101,  # hardware H1.1
    4004: 24,  # device type of the Flair 300
    4010: 0x1234,  # serial number digits in BCD
    4011: 0x5678,
    4012: 0x9012,
    4020: OperatingMode.MANUAL,
    4022: VentilationMode.NORMAL,
    4023: 150,  # supply pressure, Pa
    4024: 140,  # exhaust pressure, Pa
    4030: FanStatus.RUNNING,
    4031: 150,  # supply volume setpoint
    4032: 148,  # supply volume
    4033: 178,  # supply mass flow
    4034: 1450,  # supply fan speed
    4035: 900,  # supply anemometer speed
    4036: 213,  # supply temperature x10
    4037: 44,  # supply humidity
    4040: FanStatus.RUNNING,
    4041: 150,
    4042: 152,
    4043: 180,
    4044: 1500,
    4045: 950,
    4046: 205,
    4047: 52,
    4050: BypassStatus.CLOSED,
    4060: PreheaterStatus.INACTIVE,
    4070: FrostStatus.NO_FROST,
    4081: 85,  # outside temperature x10
    4082: 0x7FFF,  # no dwelling sensor
    4083: 455,  # RHT humidity x10
    4110: 0x0E1E,  # 14:30
    4111: 0x1C06,  # 28-06
    4114: 12000,  # operating hours, low word
    4115: 720,  # filter hours
    4117: 108000 & 0xFFFF,  # filter volume, low word
    4116: 108000 >> 16,
    4119: 4000000 & 0xFFFF,  # total flow, low word
    4118: 4000000 >> 16,
}

# Holding registers holding the unit's settings.
HOLDING_REGISTERS: dict[int, int] = {
    6000: 50,  # flow presets 0-3
    6001: 100,
    6002: 150,
    6003: 225,
    **{6010 + offset: 30 + 10 * (offset // 2) for offset in range(8)},
    6100: BypassMode.AUTO,
    6101: 240,  # bypass from dwelling x10
    6102: 100,  # bypass from outside x10
    6103: 20,  # bypass hysteresis x10
    6110: 0,
    6111: 90,
    6120: 180,  # filter change days
    6131: 200,
    **{6151 + offset: 800 + 400 * (offset % 2) for offset in range(8)},
    7991: DEFAULT_UNIT_ID,
    7992: ModbusSpeed.BAUD_19200,
    7993: ModbusParity.EVEN,
    8000: ControlMode.STEP,
    8001: VentilationLevel.MEDIUM,
    8002: 150,  # desired flow rate
}


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "homeassistant.components.brink_flair.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a Brink Flair config entry reached over Modbus TCP."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Brink Flair 300",
        data=TCP_DATA,
        unique_id=TCP_UNIQUE_ID,
        entry_id="01JBRINKFLAIR0000000000000",
    )


@pytest.fixture
def mock_modbus_unit(mock_modbus_connection: MockModbusConnection) -> MockModbusUnit:
    """Return the unit at the default address, seeded as a running Flair 300."""
    unit = mock_modbus_connection.for_unit(DEFAULT_UNIT_ID)
    unit.input.update(INPUT_REGISTERS)
    unit.holding.update(HOLDING_REGISTERS)
    return unit


@pytest.fixture(autouse=True)
def mock_shared_connection(
    mock_modbus_connection: MockModbusConnection, mock_modbus_unit: MockModbusUnit
) -> Generator[None]:
    """Hand out units on the seeded mock instead of opening a real connection."""

    @asynccontextmanager
    async def async_temporary_unit(
        hass: HomeAssistant, params: Any, unit_id: int
    ) -> AsyncIterator[MockModbusUnit]:
        yield mock_modbus_connection.for_unit(unit_id)

    with (
        patch(
            "homeassistant.components.brink_flair.async_get_unit",
            side_effect=lambda hass, entry, params, unit_id: (
                mock_modbus_connection.for_unit(unit_id)
            ),
        ),
        patch(
            "homeassistant.components.brink_flair.config_flow.async_get_temporary_unit",
            async_temporary_unit,
        ),
    ):
        yield
