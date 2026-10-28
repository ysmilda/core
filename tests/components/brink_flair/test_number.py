"""Tests for the Brink Flair number platform."""

from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit, WriteEvent
import pytest
from pytest_homeassistant.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from . import setup_integration

DESIRED_FLOW = "number.brink_flair_300_desired_flow_rate"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_numbers(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the number entities."""
    with patch("homeassistant.components.brink_flair.PLATFORMS", [Platform.NUMBER]):
        await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "value", "address", "raw"),
    [
        pytest.param(DESIRED_FLOW, 200, 8002, 200, id="desired_flow_rate"),
        pytest.param(
            "number.brink_flair_300_bypass_temperature_inside",
            25.5,
            6101,
            255,
            id="bypass_from_dwelling",
        ),
    ],
)
async def test_set_value(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
    entity_id: str,
    value: float,
    address: int,
    raw: int,
) -> None:
    """Setting a number writes its register and shows the read-back value."""
    await setup_integration(hass, mock_config_entry)
    writes: list[WriteEvent] = []
    mock_modbus_unit.on_write(writes.append)

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )

    assert [(event.address, event.values) for event in writes] == [(address, [raw])]
    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == value


async def test_desired_flow_capped_by_model(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The desired flow rate stops at the Flair 300's Modbus maximum."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(DESIRED_FLOW)
    assert state is not None
    assert state.attributes["max"] == 280


async def test_set_value_communication_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """A failed write is reported as a Home Assistant error."""
    await setup_integration(hass, mock_config_entry)
    mock_modbus_unit.fail_write(8002, ModbusError("no answer"))

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: DESIRED_FLOW, ATTR_VALUE: 200},
            blocking=True,
        )

    assert err.value.translation_key == "communication_error"
