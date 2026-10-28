"""Turn a config entry's transport fields into a Modbus params object."""

from collections.abc import Mapping
from typing import Any

from modbus_connection import ModbusSerialParams, ModbusTcpParams

from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_PORT, CONF_TYPE

from .const import CONF_BAUDRATE, CONF_PARITY, CONNECTION_SERIAL


def params_from_data(data: Mapping[str, Any]) -> ModbusTcpParams | ModbusSerialParams:
    """Return the Modbus connection params described by ``data``."""
    if data[CONF_TYPE] == CONNECTION_SERIAL:
        return ModbusSerialParams(
            device=data[CONF_DEVICE],
            baudrate=data[CONF_BAUDRATE],
            bytesize=8,
            parity=data[CONF_PARITY],
            stopbits=1,
            framer="rtu",
        )
    return ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT])
