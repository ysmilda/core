"""Sensor platform for Brink Flair."""

from dataclasses import dataclass
from enum import IntEnum
from typing import cast, override

from brink_flair_modbus import (
    BypassStatus,
    FanStatus,
    FrostStatus,
    ModbusParity,
    ModbusSpeed,
    OperatingMode,
    PreheaterStatus,
    SystemErrorStatus,
    VentilationMode,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfPressure,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BrinkConfigEntry, BrinkCoordinator
from .entity import BrinkEntity

# State arrives through the coordinator; async_update is not used.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BrinkSensorDescription(SensorEntityDescription):
    """Describes a sensor reading one attribute of one component."""

    component: str
    attribute: str


def _sensor(
    component: str,
    attribute: str,
    *,
    enabled: bool = True,
    diagnostic: bool = False,
    device_class: SensorDeviceClass | None = None,
    native_unit_of_measurement: str | None = None,
    state_class: SensorStateClass | None = None,
    suggested_display_precision: int | None = None,
    options: list[str] | None = None,
) -> BrinkSensorDescription:
    """Describe the sensor for ``component.attribute``."""
    key = f"{component}_{attribute}"
    return BrinkSensorDescription(
        key=key,
        translation_key=key,
        component=component,
        attribute=attribute,
        entity_registry_enabled_default=enabled,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
        device_class=device_class,
        native_unit_of_measurement=native_unit_of_measurement,
        state_class=state_class,
        suggested_display_precision=suggested_display_precision,
        options=options,
    )


def _enum(
    component: str,
    attribute: str,
    enum_type: type[IntEnum],
    *,
    enabled: bool = True,
    diagnostic: bool = True,
) -> BrinkSensorDescription:
    """Describe an enum sensor showing the member name."""
    return _sensor(
        component,
        attribute,
        enabled=enabled,
        diagnostic=diagnostic,
        device_class=SensorDeviceClass.ENUM,
        options=[option.name.lower() for option in enum_type],
    )


def _temperature(attribute: str, *, enabled: bool = True) -> BrinkSensorDescription:
    return _sensor(
        "measurements",
        attribute,
        enabled=enabled,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    )


def _humidity(attribute: str, *, enabled: bool = True) -> BrinkSensorDescription:
    return _sensor(
        "measurements",
        attribute,
        enabled=enabled,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    )


def _flow(
    attribute: str, *, enabled: bool = True, diagnostic: bool = False
) -> BrinkSensorDescription:
    return _sensor(
        "measurements",
        attribute,
        enabled=enabled,
        diagnostic=diagnostic,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _rpm(attribute: str, *, enabled: bool = True) -> BrinkSensorDescription:
    return _sensor(
        "measurements",
        attribute,
        enabled=enabled,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _measurement_percentage(attribute: str) -> BrinkSensorDescription:
    return _sensor(
        "measurements",
        attribute,
        enabled=False,
        diagnostic=True,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _pressure(attribute: str) -> BrinkSensorDescription:
    return _sensor(
        "measurements",
        attribute,
        enabled=False,
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PA,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _total_volume(attribute: str, *, enabled: bool) -> BrinkSensorDescription:
    return _sensor(
        "measurements",
        attribute,
        enabled=enabled,
        diagnostic=True,
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    )


def _co2(sensor: int) -> BrinkSensorDescription:
    return _sensor(
        "status",
        f"co2_{sensor}_value",
        enabled=False,
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
    )


SENSORS: tuple[BrinkSensorDescription, ...] = (
    _temperature("supply_temperature"),
    _temperature("exhaust_temperature"),
    _temperature("outside_temperature"),
    # Only fitted to the Flair 450/600; reads as absent on other models.
    _temperature("dwelling_temperature", enabled=False),
    _humidity("supply_relative_humidity"),
    _humidity("exhaust_relative_humidity"),
    # Only present when the optional RHT sensor is installed.
    _humidity("rht_humidity", enabled=False),
    _flow("supply_volume"),
    _flow("exhaust_volume"),
    _flow("setpoint_supply_volume", enabled=False, diagnostic=True),
    _flow("setpoint_exhaust_volume", enabled=False, diagnostic=True),
    _rpm("supply_fan_rpm"),
    _rpm("exhaust_fan_rpm"),
    _rpm("supply_anemometer_rpm", enabled=False),
    _rpm("exhaust_anemometer_rpm", enabled=False),
    _pressure("supply_pressure"),
    _pressure("exhaust_pressure"),
    _sensor(
        "measurements",
        "supply_mass_flow",
        enabled=False,
        native_unit_of_measurement="kg/h",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _sensor(
        "measurements",
        "exhaust_mass_flow",
        enabled=False,
        native_unit_of_measurement="kg/h",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _sensor(
        "measurements",
        "bypass_step_position",
        enabled=False,
        diagnostic=True,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    _measurement_percentage("preheater_capacity"),
    _measurement_percentage("frost_heater_setpoint"),
    _measurement_percentage("frost_fan_reduction"),
    _sensor(
        "device",
        "exchange_filter_in",
        diagnostic=True,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
    ),
    _sensor(
        "measurements",
        "filter_used_hours",
        enabled=False,
        diagnostic=True,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    _total_volume("filter_used_volume", enabled=False),
    _total_volume("total_flow", enabled=False),
    _sensor(
        "measurements",
        "current_operating_time",
        enabled=False,
        diagnostic=True,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    _sensor("measurements", "current_time", enabled=False, diagnostic=True),
    _sensor("measurements", "current_date", enabled=False, diagnostic=True),
    _enum("status", "operation_mode", OperatingMode, diagnostic=False),
    _enum("status", "bypass_status", BypassStatus),
    _enum("status", "frost_status", FrostStatus),
    _enum("status", "system_error", SystemErrorStatus),
    _sensor("status", "active_incident", diagnostic=True),
    _enum("status", "ventilation_mode", VentilationMode, enabled=False),
    _enum("status", "preheater_status", PreheaterStatus, enabled=False),
    _enum("status", "supply_fan_status", FanStatus, enabled=False),
    _enum("status", "exhaust_fan_status", FanStatus, enabled=False),
    *(_co2(sensor) for sensor in range(1, 5)),
    # The link settings are only changed on the unit itself (see config_flow),
    # but are shown so a mismatch with the configured connection can be spotted.
    _sensor("settings", "modbus_slave_address", enabled=False, diagnostic=True),
    _enum("settings", "modbus_speed", ModbusSpeed, enabled=False),
    _enum("settings", "modbus_parity", ModbusParity, enabled=False),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Brink Flair sensors."""
    coordinator = entry.runtime_data
    async_add_entities(BrinkSensor(coordinator, description) for description in SENSORS)


class BrinkSensor(BrinkEntity, SensorEntity):
    """A single value read from a component attribute."""

    entity_description: BrinkSensorDescription

    def __init__(
        self, coordinator: BrinkCoordinator, description: BrinkSensorDescription
    ) -> None:
        """Initialize the sensor from its description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    @override
    def native_value(self) -> int | float | str | None:
        """Return the value, enums as their lowercase member name."""
        device = self.coordinator.device
        component = self.entity_description.component
        source = device if component == "device" else getattr(device, component)
        value = getattr(source, self.entity_description.attribute)
        if isinstance(value, IntEnum):
            return value.name.lower()
        return cast(int | float | str | None, value)
