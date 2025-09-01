import requests
import socket
import uuid


class rf_converter:
  remote_data = {}
  sequence = 0


  def __init__(self):
    remote_data = {}
    sequence = 0


  def GetRemote(self, requesturlbase, account, security_code, headers):
    device_response = requests.post(requesturlbase + 'get_all_device_data.php', data = {'account': account, 'security_code': security_code }, headers = headers)
    device_response.raise_for_status()
    devices = device_response.json()
    self.remote_data = {}
    if devices['result'] == 0:
      for i in range(len(devices['message'])):
        remote_response = requests.post(requesturlbase + 'get_remote_controller.php', data = {'mac': devices['message'][i]['mac'], 'security_code': security_code}, headers = headers)
        remote_response.raise_for_status()
        remotes = remote_response.json()
        if remotes['result'] == 0:
          for j in range(len(remotes['message'])):
            self.remote_data[remotes['message'][j]['r_name']] = {}
            self.remote_data[remotes['message'][j]['r_name']]['ip'] = devices['message'][i]['ip']
            self.remote_data[remotes['message'][j]['r_name']]['mac'] = devices['message'][i]['mac']
            self.remote_data[remotes['message'][j]['r_name']]['type'] = devices['message'][i]['type']
            self.remote_data[remotes['message'][j]['r_name']]['project'] = devices['message'][i]['project']
            self.remote_data[remotes['message'][j]['r_name']]['frequency'] = remotes['message'][j]['frequency']
            self.remote_data[remotes['message'][j]['r_name']]['id'] = remotes['message'][j]['id']
            self.remote_data[remotes['message'][j]['r_name']]['key'] = {}
            for k in range(len(remotes['message'][j]['key'])):
              self.remote_data[remotes['message'][j]['r_name']]['key'][remotes['message'][j]['key'][k]['k_name']] = remotes['message'][j]['key'][k]['value']
    return devices['result']


  def Checksum(self, crc_data, length):
    crc = 0
    for i in range(length):
      crc ^= crc_data[i]
      for j in range(8):
        crc = (crc >> 1) if (crc & 1) <= 0 else (crc >> 1) ^ 0x8c
    return crc


  def PacketBuilder(self, device_type, device_project, sender, receiver, remote_id, frequency, key_value, sequence):
    packet = bytearray()
    packet.append(0xFE)
    if key_value == None:
      packet.append(2)
    else:
      packet.append(1)
    packet.append(int(device_type) & 0xFF)
    packet.append(int(device_project) & 0xFF)
    packet.extend(bytes.fromhex(sender.replace(':', '')))
    packet.extend(bytes.fromhex(receiver.replace(':', '')))
    packet.extend(b'\x00' * 8)
    if key_value == None:
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
    packet.append(self.Checksum(packet, 29 if key_value == None else 41) & 0xFF)
    packet.append(0xEF)
    return packet


  def CreatePacket(self, remote, key):
    if remote in self.remote_data.keys():
      if key in self.remote_data[remote]['key'].keys() or key == '':
        packet = self.PacketBuilder(
          self.remote_data[remote]['type'],
          self.remote_data[remote]['project'],
          f'{uuid.getnode():x}',
          self.remote_data[remote]['mac'],
          self.remote_data[remote]['id'],
          self.remote_data[remote]['frequency'],
          None if key == '' else self.remote_data[remote]['key'][key],
          self.sequence)
        self.sequence += 1
        self.sequence &= 0xff
        return self.remote_data[remote]['ip'], packet
    return None, None


  def SendCommand(self, remote, key):
    ip, p = self.CreatePacket(str(remote), str(key))
    if ip != None and p != None:
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      sock.sendto(p, (ip, 26258))
      sock.close()
      return True
    return False
