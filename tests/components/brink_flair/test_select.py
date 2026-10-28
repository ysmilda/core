"""Tests for the Brink Flair select platform."""

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit, WriteEvent
import pytest
from pytest_homeassistant.common import MockConfigEntry, snapshot_platform
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from . import setup_integration

LEVEL = "select.brink_flair_300_ventilation_level"
BYPASS_MODE = "select.brink_flair_300_bypass_mode"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_selects(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the select entities."""
    with patch("homeassistant.components.brink_flair.PLATFORMS", [Platform.SELECT]):
        await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "option", "address", "raw"),
    [
        pytest.param(LEVEL, "high", 8001, 3, id="level"),
        pytest.param(BYPASS_MODE, "closed", 6100, 1, id="bypass_closed"),
        pytest.param(BYPASS_MODE, "open", 6100, 2, id="bypass_open_low_flow"),
    ],
)
async def test_select_option(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
    entity_id: str,
    option: str,
    address: int,
    raw: int,
) -> None:
    """Selecting an option writes its register and shows the read-back value."""
    await setup_integration(hass, mock_config_entry)
    writes: list[WriteEvent] = []
    mock_modbus_unit.on_write(writes.append)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: option},
        blocking=True,
    )

    assert [(event.address, event.values) for event in writes] == [(address, [raw])]
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == option


async def test_bypass_open_blocked_at_high_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """Forcing the bypass open is refused while the supply flow is high."""
    mock_modbus_unit.input[4032] = 250
    await setup_integration(hass, mock_config_entry)
    writes: list[WriteEvent] = []
    mock_modbus_unit.on_write(writes.append)

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: BYPASS_MODE, ATTR_OPTION: "open"},
            blocking=True,
        )

    assert err.value.translation_key == "bypass_override_blocked"
    assert err.value.translation_placeholders == {"supply_volume": "250"}
    assert not writes
