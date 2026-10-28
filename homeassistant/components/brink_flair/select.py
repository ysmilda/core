"""Select platform for Brink Flair."""

from dataclasses import dataclass
from enum import IntEnum
from typing import override

from brink_flair_modbus import (
    BypassMode,
    ControlMode,
    DateFormat,
    DigitalInputFunction,
    ExternalHeaterMode,
    FanFunction,
    FlowType,
    GeoValveOutput,
    GeoValvePosition,
    Language,
    SignalOutputFunction,
    TimeNotation,
    VentilationLevel,
)

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BrinkConfigEntry, BrinkCoordinator
from .entity import BrinkEntity

# State arrives through the coordinator; async_update is not used.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BrinkSelectDescription(SelectEntityDescription):
    """Describes a select over one enum settings field."""

    attribute: str
    enum_type: type[IntEnum]


def _select(
    attribute: str,
    enum_type: type[IntEnum],
    *,
    enabled: bool = False,
    config: bool = True,
) -> BrinkSelectDescription:
    key = f"settings_{attribute}"
    return BrinkSelectDescription(
        key=key,
        translation_key=key,
        attribute=attribute,
        enum_type=enum_type,
        options=[option.name.lower() for option in enum_type],
        entity_category=EntityCategory.CONFIG if config else None,
        entity_registry_enabled_default=enabled,
    )


SELECTS: tuple[BrinkSelectDescription, ...] = (
    _select("level", VentilationLevel, enabled=True, config=False),
    _select("control_mode", ControlMode, enabled=True),
    _select("bypass_mode", BypassMode, enabled=True),
    _select("flow_type", FlowType),
    _select("external_heater_mode", ExternalHeaterMode),
    _select("signal_output_function", SignalOutputFunction),
    _select("digital_input_1_function", DigitalInputFunction),
    _select("digital_input_1_supply_fan", FanFunction),
    _select("digital_input_1_exhaust_fan", FanFunction),
    _select("digital_input_2_function", DigitalInputFunction),
    _select("digital_input_2_supply_fan", FanFunction),
    _select("digital_input_2_exhaust_fan", FanFunction),
    _select("geo_valve_default_position", GeoValvePosition),
    _select("geo_valve_output", GeoValveOutput),
    _select("language", Language),
    _select("date_format", DateFormat),
    _select("time_notation", TimeNotation),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Brink Flair selects."""
    coordinator = entry.runtime_data
    async_add_entities(
        BrinkFlairSelect(coordinator, description) for description in SELECTS
    )


class BrinkFlairSelect(BrinkEntity, SelectEntity):
    """A dropdown for one enum settings field."""

    entity_description: BrinkSelectDescription

    def __init__(
        self, coordinator: BrinkCoordinator, description: BrinkSelectDescription
    ) -> None:
        """Initialize the select from its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    @override
    def current_option(self) -> str | None:
        """Return the current value as a lowercase option name."""
        value: IntEnum | None = getattr(
            self.coordinator.device.settings, self.entity_description.attribute
        )
        return None if value is None else value.name.lower()

    @override
    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the unit."""
        device = self.coordinator.device
        value = self.entity_description.enum_type[option.upper()]
        if isinstance(value, BypassMode):
            await self._async_write(device.async_set_bypass_mode(value))
        else:
            await self._async_write(
                device.settings.write(self.entity_description.attribute, value)
            )
