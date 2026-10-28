"""Number platform for Brink Flair."""

from dataclasses import dataclass
from typing import override

from brink_flair_modbus import FlowLimits, Settings

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BrinkConfigEntry, BrinkCoordinator
from .entity import BrinkEntity

# State arrives through the coordinator; async_update is not used.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BrinkNumberDescription(NumberEntityDescription):
    """Describes a number over one numeric settings field."""

    attribute: str


def _number(
    attribute: str,
    *,
    enabled: bool = False,
    config: bool = True,
    device_class: NumberDeviceClass | None = None,
    unit: str | None = None,
    maximum: float | None = None,
) -> BrinkNumberDescription:
    """Describe a settings number; the range comes from the library's metadata."""
    metadata = Settings.metadata(attribute).number
    assert metadata is not None
    key = f"settings_{attribute}"
    return BrinkNumberDescription(
        key=key,
        translation_key=key,
        attribute=attribute,
        native_min_value=metadata.min_value or 0,
        native_max_value=maximum if maximum is not None else metadata.max_value or 0,
        native_step=metadata.step or 1,
        mode=NumberMode.BOX,
        device_class=device_class,
        native_unit_of_measurement=unit,
        entity_category=EntityCategory.CONFIG if config else None,
        entity_registry_enabled_default=enabled,
    )


def _temperature(attribute: str, *, enabled: bool = False) -> BrinkNumberDescription:
    return _number(
        attribute,
        enabled=enabled,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
    )


def _flow(
    attribute: str, maximum: int, *, config: bool = True
) -> BrinkNumberDescription:
    return _number(
        attribute,
        enabled=True,
        config=config,
        device_class=NumberDeviceClass.VOLUME_FLOW_RATE,
        unit=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        maximum=maximum,
    )


def _descriptions(limits: FlowLimits) -> tuple[BrinkNumberDescription, ...]:
    """Describe the numbers, capping airflow at the detected model's envelope."""
    return (
        _flow("desired_flow_rate", limits.modbus_flow_rate_max, config=False),
        *(_flow(f"flow_{step}", limits.flow_max) for step in range(4)),
        _number("filter_change_days", enabled=True, unit=UnitOfTime.DAYS),
        _temperature("bypass_from_dwelling", enabled=True),
        _temperature("bypass_from_outside", enabled=True),
        _temperature("bypass_hysteresis"),
        _number("bypass_boost_position"),
        *(
            _number(f"pwm_{fan}_{step}", unit=PERCENTAGE)
            for step in range(4)
            for fan in ("inlet", "exhaust")
        ),
        _number("switch_default_position"),
        _number("imbalance_value", unit=PERCENTAGE),
        _number("imbalance_intake", unit=PERCENTAGE),
        _number("imbalance_exhaust", unit=PERCENTAGE),
        _temperature("frost_control_temperature"),
        _temperature("frost_minimum_inlet_temperature"),
        _temperature("postheater_setpoint"),
        _number("rht_sensor_sensitivity"),
        *(
            _number(
                f"co2_{sensor}_{bound}_level",
                device_class=NumberDeviceClass.CO2,
                unit=UnitOfRatio.PARTS_PER_MILLION,
            )
            for sensor in range(1, 5)
            for bound in ("low", "high")
        ),
        *(
            _number(
                f"analogue_input_{port}_v{bound}",
                device_class=NumberDeviceClass.VOLTAGE,
                unit=UnitOfElectricPotential.VOLT,
            )
            for port in (1, 2)
            for bound in ("min", "max")
        ),
        _temperature("geo_minimum_temperature"),
        _temperature("geo_maximum_temperature"),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Brink Flair numbers."""
    coordinator = entry.runtime_data
    async_add_entities(
        BrinkFlairNumber(coordinator, description)
        for description in _descriptions(coordinator.device.flow_limits)
    )


class BrinkFlairNumber(BrinkEntity, NumberEntity):
    """A number over one numeric settings field."""

    entity_description: BrinkNumberDescription

    def __init__(
        self, coordinator: BrinkCoordinator, description: BrinkNumberDescription
    ) -> None:
        """Initialize the number from its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    @override
    def native_value(self) -> float | None:
        """Return the value read from the unit."""
        value: float | None = getattr(
            self.coordinator.device.settings, self.entity_description.attribute
        )
        return value

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Write the value to the unit."""
        await self._async_write(
            self.coordinator.device.settings.write(
                self.entity_description.attribute, value
            )
        )
