import logging
import socket
import threading
import uuid

import requests

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
UDP_PORT = 26258
REQUIRED_FIELDS = ('ip', 'mac', 'type', 'project', 'frequency', 'id', 'key')


class RfConverterError(Exception):
  """Base error for this integration."""


class CannotConnect(RfConverterError):
  """Vendor server is unreachable or returned malformed data."""


class InvalidAccount(RfConverterError):
  """Vendor server returned an error for the account."""


class RemoteNotFound(RfConverterError):
  """Requested remote or key does not exist."""


def _mac_bytes(mac):
  value = bytes.fromhex(str(mac).replace(':', '').replace('-', ''))
  if len(value) != 6:
    raise ValueError(f'Invalid MAC address: {mac!r}')
  return value


def validate_remote_data(data):
  """Raise ValueError if data cannot be used to build packets."""
  if not isinstance(data, dict):
    raise ValueError('Remote data is not a dictionary')
  for name, remote in data.items():
    if not isinstance(remote, dict) or any(field not in remote for field in REQUIRED_FIELDS):
      raise ValueError(f'Remote {name!r} is missing required fields')
    if not isinstance(remote['ip'], str) or not isinstance(remote['key'], dict):
      raise ValueError(f'Remote {name!r} has invalid fields')
    try:
      _mac_bytes(remote['mac'])
      for field in ('type', 'project', 'frequency', 'id'):
        int(remote[field])
      for value in remote['key'].values():
        int(value)
    except (TypeError, ValueError) as err:
      raise ValueError(f'Remote {name!r} has invalid values: {err}') from err


def _post(url, data, headers):
  try:
    response = requests.post(url, data = data, headers = headers, timeout = REQUEST_TIMEOUT)
    response.raise_for_status()
    body = response.json()
  except (requests.RequestException, ValueError) as err:
    raise CannotConnect(str(err)) from err
  if not isinstance(body, dict) or 'result' not in body:
    raise CannotConnect(f'Unexpected response from {url}')
  return body


def fetch_remote_data(requesturlbase, account, security_code, headers):
  """Fetch all remotes of an account from the vendor server (blocking)."""
  devices = _post(requesturlbase + 'get_all_device_data.php', {'account': account, 'security_code': security_code}, headers)
  if devices['result'] != 0:
    raise InvalidAccount(f"Vendor server returned error code {devices['result']}")

  remote_data = {}
  try:
    for device in devices['message']:
      remotes = _post(requesturlbase + 'get_remote_controller.php', {'mac': device['mac'], 'security_code': security_code}, headers)
      if remotes['result'] != 0:
        _LOGGER.warning('Skipping converter %s: vendor server returned error code %s', device['mac'], remotes['result'])
        continue
      for remote in remotes['message']:
        name = remote['r_name']
        if name in remote_data:
          _LOGGER.warning('Duplicate remote name %r; only the last one is used', name)
        remote_data[name] = {
          'ip': device['ip'],
          'mac': device['mac'],
          'type': device['type'],
          'project': device['project'],
          'frequency': remote['frequency'],
          'id': remote['id'],
          'key': {key['k_name']: key['value'] for key in remote['key']},
        }
    validate_remote_data(remote_data)
  except (KeyError, TypeError, ValueError) as err:
    raise CannotConnect(f'Malformed remote data from vendor server: {err}') from err
  return remote_data


class rf_converter:
  def __init__(self):
    self.remote_data = {}
    self.sequence = 0
    self._lock = threading.Lock()


  def Checksum(self, crc_data):
    crc = 0
    for byte in crc_data:
      crc ^= byte
      for _ in range(8):
        crc = (crc >> 1) ^ 0x8c if crc & 1 else crc >> 1
    return crc


  def PacketBuilder(self, device_type, device_project, sender, receiver, remote_id, frequency, key_value, sequence):
    packet = bytearray()
    packet.append(0xFE)
    packet.append(2 if key_value is None else 1)
    packet.append(int(device_type) & 0xFF)
    packet.append(int(device_project) & 0xFF)
    packet.extend(_mac_bytes(sender))
    packet.extend(_mac_bytes(receiver))
    packet.extend(b'\x00' * 8)
    if key_value is None:
      packet.extend(b'\x21\x01')
      packet.extend(b'\x00\x00')
    else:
      packet.extend(b'\x02\x01')
      packet.extend(b'\x00\x0c')
      packet.extend((int(remote_id) & 0xFFFFFFFF).to_bytes(4, 'big'))
      packet.extend(b'\x00' * 4)
      packet.extend((int(frequency) & 0xFFFF).to_bytes(2, 'big'))
      packet.append(int(key_value) & 0xFF)
      packet.append(0)
    packet.append(sequence & 0xFF)
    packet.append(self.Checksum(packet) & 0xFF)
    packet.append(0xEF)
    return packet


  def CreatePacket(self, remote_name, key_name):
    remote = self.remote_data.get(remote_name)
    if remote is None:
      raise RemoteNotFound(f'Remote {remote_name!r} not found')
    if key_name not in remote['key']:
      raise RemoteNotFound(f'Key {key_name!r} not found in remote {remote_name!r}')
    with self._lock:
      sequence = self.sequence
      self.sequence = (self.sequence + 1) & 0xFF
    packet = self.PacketBuilder(
      remote['type'],
      remote['project'],
      f'{uuid.getnode():012x}',
      remote['mac'],
      remote['id'],
      remote['frequency'],
      remote['key'][key_name],
      sequence)
    return remote['ip'], packet


  def SendCommand(self, remote_name, key_name):
    ip, packet = self.CreatePacket(str(remote_name), str(key_name))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      sock.sendto(packet, (ip, UDP_PORT))
