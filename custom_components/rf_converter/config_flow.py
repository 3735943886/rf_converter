import voluptuous as vol
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers import config_validation as cv
from homeassistant import config_entries
from .const import DOMAIN

class ConfigFlow(config_entries.ConfigFlow, domain = DOMAIN):
  async def async_step_user(self, user_input):

    if self._async_current_entries() or self.hass.data.get(DOMAIN):
      return self.async_abort(reason = 'Only single instance allowed')

    if user_input:
      return self.async_create_entry(title = 'RF Converter Assistant - {}'.format(user_input[CONF_USERNAME]), data = user_input)

    return self.async_show_form(step_id = 'user', data_schema = vol.Schema({vol.Required(CONF_USERNAME): cv.string}))
