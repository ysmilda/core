"""DataUpdateCoordinator that polls the Brink Flair unit."""

import logging
from typing import override

from brink_flair_modbus import BrinkFlair
from modbus_connection import ModbusError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type BrinkConfigEntry = ConfigEntry[BrinkCoordinator]


class BrinkCoordinator(DataUpdateCoordinator[BrinkFlair]):
    """Poll a Brink Flair unit."""

    config_entry: BrinkConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: BrinkConfigEntry,
        device: BrinkFlair,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device

    @override
    async def _async_update_data(self) -> BrinkFlair:
        try:
            await self.device.async_update()
        except ModbusError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="communication_error",
                translation_placeholders={"error": str(err)},
            ) from err
        return self.device
