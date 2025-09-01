DOMAIN = 'rf_converter'
CONF_FILE = '/config/custom_components/rf_converter/rf_data.json'
REQUESTURL = 'http://47.254.152.213/yetcloud_release/'
IOS_REQUEST = {
  'security_code': 'DSKWIJAKZXLQPSZMANXVTBFGYHPNVCRE',
  'headers': {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Connection': 'keep-alive',
    'Proxy-Connection': 'keep-alive',
    'Accept': '*/*',
    'User-Agent': 'Safemate/2.2.1 (iPhone; iOS 17.1.2; Scale/3.00)',
    'Accept-Language': 'ko-KR;q=1, en-KR;q=0.9, ja-KR;q=0.8'
  }
}
ANDROID_REQUEST = {
  'security_code': 'SDLKELS384DJ29Z49021DX30D92KS58S',
  'headers': {
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Connection': 'keep-alive',
    'Proxy-Connection': 'keep-alive',
    'Accept-Encoding': 'gzip',
    'User-Agent': 'okhttp/3.12.0'
  }
}
