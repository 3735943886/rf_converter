import json
import logging

from .const import *
from .rf_converter import rf_converter
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.const import CONF_USERNAME
from homeassistant.config_entries import ConfigEntry

# DEFINE DOMAIN
_LOGGER = logging.getLogger(__name__)

# DEFINE CONSTANTS
SECURITY_CODE = ANDROID_REQUEST['security_code']
HEADERS = ANDROID_REQUEST['headers']

# DEFINE GLOBAL VARIABLES
ACCOUNT = None
RF = None


def InitConf(forcereload):
  global _LOGGER, CONF_FILE, ACCOUNT, REQUESTURL, SECURITY_CODE, HEADERS, RF
  try:
    if forcereload == True:
      raise Exception('Skip loading file')
    with open(CONF_FILE, 'r') as f:
      RF.remote_data = json.load(f)
    RF.CreatePacket(next(iter(RF.remote_data)), '')
  except:
    _LOGGER.info('Create new config file')
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
  global _LOGGER, ACCOUNT, DOMAIN, CONF_USERNAME, RF

  RF = rf_converter()

  @callback
  async def reload_remote(call: ServiceCall) -> None:
    await hass.async_add_executor_job(InitConf, True)

  @callback
  async def send_command(call: ServiceCall) -> None:
    await hass.async_add_executor_job(Command, call.data['remote'], call.data['key'])

  ACCOUNT = config.data[CONF_USERNAME]

  await hass.async_add_executor_job(InitConf, False)

  hass.services.async_register(DOMAIN, 'reload_remote', reload_remote)
  hass.services.async_register(DOMAIN, 'send_command', send_command)

  return True
