import json
import logging

import requests

from .const import *
from .rf_converter import rf_converter
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.const import CONF_USERNAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

# DEFINE DOMAIN
_LOGGER = logging.getLogger(__name__)

# DEFINE CONSTANTS
SECURITY_CODE = ANDROID_REQUEST['security_code']
HEADERS = ANDROID_REQUEST['headers']

# DEFINE GLOBAL VARIABLES
ACCOUNT = None
RF = None
CONF_FILE = None


def InitConf(forcereload):
  global _LOGGER, CONF_FILE, ACCOUNT, REQUESTURL, SECURITY_CODE, HEADERS, RF
  if not forcereload:
    try:
      with open(CONF_FILE, 'r') as f:
        RF.remote_data = json.load(f)
      RF.CreatePacket(next(iter(RF.remote_data)), '')
      return
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as e:
      _LOGGER.info('No usable local cache (%s), fetching from vendor', e)
  result = RF.GetRemote(REQUESTURL, ACCOUNT, SECURITY_CODE, HEADERS)
  if result == 0:
    with open(CONF_FILE, 'w') as f:
      json.dump(RF.remote_data, f)
  else:
    _LOGGER.warning('Error code: {}'.format(result))


def Command(remote, key):
  global _LOGGER, RF

  result = RF.SendCommand(remote, key)
  if result == False:
    _LOGGER.warning('Remote [{}]/[{}] not found'.format(remote, key))


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
  global _LOGGER, ACCOUNT, DOMAIN, CONF_USERNAME, CONF_FILE, RF

  RF = rf_converter()
  CONF_FILE = hass.config.path(CACHE_FILE_NAME)

  @callback
  async def reload_remote(call: ServiceCall) -> None:
    await hass.async_add_executor_job(InitConf, True)

  @callback
  async def send_command(call: ServiceCall) -> None:
    await hass.async_add_executor_job(Command, call.data['remote'], call.data['key'])

  ACCOUNT = config.data[CONF_USERNAME]

  try:
    await hass.async_add_executor_job(InitConf, False)
  except (requests.RequestException, ValueError) as err:
    raise ConfigEntryNotReady(f'Cannot load remote data from vendor server: {err}') from err

  hass.services.async_register(DOMAIN, 'reload_remote', reload_remote)
  hass.services.async_register(DOMAIN, 'send_command', send_command)

  return True


async def async_unload_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
  hass.services.async_remove(DOMAIN, 'reload_remote')
  hass.services.async_remove(DOMAIN, 'send_command')
  return True
