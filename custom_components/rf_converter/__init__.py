import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady, HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

from .const import DOMAIN, HEADERS, REQUESTURL, SECURITY_CODE, STORAGE_KEY, STORAGE_VERSION
from .rf_converter import CannotConnect, InvalidAccount, RemoteNotFound, RfConverterError, fetch_remote_data, rf_converter, validate_remote_data

_LOGGER = logging.getLogger(__name__)

SERVICE_RELOAD_REMOTE = 'reload_remote'
SERVICE_SEND_COMMAND = 'send_command'
SEND_COMMAND_SCHEMA = vol.Schema({
  vol.Required('remote'): cv.string,
  vol.Required('key'): cv.string,
})


def _cached_remotes(cache, account):
  if not isinstance(cache, dict) or cache.get('account') != account:
    return None
  try:
    validate_remote_data(cache.get('remotes'))
  except ValueError as err:
    _LOGGER.info('Ignoring invalid cached remote data: %s', err)
    return None
  return cache['remotes']


async def _async_load_remote_data(hass, store, rf, account, force_reload):
  if not force_reload:
    try:
      cache = await store.async_load()
    except HomeAssistantError as err:
      _LOGGER.info('Ignoring unreadable cached remote data: %s', err)
      cache = None
    remotes = _cached_remotes(cache, account)
    if remotes is not None:
      rf.remote_data = remotes
      return
  remotes = await hass.async_add_executor_job(fetch_remote_data, REQUESTURL, account, SECURITY_CODE, HEADERS)
  rf.remote_data = remotes
  await store.async_save({'account': account, 'remotes': remotes})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
  account = entry.data[CONF_USERNAME]
  store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
  rf = rf_converter()

  try:
    await _async_load_remote_data(hass, store, rf, account, False)
  except InvalidAccount as err:
    raise ConfigEntryError(f'Vendor server rejected account {account!r}: {err}') from err
  except CannotConnect as err:
    raise ConfigEntryNotReady(f'Cannot load remote data from vendor server: {err}') from err

  async def reload_remote(call: ServiceCall) -> None:
    try:
      await _async_load_remote_data(hass, store, rf, account, True)
    except RfConverterError as err:
      raise HomeAssistantError(f'Failed to reload remote data: {err}') from err

  async def send_command(call: ServiceCall) -> None:
    try:
      await hass.async_add_executor_job(rf.SendCommand, call.data['remote'], call.data['key'])
    except RemoteNotFound as err:
      raise ServiceValidationError(str(err)) from err
    except (OSError, ValueError) as err:
      raise HomeAssistantError(f'Failed to send command: {err}') from err

  hass.services.async_register(DOMAIN, SERVICE_RELOAD_REMOTE, reload_remote)
  hass.services.async_register(DOMAIN, SERVICE_SEND_COMMAND, send_command, schema = SEND_COMMAND_SCHEMA)

  return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
  hass.services.async_remove(DOMAIN, SERVICE_RELOAD_REMOTE)
  hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
  return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
  await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()
