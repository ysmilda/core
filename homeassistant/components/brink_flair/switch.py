"""Switch platform for Brink Flair."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, override

from brink_flair_modbus import BrinkFlair

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BrinkConfigEntry, BrinkCoordinator
from .entity import BrinkEntity

# State arrives through the coordinator; async_update is not used.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BrinkSwitchDescription(SwitchEntityDescription):
    """Describes a switch over one boolean of the unit."""

    is_on_fn: Callable[[BrinkFlair], bool | None]
    set_fn: Callable[[BrinkFlair, bool], Awaitable[None]]


def _setting(attribute: str, *, enabled: bool = False) -> BrinkSwitchDescription:
    """Describe the switch for a boolean settings field."""
    key = f"settings_{attribute}"

    def is_on(device: BrinkFlair) -> bool | None:
        value = getattr(device.settings, attribute)
        return None if value is None else bool(value)

    return BrinkSwitchDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=enabled,
        is_on_fn=is_on,
        set_fn=lambda device, on: device.settings.write(attribute, on),
    )


SWITCHES: tuple[BrinkSwitchDescription, ...] = (
    BrinkSwitchDescription(
        key="standby",
        translation_key="standby",
        is_on_fn=lambda device: device.standby,
        set_fn=lambda device, on: device.async_set_standby(on),
    ),
    _setting("bypass_boost", enabled=True),
    _setting("display_as_switch"),
    _setting("imbalance_allowed"),
    _setting("rht_sensor_mode"),
    _setting("co2_sensor_mode"),
    _setting("cv_connected"),
    _setting("digital_input_1_closed"),
    _setting("digital_input_2_closed"),
    _setting("analogue_input_1_mode"),
    _setting("analogue_input_2_mode"),
    _setting("geo_exchanger"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Brink Flair switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        BrinkFlairSwitch(coordinator, description) for description in SWITCHES
    )


class BrinkFlairSwitch(BrinkEntity, SwitchEntity):
    """A switch over one boolean of the unit."""

    entity_description: BrinkSwitchDescription

    def __init__(
        self, coordinator: BrinkCoordinator, description: BrinkSwitchDescription
    ) -> None:
        """Initialize the switch from its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the state read from the unit."""
        return self.entity_description.is_on_fn(self.coordinator.device)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_write(
            self.entity_description.set_fn(self.coordinator.device, True)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_write(
            self.entity_description.set_fn(self.coordinator.device, False)
        )
