import uos
import ujson
import utime
import urequests


class BOM:
  def __init__(self, geohash):
    self.geohash = geohash

  def _get(self, thing):
    key = 'cache-{}-{}.json'.format(self.geohash, thing).replace('/', '__')
    try:
      mtime = uos.stat(key)[8]
      if utime.time() - mtime < 60 * 60:
        print('using cache')
        with open(key) as f:
          return ujson.loads(f.read())
      else:
        print('cache out of date')
    except:
      print('error accessing cache')

    url = 'https://api.weather.bom.gov.au/v1/locations/{}/{}'.format(self.geohash, thing)
    r = urequests.get(url)
    try:
      with open(key, 'w') as f:
        f.write(r.content)
      return r.json()
    finally:
      r.close()

  def forecasts_3_hourly(self):
    return self._get('forecasts/3-hourly')

  def __getattr__(self, name):
    return lambda: self._get(name.replace('_', '/'))