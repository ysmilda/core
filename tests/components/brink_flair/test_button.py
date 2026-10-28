"""Tests for the Brink Flair button platform."""

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit, WriteEvent
from pytest_homeassistant.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration

ENTITY_ID = "button.brink_flair_300_filter_reset"


async def test_buttons(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the button entities."""
    with patch("homeassistant.components.brink_flair.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_reset_filter(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """Pressing the button pulses the filter reset bit."""
    await setup_integration(hass, mock_config_entry)
    writes: list[WriteEvent] = []
    mock_modbus_unit.on_write(writes.append)

    # The unit only sees the pulse if the bit is held; skip the real wait.
    with patch("brink_flair_modbus.device.asyncio.sleep"):
        await hass.services.async_call(
            BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
        )

    assert [(event.address, event.values) for event in writes] == [
        (8010, [1]),
        (8010, [0]),
    ]
