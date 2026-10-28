"""Tests for the Brink Flair config flow."""

from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.brink_flair.const import (
    CONF_BAUDRATE,
    CONF_PARITY,
    CONF_UNIT_ID,
    CONNECTION_SERIAL,
    CONNECTION_TCP,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_MODEL, CONF_PORT, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError

from .conftest import TCP_DATA, TCP_UNIQUE_ID

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

TCP_INPUT = {CONF_HOST: "127.0.0.1", CONF_PORT: 502, CONF_UNIT_ID: 20}
SERIAL_INPUT = {
    CONF_DEVICE: "/dev/ttyUSB0",
    CONF_UNIT_ID: 20,
    CONF_BAUDRATE: "19200",
    CONF_PARITY: "E",
}


async def _start_tcp(hass: HomeAssistant) -> str:
    """Start a user flow and pick Modbus TCP, returning the flow id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "modbus_tcp"}
    )
    assert result["type"] is FlowResultType.FORM
    return result["flow_id"]


async def test_tcp_flow(hass: HomeAssistant) -> None:
    """A unit with a mapped device type is set up over TCP."""
    flow_id = await _start_tcp(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, TCP_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovered"

    result = await hass.config_entries.flow.async_configure(flow_id, {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Brink Flair 300"
    assert result["data"] == TCP_DATA
    assert result["result"].unique_id == TCP_UNIQUE_ID


async def test_serial_flow(hass: HomeAssistant) -> None:
    """A unit is set up over a serial line, storing its line settings."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "serial"}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], SERIAL_INPUT
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_TYPE: CONNECTION_SERIAL,
        CONF_DEVICE: "/dev/ttyUSB0",
        CONF_UNIT_ID: 20,
        CONF_BAUDRATE: 19200,
        CONF_PARITY: "E",
    }
    assert result["result"].unique_id == "serial-/dev/ttyUSB0_20"


async def test_unmapped_device_type_asks_model(
    hass: HomeAssistant, mock_modbus_unit: MockModbusUnit
) -> None:
    """A unit reporting an unmapped device type is set up with the chosen model."""
    mock_modbus_unit.input[4004] = 99
    flow_id = await _start_tcp(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, TCP_INPUT)
    assert result["step_id"] == "select_model"
    assert result["description_placeholders"]["device_type"] == "99"

    result = await hass.config_entries.flow.async_configure(
        flow_id, {CONF_MODEL: "450"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Brink Flair 450"
    assert result["data"] == {**TCP_DATA, CONF_MODEL: 450}
    assert result["result"].unique_id == TCP_UNIQUE_ID


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        pytest.param(ModbusError("no answer"), "cannot_connect", id="cannot_connect"),
        pytest.param(
            HomeAssistantError("different link settings"),
            "link_settings_conflict",
            id="link_conflict",
        ),
    ],
)
async def test_flow_errors_recover(
    hass: HomeAssistant, side_effect: Exception, error: str
) -> None:
    """A failed probe shows an error, and the flow finishes once it succeeds."""
    flow_id = await _start_tcp(hass)

    with patch(
        "homeassistant.components.brink_flair.config_flow.async_get_temporary_unit",
        side_effect=side_effect,
    ):
        result = await hass.config_entries.flow.async_configure(flow_id, TCP_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    result = await hass.config_entries.flow.async_configure(flow_id, TCP_INPUT)
    result = await hass.config_entries.flow.async_configure(flow_id, {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == TCP_UNIQUE_ID


async def test_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The same unit cannot be added twice."""
    mock_config_entry.add_to_hass(hass)
    flow_id = await _start_tcp(hass)

    result = await hass.config_entries.flow.async_configure(flow_id, TCP_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def _start_reconfigure(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    """Start a reconfigure flow and pick Modbus TCP, returning the flow id."""
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "modbus_tcp"}
    )
    assert result["type"] is FlowResultType.FORM
    return result["flow_id"]


async def test_reconfigure(
    hass: HomeAssistant, mock_modbus_unit: MockModbusUnit
) -> None:
    """Reconfiguring probes the new address and keeps the chosen model."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**TCP_DATA, CONF_MODEL: 450},
        unique_id=TCP_UNIQUE_ID,
    )
    entry.add_to_hass(hass)
    flow_id = await _start_reconfigure(hass, entry)

    mock_modbus_unit.fail_requests(ModbusError("no answer"))
    result = await hass.config_entries.flow.async_configure(
        flow_id, {**TCP_INPUT, CONF_HOST: "192.0.2.10"}
    )
    assert result["errors"] == {"base": "cannot_connect"}

    mock_modbus_unit.fail_requests(None)
    result = await hass.config_entries.flow.async_configure(
        flow_id, {**TCP_INPUT, CONF_HOST: "192.0.2.10"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        CONF_TYPE: CONNECTION_TCP,
        CONF_HOST: "192.0.2.10",
        CONF_PORT: 502,
        CONF_UNIT_ID: 20,
        CONF_MODEL: 450,
    }
    assert entry.unique_id == "tcp-192.0.2.10-502_20"


async def test_reconfigure_serial_prefills_form(hass: HomeAssistant) -> None:
    """The serial form is prefilled from a serial entry, then saved unchanged."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_TYPE: CONNECTION_SERIAL,
            CONF_DEVICE: "/dev/ttyUSB0",
            CONF_UNIT_ID: 20,
            CONF_BAUDRATE: 19200,
            CONF_PARITY: "E",
        },
        unique_id="serial-/dev/ttyUSB0_20",
    )
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "serial"}
    )
    schema = result["data_schema"].schema
    baudrate = next(key for key in schema if key == CONF_BAUDRATE)
    assert baudrate.description == {"suggested_value": "19200"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], SERIAL_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_BAUDRATE] == 19200


async def test_reconfigure_to_other_entry_aborts(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfiguring onto the address of another entry is refused."""
    mock_config_entry.add_to_hass(hass)
    other = MockConfigEntry(
        domain=DOMAIN,
        data={**TCP_DATA, CONF_HOST: "192.0.2.10"},
        unique_id="tcp-192.0.2.10-502_20",
    )
    other.add_to_hass(hass)
    flow_id = await _start_reconfigure(hass, other)

    result = await hass.config_entries.flow.async_configure(flow_id, TCP_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
