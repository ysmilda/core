"""Binary sensor platform — filter warning of the Brink Flair unit."""

from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BrinkConfigEntry, BrinkCoordinator
from .entity import BrinkEntity

# State arrives through the coordinator; async_update is not used.
PARALLEL_UPDATES = 0

_DESCRIPTION = BinarySensorEntityDescription(
    key="status_filter_dirty",
    translation_key="status_filter_dirty",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Brink Flair binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities([BrinkFilterDirtyBinarySensor(coordinator)])


class BrinkFilterDirtyBinarySensor(BrinkEntity, BinarySensorEntity):
    """Whether the filter counter has expired."""

    entity_description = _DESCRIPTION

    def __init__(self, coordinator: BrinkCoordinator) -> None:
        """Initialize the Brink Flair status binary sensor."""
        super().__init__(coordinator, _DESCRIPTION.key)

    @property
    @override
    def is_on(self) -> bool | None:
        """Return whether the filter is due for a change."""
        return self.coordinator.device.status.filter_dirty
