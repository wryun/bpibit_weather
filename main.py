import sys
from ucontextlib import contextmanager
from graphics import Display
import graphics
import time
import ujson
from bom import BOM
import machine
from machine import deepsleep, lightsleep, Pin
import esp32
import micropython
import network
import ntptime


micropython.alloc_emergency_exception_buf(500)

@contextmanager
def wifi_connect(ap, password):
  sta_if = network.WLAN(network.STA_IF)

  try: 
    sta_if.active(True)
    if not sta_if.isconnected():
      sta_if.connect(ap, password)
      for _ in range(10):
        if sta_if.isconnected():
          yield sta_if
          break
        time.sleep(1)
      else:
        raise Exception('wifi fail')
  finally:
    sta_if.active(False)


def get_bom_data(geohash):
  bom = BOM(geohash)

  observations = bom.observations()['data']
  temp_now = observations['temp']
  rain_since_9am = observations['rain_since_9am']
  forecast = bom.forecasts_daily()['data'][0]
  # Stupid hack... should just check time > 4pm or something
  #forecast = tomorrow if today['now']['is_night'] else today
  # bizarrely, temp_now often holds the overnight min (?)
  temp_min = forecast['temp_min'] or forecast['now']['temp_now']
  temp_max = forecast['temp_max']
  icon = forecast['icon_descriptor']
  rain = forecast['rain']['amount']['max'] or forecast['rain']['amount']['min']
  return (temp_min, temp_max, icon, rain)


button_a = Pin(35, Pin.IN)
button_b = Pin(27, Pin.IN)


class WeatherDisplay:
  ICON = 0
  TEMP = 1
  RAIN = 2
  MAX = 3

  RAINBOW = 10

  def __init__(self, display, temp_min, temp_max, icon, rain):
    self.state = self.ICON
    self.display = display
    self.last_interaction = time.ticks_ms()
    self.temp_min = temp_min
    self.temp_max = temp_max
    self.icon = icon
    self.rain = rain
    button_a.irq(trigger=Pin.IRQ_FALLING, handler=self.button_press, wake=machine.SLEEP | machine.DEEPSLEEP)
    button_b.irq(trigger=Pin.IRQ_FALLING, handler=self.button_press, wake=machine.SLEEP | machine.DEEPSLEEP)
    esp32.wake_on_ext0(button_a, esp32.WAKEUP_ALL_LOW)
    esp32.wake_on_ext1((button_b,), esp32.WAKEUP_ALL_LOW)

  def button_press(self, pin):
    ticks = time.ticks_ms()
    # debounce
    if time.ticks_diff(ticks, self.last_interaction) < 100:
      return
    self.last_interaction = ticks
    if pin == button_a:
      if pin.value() == 0:
        if self.state >= self.MAX:
          self.state = self.ICON
        else:
          self.state = (self.state + 1) % self.MAX
    elif pin == button_b:
      if pin.value() == 0:
        self.state = self.RAINBOW

  def run(self):
    old_state = None
    while True:
      if self.state != old_state:
        if self.state == self.ICON:
          display.show_weather(self.icon)
        elif self.state == self.TEMP:
          display.scroll_text('T{}-{}'.format(self.temp_min, self.temp_max), graphics.RE)
        elif self.state == self.RAIN:
          display.scroll_text('R{}'.format(self.rain), graphics.BL)
        elif self.state == self.RAINBOW:
          display.show_rainbow()
        old_state = self.state

      if not display.is_scrolling() and self.state not in (self.ICON, self.RAINBOW):
        self.state = self.ICON
        continue

      li_diff = time.ticks_diff(time.ticks_ms(), self.last_interaction)
      if display.is_scrolling():
        time.sleep_ms(200)
      elif li_diff < 10000:
        lightsleep(10000 - li_diff + 1)
      else:
        print('Entering deep sleep...')
        # Figure out how to do a real deep sleep here...
        lightsleep()


if __name__ == '__main__':
  display = Display()

  print('Loading config...')
  with open('config.json') as f:
    config = ujson.loads(f.read())

  # TODO don't connect to wifi if the RTC is set
  # AND we have cached data.
  print('Connecting to wifi...')
  with display.scroll_status('wifi...'):
    wifi = wifi_connect(config['ap'], config['password'])

  with wifi:
    print('Setting time...')
    with display.scroll_status('time...'):
      ntptime.settime()
    print('Loading data from BOM...')
    with display.scroll_status('bom...'):
      data = get_bom_data(config['bom_geohash'])

  print('Configuring display...')
  wd = WeatherDisplay(display, *data)
  print('Running...')
  wd.run()
