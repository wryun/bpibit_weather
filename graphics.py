from ucontextlib import contextmanager
from neopixel import NeoPixel
from machine import Pin
from time import sleep_ms
import _thread
import sys


GY = (1, 1, 1)
__ = (0, 0, 0)
WH = (7, 7, 7)
RE = (10, 0, 0)
GR = (0, 10, 0)
BL = (0, 0, 10)
YE = (8, 8, 0)
PU = (8, 0, 8)
CY = (0, 8, 8)
OR = (8, 4, 0)
DO = (5, 2, 0)
BG = (1, 1, 3)


class Display:
  def __init__(self):
    self.lock = _thread.allocate_lock()
    self.np = NeoPixel(Pin(4), 25)
    self.clear()

  def is_scrolling(self):
    with self.lock:
      return bool(self.scrolling)

  def clear(self):
    with self.lock:
      self.scrolling = None
      self.np.fill((0, 0, 0))

  def set(self, x, y, val):
    with self.lock:
      self.scrolling = None
      self.np[y + (4 - x) * 5] = val

  def show_image(self, img):
    for (i, val) in enumerate(img):
      self.set(i % 5, i // 5, val)
    self.flush()

  def show_rainbow(self):
    self.show_image(RAINBOW)

  def show_weather(self, name):
    self.show_image(BOM_ICONS.get(name, DEFAULT_BOM_ICON))

  def scroll_text(self, text, colour=RE, delay=150, times=1):
    with self.lock:
      # since start_new_thread isn't actually Python compatible,
      # we can't take the thread identifier from the return value
      # and have to get it inside the thread.
      # But we need this here to mark us as 'scrolling' ASAP.
      self.scrolling = 'fake'
      _thread.start_new_thread(self._scroll_text, [text, colour, delay, times])

  @contextmanager
  def scroll_status(self, text, colour=RE, delay=150, times=1):
    self.scroll_text(text, colour, delay)
    yield self
    self.clear()

  def _scroll_text(self, text, colour, delay, times):
    with self.lock:
      self.scrolling = _thread.get_ident()

    try:
      for _ in range(times):
        self._scroll_text_inner(text, colour, delay)
    finally:
      with self.lock:
        if self.scrolling == _thread.get_ident():
          self.scrolling = None

  def get_image_for_char(self, c, colour):
    return [colour if v else [0, 0, 0] for v in CHAR_DATA.get(c, CHAR_DATA['?'])] + [__] * 5

  def _display_buf(self, buf):
    with self.lock:
      if self.scrolling != _thread.get_ident():
        return False

    for i, val in enumerate(buf):
      self.np[i] = val
    self.np.write()
    return True

  def _scroll_text_inner(self, text, colour, delay):
    buf = self.get_image_for_char(text[0], colour)[:25]
    if not self._display_buf(buf):
      return
    sleep_ms(500)

    for c in text[1:] + ' ':
      image = self.get_image_for_char(c, colour)

      for i in range(6):
        buf[5:] = buf[:20]
        buf[0:5] = image[25 - (i * 5):30 - (i * 5)]
        if not self._display_buf(buf):
          return

        sleep_ms(delay)

  def flush(self):
    with self.lock:
      self.scrolling = None
      self.np.write()
      self.np.fill((0, 0, 0))


class Gauge:
  """
  g = Gauge(np, 0, 5, YELLOW, RED)
  g = Gauge(np, 0, 5, GREEN, BLUE)
  g = Gauge(np, 5, 5, BLUE, GREEN)

  x = 0
  while x <= 1.0:
    g.set(x)
    np.write()
    sleep(0.04)
    x += 0.01
  """

  def __init__(self, display, run, empty_colour, full_colour):
    self.display = display
    self.start_pixel = start_pixel
    self.run = run
    self.fc = full_colour
    self.ec = empty_colour

  def set(self, f):
    for i in range(0, self.run):
      if i < self.run * f - 1:
        pixel_colour = self.fc
      elif i < self.run * f:
        perc = self.run * f - i
        pixel_colour = (
          int(self.ec[0] + (self.fc[0] - self.ec[0]) * perc),
          int(self.ec[1] + (self.fc[1] - self.ec[1]) * perc),
          int(self.ec[2] + (self.fc[2] - self.ec[2]) * perc),
        )
      else:
        pixel_colour = (0, 0, 0)

      self.display.set(i, 0, pixel_colour)


CHAR_DATA = {
    '!': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    '"': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0],
    '#': [0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0],
    '$': [0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    '%': [1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1],
    '&': [0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    "'": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    '(': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
    '@': [0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0],
    ')': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    '*': [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0],
    '+': [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    ',': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    '-': [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    '.': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    '/': [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
    '0': [0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0],
    '1': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0],
    '2': [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1],
    '3': [0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0],
    '4': [0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0],
    '5': [1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1],
    '6': [0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0],
    '7': [1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1],
    '8': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    '9': [0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0],
    ':': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0],
    ';': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    '<': [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    '=': [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0],
    '>': [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    '?': [0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    'A': [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1],
    'B': [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1],
    'C': [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0],
    'D': [0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1],
    'E': [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1],
    'F': [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1],
    'G': [0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0],
    'H': [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1],
    'I': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1],
    'J': [1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0],
    'K': [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1],
    'L': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
    'M': [1, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1],
    'N': [1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1],
    'O': [0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0],
    'P': [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1],
    'Q': [0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0],
    'R': [0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1],
    'S': [0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1],
    'T': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    'U': [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0],
    'V': [1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0],
    'W': [1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1],
    'X': [0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 1],
    'Y': [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    'Z': [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1],
    '[': [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
    "\\": [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
    ']': [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    '^': [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    '_': [0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    '`': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'a': [0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0],
    'b': [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1],
    'c': [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0],
    'd': [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0],
    'e': [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0],
    'f': [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 0],
    'g': [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0],
    'h': [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1],
    'i': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0],
    'j': [0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    'k': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1],
    'l': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
    'm': [0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1],
    'n': [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1],
    'o': [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0],
    'p': [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1],
    'q': [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0],
    'r': [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1],
    's': [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1],
    't': [0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
    'u': [0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0],
    'v': [0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0],
    'w': [0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1],
    'x': [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1],
    'y': [0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1],
    'z': [0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1],
    '{': [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    '|': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
    '}': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1],
    '~': [0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    ' ': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
}

BOM_ICONS = {
  'sunny': (
    YE, __, YE, __, YE,
    __, YE, OR, YE, __,
    YE, OR, DO, OR, YE,
    __, YE, OR, YE, __,
    YE, __, YE, __, YE,
  ),
  'clear': (
    __, __, __, __, __,
    __, YE, __, YE, __,
    __, __, OR, __, __,
    __, YE, __, YE, __,
    __, __, __, __, __,
  ),
  'partly_cloudy': (
    YE, __, YE, __, __,
    __, YE, OR, GY, __,
    YE, OR, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, GY, GY, GY, __,
  ),
  'cloudy': ( # Cloudy
    YE, __, YE, __, __,
    __, GY, GY, GY, __,
    GY, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, GY, GY, GY, __,
  ),
  'mostly_sunny': (
    YE, __, YE, __, YE,
    __, YE, OR, YE, __,
    YE, OR, DO, OR, YE,
    __, YE, OR, GY, GY,
    YE, __, GY, GY, GY,
  ),
  'haze': (
    __, __, __, __, __,
    GY, GY, YE, GY, GY,
    __, YE, OR, YE, __,
    GY, GY, YE, GY, GY,
    __, __, __, __, __,
  ),
  'hazy': (
    __, __, __, __, __,
    GY, GY, YE, GY, GY,
    __, YE, OR, YE, __,
    GY, GY, YE, GY, GY,
    __, __, __, __, __,
  ),
  'light_rain': ( # Light rain
    __, GY, GY, GY, __,
    GY, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, BL, __, BL, __,
    BL, __, BL, __ , __,
  ),
  'wind': (
    __, __, __, BG, __,
    __, __, __, __, BG,
    BG, BG, BG, BG, __,
    __, __, __, __, BG,
    __, __, __, BG, __,
  ),
  'windy': (
    __, __, __, BG, __,
    __, __, __, __, BG,
    BG, BG, BG, BG, __,
    __, __, __, __, BG,
    __, __, __, BG, __,
  ),
  'shower': ( # Shower
    YE, __, YE, __, __,
    __, YE, OR, GY, __,
    YE, OR, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, BL, __, BL, __,
  ),
  'showers': ( # Shower
    YE, __, YE, __, __,
    __, YE, OR, GY, __,
    YE, OR, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, BL, __, BL, __,
  ),
  'rain': ( # Rain
    __, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, BL, __, BL, __,
    BL, __, BL, __, BL,
    BL, __, BL, __, BL,
  ),
  'storm': (
    __, GY, GY, GY, __,
    GY, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, __, YE, YE, __,
    __, YE, YE, __, __,
  ),
  'storms': (
    __, GY, GY, GY, __,
    GY, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, __, YE, YE, __,
    __, YE, YE, __, __,
  ),
  'light_shower': (
    __, GY, GY, GY, __,
    GY, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, BL, __, BL, __,
    __, BL, __, BL, __,
  ),
  'light_showers': (
    __, GY, GY, GY, __,
    GY, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, BL, __, BL, __,
    __, BL, __, BL, __,
  ),
  'heavy_shower': ( # Heavy Shower
    __, GY, GY, GY, __,
    GY, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, BL, BL, BL, __,
    BL, __, BL, __, BL,
  ),
  'heavy_showers': ( # Heavy Shower
    __, GY, GY, GY, __,
    GY, GY, GY, GY, GY,
    GY, GY, GY, GY, GY,
    __, BL, BL, BL, __,
    BL, __, BL, __, BL,
  ),
}

DEFAULT_BOM_ICON = (
  __, GY, GY, GY, __,
  __, __, __, __, GY,
  __, __, GY, GY, __,
  __, __, __, __, __,
  __, __, GY, __, __,
)

RAINBOW = (
  __, __, __, __, YE,
  BL, GR, YE, OR, RE,
  PU, __, __, BL, GY,
  __, __, __, __, __,
  __, __, __, __, __,
)
