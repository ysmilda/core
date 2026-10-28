"""Button platform — one-shot actions of the Brink Flair unit."""

from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BrinkConfigEntry, BrinkCoordinator
from .entity import BrinkEntity

# State arrives through the coordinator; async_update is not used.
PARALLEL_UPDATES = 0

_RESET_FILTER = ButtonEntityDescription(
    key="reset_filter",
    translation_key="reset_filter",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Brink Flair buttons."""
    coordinator = entry.runtime_data
    async_add_entities([BrinkFlairButton(coordinator)])


class BrinkFlairButton(BrinkEntity, ButtonEntity):
    """Pulses the filter-reset bit on the unit."""

    entity_description = _RESET_FILTER

    def __init__(self, coordinator: BrinkCoordinator) -> None:
        """Initialize the filter reset button."""
        super().__init__(coordinator, _RESET_FILTER.key)

    @override
    async def async_press(self) -> None:
        """Reset the filter counter."""
        await self._async_write(self.coordinator.device.async_reset_filter())
