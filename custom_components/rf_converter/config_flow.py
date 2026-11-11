import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, HEADERS, REQUESTURL, SECURITY_CODE
from .rf_converter import CannotConnect, InvalidAccount, fetch_remote_data

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain = DOMAIN):
  VERSION = 1

  async def async_step_user(self, user_input = None):
    if self._async_current_entries():
      return self.async_abort(reason = 'single_instance_allowed')

    errors = {}
    if user_input is not None:
      account = user_input[CONF_USERNAME].strip()
      try:
        await self.hass.async_add_executor_job(fetch_remote_data, REQUESTURL, account, SECURITY_CODE, HEADERS)
      except InvalidAccount:
        errors['base'] = 'invalid_account'
      except CannotConnect:
        errors['base'] = 'cannot_connect'
      except Exception:  # pylint: disable=broad-except
        _LOGGER.exception('Unexpected error while validating account')
        errors['base'] = 'unknown'
      else:
        return self.async_create_entry(title = f'RF Converter - {account}', data = {CONF_USERNAME: account})

    return self.async_show_form(step_id = 'user', data_schema = vol.Schema({vol.Required(CONF_USERNAME): cv.string}), errors = errors)
