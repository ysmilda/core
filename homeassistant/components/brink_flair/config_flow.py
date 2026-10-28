"""Config flow for Brink Flair."""

from collections.abc import Mapping
from typing import Any, override
from urllib.parse import urlencode

from brink_flair_modbus import (
    SUPPORTED_MODELS,
    BrinkFlair,
    BrinkProbe,
    is_known_device_type,
    model_name_for_device_type,
)
from modbus_connection import ModbusError
import probatio

from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_MODEL, CONF_PORT, CONF_TYPE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SerialPortSelector,
)

from .connection import params_from_data
from .const import (
    BAUDRATES,
    CONF_BAUDRATE,
    CONF_PARITY,
    CONF_UNIT_ID,
    CONNECTION_SERIAL,
    CONNECTION_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    PARITY_LABELS,
)

_GITHUB_ISSUES_NEW = "https://github.com/ysmilda/brink-flair-modbus/issues/new"
_GITHUB_MAPPING_EDIT = (
    "https://github.com/ysmilda/brink-flair-modbus/edit/main/"
    "brink_flair_modbus/device_types.py"
)


def _unit_id_selector(default: int = DEFAULT_UNIT_ID) -> dict[Any, Any]:
    """Return the Modbus unit field shared by every connection form."""
    return {
        probatio.Required(CONF_UNIT_ID, default=default): probatio.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=1, max=247, step=1, mode=NumberSelectorMode.BOX
                )
            ),
            probatio.Coerce(int),
        )
    }


# Connection forms. Reconfiguration pre-fills them via
# ``add_suggested_values_to_schema``; setups fall back to the ``default`` values.
STEP_MODBUS_TCP = probatio.Schema(
    {
        probatio.Required(CONF_HOST): str,
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): probatio.All(
            probatio.Coerce(int), probatio.Range(min=1, max=65535)
        ),
        **_unit_id_selector(),
    }
)

STEP_SERIAL = probatio.Schema(
    {
        probatio.Required(CONF_DEVICE): SerialPortSelector(),
        **_unit_id_selector(),
        probatio.Required(CONF_BAUDRATE, default=str(DEFAULT_BAUDRATE)): probatio.All(
            SelectSelector(
                SelectSelectorConfig(
                    options=[str(baudrate) for baudrate in BAUDRATES],
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_BAUDRATE,
                )
            ),
            probatio.Coerce(int),
        ),
        probatio.Required(CONF_PARITY, default=DEFAULT_PARITY): SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=code, label=label)
                    for code, label in PARITY_LABELS.items()
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


STEP_MODEL = probatio.Schema(
    {
        probatio.Required(CONF_MODEL): SelectSelector(
            SelectSelectorConfig(
                options=[str(model) for model in SUPPORTED_MODELS],
                translation_key="model",
                mode=SelectSelectorMode.LIST,
            )
        )
    }
)


def _mapping_report_url(device_type: str) -> str:
    """Return a prefilled issue URL describing an unmapped device type."""
    params = {
        "title": f"Unmapped Brink Flair device type {device_type}",
        "body": (
            "Detected during setup:\n\n"
            f"- Device type (register 4004): `{device_type}`\n"
            "- Model: the one selected in the setup flow\n\n"
            "The mapping lives in "
            "`brink_flair_modbus/device_types.py`."
        ),
    }
    return f"{_GITHUB_ISSUES_NEW}?{urlencode(params)}"


class BrinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Brink Flair."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._data: dict[str, Any] = {}
        self._probe: BrinkProbe | None = None

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user choose the transport the unit is reached through."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["modbus_tcp", "serial"],
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure the integration."""
        return self.async_show_menu(
            step_id="reconfigure",
            menu_options=["modbus_tcp", "serial"],
        )

    async def async_step_modbus_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a Modbus TCP connection."""
        return await self._async_step_transport(
            "modbus_tcp", CONNECTION_TCP, STEP_MODBUS_TCP, user_input
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a Modbus serial (RTU) connection, incl. network serial proxies."""
        return await self._async_step_transport(
            "serial", CONNECTION_SERIAL, STEP_SERIAL, user_input
        )

    async def async_step_discovered(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the discovered unit."""
        assert self._probe is not None
        model = model_name_for_device_type(self._probe.device_type)
        if user_input is not None:
            return self.async_create_entry(title=model, data=self._data)
        return self.async_show_form(
            step_id="discovered",
            description_placeholders={
                "model": model,
                "device_type": str(self._probe.device_type),
            },
        )

    async def async_step_select_model(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the model of a unit whose device type is not mapped yet."""
        assert self._probe is not None
        if user_input is not None:
            model = int(user_input[CONF_MODEL])
            return self.async_create_entry(
                title=f"Brink Flair {model}", data={**self._data, CONF_MODEL: model}
            )
        device_type = str(self._probe.device_type)
        return self.async_show_form(
            step_id="select_model",
            data_schema=STEP_MODEL,
            description_placeholders={
                "device_type": device_type,
                "report_url": _mapping_report_url(device_type),
                "edit_url": _GITHUB_MAPPING_EDIT,
            },
        )

    async def _async_step_transport(
        self,
        step_id: str,
        connection_type: str,
        schema: probatio.Schema,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Show a connection form, probing the unit once it is submitted."""
        errors: dict[str, str] = {}
        reconfigure_entry = (
            self._get_reconfigure_entry() if self.source == SOURCE_RECONFIGURE else None
        )

        if user_input is not None:
            data = {CONF_TYPE: connection_type, **user_input}
            endpoint = "-".join(str(part) for part in params_from_data(data).endpoint)
            unique_id = f"{endpoint}_{data[CONF_UNIT_ID]}"
            await self.async_set_unique_id(unique_id, raise_on_progress=False)
            if reconfigure_entry is None:
                self._abort_if_unique_id_configured()
            elif (
                existing := self.hass.config_entries.async_entry_for_domain_unique_id(
                    self.handler, unique_id
                )
            ) is not None and existing is not reconfigure_entry:
                return self.async_abort(reason="already_configured")

            try:
                probe = await self._async_probe(data)
            except HomeAssistantError:
                errors["base"] = "link_settings_conflict"
            else:
                if probe is None:
                    errors["base"] = "cannot_connect"
                elif reconfigure_entry is not None:
                    # The line settings and unit address only change how Home
                    # Assistant talks to the unit; they are set on the unit itself.
                    if CONF_MODEL in reconfigure_entry.data:
                        data[CONF_MODEL] = reconfigure_entry.data[CONF_MODEL]
                    return self.async_update_reload_and_abort(
                        reconfigure_entry, data=data, unique_id=unique_id
                    )
                else:
                    self._data = data
                    self._probe = probe
                    if is_known_device_type(probe.device_type):
                        return await self.async_step_discovered()
                    return await self.async_step_select_model()

        suggested_values: Mapping[str, Any] | None = user_input
        if suggested_values is None and reconfigure_entry is not None:
            suggested_values = reconfigure_entry.data
        if suggested_values is not None and CONF_BAUDRATE in suggested_values:
            # The baud rate select works on strings, the entry stores an int.
            suggested_values = {
                **suggested_values,
                CONF_BAUDRATE: str(suggested_values[CONF_BAUDRATE]),
            }
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(schema, suggested_values),
            errors=errors,
        )

    async def _async_probe(self, data: Mapping[str, Any]) -> BrinkProbe | None:
        """Read the identity register through a temporary connection.

        Raises ``HomeAssistantError`` when the device is already in use with
        different link settings.
        """
        params = params_from_data(data)
        try:
            async with async_get_temporary_unit(
                self.hass, params, data[CONF_UNIT_ID]
            ) as unit:
                probe = await BrinkFlair.async_probe(unit)
        except ModbusError, OSError:
            return None
        # No code read means unreachable unit (wrong address, flaky link).
        if probe.device_type is None:
            return None
        return probe
