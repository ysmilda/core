"""Tests for the Brink Flair integration setup."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from syrupy.assertion import SnapshotAssertion

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import setup_integration


async def test_setup_and_unload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The entry loads and unloads."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_when_unreachable(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """Setup is retried while the unit does not answer."""
    mock_modbus_unit.fail_requests(ModbusError("no answer"))
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unavailable_when_unreachable(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """Entities go unavailable when a poll fails."""
    await setup_integration(hass, mock_config_entry)
    mock_modbus_unit.fail_requests(ModbusError("no answer"))

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.brink_flair_300_supply_temperature")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_device_info(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The device carries the unit's identity."""
    await setup_integration(hass, mock_config_entry)

    assert (
        dr.async_entries_for_config_entry(device_registry, mock_config_entry.entry_id)
        == snapshot
    )


async def test_entities_enabled_by_default(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Only the everyday entities are enabled for a new unit."""
    await setup_integration(hass, mock_config_entry)

    entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    assert {
        "enabled": sorted(e.entity_id for e in entries if e.disabled_by is None),
        "disabled": sorted(e.entity_id for e in entries if e.disabled_by is not None),
    } == snapshot
