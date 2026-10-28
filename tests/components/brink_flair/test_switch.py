"""Tests for the Brink Flair switch platform."""

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit, WriteEvent
import pytest
from pytest_homeassistant.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration

STANDBY = "switch.brink_flair_300_standby"
BYPASS_BOOST = "switch.brink_flair_300_bypass_boost"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_switches(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the switch entities."""
    with patch("homeassistant.components.brink_flair.PLATFORMS", [Platform.SWITCH]):
        await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_standby_reads_unit_state(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """The standby switch follows the state the unit reports."""
    mock_modbus_unit.holding[8003] = 1
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(STANDBY)
    assert state is not None
    assert state.state == STATE_ON


@pytest.mark.parametrize(
    ("entity_id", "service", "address", "raw", "expected"),
    [
        pytest.param(STANDBY, SERVICE_TURN_ON, 8003, 1, STATE_ON, id="standby_on"),
        pytest.param(STANDBY, SERVICE_TURN_OFF, 8003, 2, STATE_OFF, id="standby_off"),
        pytest.param(
            BYPASS_BOOST, SERVICE_TURN_ON, 6104, 1, STATE_ON, id="bypass_boost_on"
        ),
    ],
)
async def test_switch_writes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
    entity_id: str,
    service: str,
    address: int,
    raw: int,
    expected: str,
) -> None:
    """Toggling a switch writes its register."""
    await setup_integration(hass, mock_config_entry)
    writes: list[WriteEvent] = []
    mock_modbus_unit.on_write(writes.append)

    await hass.services.async_call(
        SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )

    assert [(event.address, event.values) for event in writes] == [(address, [raw])]
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected
