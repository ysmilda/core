"""Base entity for Brink Flair."""

from collections.abc import Awaitable

from brink_flair_modbus import BypassOverrideBlockedError
from modbus_connection import ModbusError

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrinkCoordinator


class BrinkEntity(CoordinatorEntity[BrinkCoordinator]):
    """Common identity + device-info for every Brink Flair entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BrinkCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        info = coordinator.device.info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=info.manufacturer,
            model=info.model,
            name=info.model,
            sw_version=info.software_version,
            hw_version=info.hardware_version,
            serial_number=info.serial_number,
        )

    async def _async_write(self, write: Awaitable[None]) -> None:
        """Run a write on the unit and refresh to show its result."""
        try:
            await write
        except BypassOverrideBlockedError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="bypass_override_blocked",
                translation_placeholders={"supply_volume": str(err.supply_volume)},
            ) from err
        except ModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="communication_error",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_request_refresh()
