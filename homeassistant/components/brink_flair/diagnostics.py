"""Diagnostics support for the Brink Flair integration."""

from typing import Any

from brink_flair_modbus import BrinkComponent

from homeassistant.core import HomeAssistant

from .coordinator import BrinkConfigEntry


def _component_snapshot(component: BrinkComponent) -> dict[str, Any]:
    """Return the decoded register values of a library component."""
    return {name: getattr(component, name) for name in component.declared_fields}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: BrinkConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Host, port, serial path and Modbus address identify no person and are
    needed to diagnose a failing link, so they are not redacted.
    """
    coordinator = config_entry.runtime_data
    device = coordinator.device
    return {
        "entry": dict(config_entry.data),
        "options": dict(config_entry.options),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception),
        },
        "device": {
            "info": _component_snapshot(device.info),
            "measurements": _component_snapshot(device.measurements),
            "settings": _component_snapshot(device.settings),
            "status": _component_snapshot(device.status),
            "flow_limits": vars(device.flow_limits),
        },
    }
