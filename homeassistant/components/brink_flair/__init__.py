"""The Brink Flair integration."""

from brink_flair_modbus import BrinkFlair

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_MODEL, Platform
from homeassistant.core import HomeAssistant

from .connection import params_from_data
from .const import CONF_UNIT_ID
from .coordinator import BrinkConfigEntry, BrinkCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: BrinkConfigEntry) -> None:
    """Set up Brink Flair from a config entry."""
    unit = async_get_unit(
        hass, entry, params_from_data(entry.data), entry.data[CONF_UNIT_ID]
    )
    device = BrinkFlair(unit, model_override=entry.data.get(CONF_MODEL))
    coordinator = BrinkCoordinator(hass, entry, device)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: BrinkConfigEntry) -> None:
    """Unload the config entry and its platforms."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
