import sys
import math
import ctypes
from PIL import ImageFont, ImageDraw, Image
from dateutil.parser import parse
from zoneinfo import ZoneInfo
from configparser import SectionProxy
from typing import Optional, Union
from type_alias import Datetime, Fonts, Icons, DayNightIcons, WeatherWarning

SUPPORTED_EPD_MODELS = ['7.8', '10.3']


def draw_quantity(draw: ImageDraw.ImageDraw, mid_point: tuple[int, int], value: str, unit: str, fonts: Fonts, font: str = 'font_sm', font_unit: str = 'font_xs') -> None:
  (x, y) = mid_point
  draw.text((x - 3, y), value, font=fonts[font], fill=0, anchor='rs')
  draw.text((x + 3, y), unit, font=fonts[font_unit], fill=0, anchor='ls')


def check_python_version() -> None:
  major = sys.version_info[0]
  minor = sys.version_info[1]
  if major < 3 or minor < 7:
    raise Exception('Python 3.7 or newer required')

# Converts a 8-bit image into a packed 2-bit image which can be fed to EPD


def from_8bit_to_2bit(image: Image.Image) -> bytes:
  if (image.mode != 'L'):
    raise Exception('Image mode must be \'L\'')
  if (image.width % 4 != 0):
    raise Exception('Image width % 4 must be 0')

  image_bytes = image.tobytes()
  result = bytearray()
  for y in range(image.height):
    for x in range(image.width // 4):
      px0 = (image_bytes[y*image.width + x*4 + 0] & (0x3 << 6)) >> 0
      px1 = (image_bytes[y*image.width + x*4 + 1] & (0x3 << 6)) >> 2
      px2 = (image_bytes[y*image.width + x*4 + 2] & (0x3 << 6)) >> 4
      px3 = (image_bytes[y*image.width + x*4 + 3] & (0x3 << 6)) >> 6

      new_px = px0 | px1 | px2 | px3
      result.append(new_px)
  return bytes(result)


def get_epd_data(config: SectionProxy) -> tuple[Optional[ctypes.CDLL], tuple[int, int]]:
  if (is_supported_epd(config.get('EPD_MODEL'))):
    if (config.getboolean('FILE_OUTPUT')):
      return (None, (600, 448))
    else:
      return (ctypes.CDLL("lib/epd78.so"), (1872, 1404))
  else:
    raise Exception(f'Unsupported model: {config.get("EPD_MODEL")}')


def get_fonts(config: SectionProxy) -> Fonts:
  if (is_supported_epd(config.get('EPD_MODEL'))):
    font_mult = 2
  else:
    raise Exception(f'Unsupported model: {config.get("EPD_MODEL")}')

  return {
    'font_lg': ImageFont.truetype('fonts/regular.woff', font_mult * 42),
    'font_md': ImageFont.truetype('fonts/regular.woff', font_mult * 32),
    'font_sm': ImageFont.truetype('fonts/regular.woff', font_mult * 18),
    'font_sm_bold': ImageFont.truetype('fonts/bold.woff', font_mult * 18),
    'font_xs': ImageFont.truetype('fonts/regular.woff', font_mult * 14),
    'font_xxs': ImageFont.truetype('fonts/regular.woff', font_mult * 8),
    'font_misc_md': ImageFont.truetype('fonts/misc.woff', font_mult * 32)
  }


def draw_title(draw: ImageDraw.ImageDraw, title_font: ImageFont.FreeTypeFont, title: str, sub_title: Optional[str] = None, sub_title_font: Optional[ImageFont.FreeTypeFont] = None) -> None:
  size_width, size_height = draw.textsize(title, title_font)
  x_padding = 2
  y_padding = 1

  draw.rectangle(((0, 0), (size_width + x_padding, size_height + y_padding)), fill=0x00)
  draw.text(((size_width + x_padding)//2, (size_height + y_padding)//2), title, fill="white", font=title_font, anchor='mm')
  if (sub_title):
    if (not sub_title_font):
      sub_title_font = title_font
    sub_title_size_width, _ = draw.textsize(sub_title, sub_title_font)
    draw.rectangle(((size_width + x_padding, 0), (size_width + x_padding + sub_title_size_width + 40, size_height + y_padding)), fill=0xff, outline=0, width=4)
    draw.text(((size_width + x_padding + (sub_title_size_width + 40)//2), (size_height + y_padding)//2), sub_title, fill="black", font=sub_title_font, anchor='mm')


def get_icon_variant(is_daylight: bool, icon_set: DayNightIcons) -> Image.Image:
  if (not is_daylight and 'night' in icon_set):
    return icon_set['night']
  return icon_set['day']


def get_missing_weather_icon_icon(icon_index: Union[float, int], is_daylight: bool, images: Icons, fonts: Fonts) -> Image.Image:
  icon = images['misc']['background_day'].copy() if is_daylight else images['misc']['background_night'].copy()
  draw = ImageDraw.Draw(icon)
  text = "NaN" if math.isnan(icon_index) else str(icon_index)
  draw.text((icon.width//2, icon.height//2), text, font=fonts['font_md'], fill="black", anchor='mm')
  return icon


def get_cloud_cover_icon(cloud_cover: float, images: Icons, fonts: Fonts, config: SectionProxy) -> Image.Image:
  icon_index = math.nan if math.isnan(cloud_cover) else round(cloud_cover)
  if (not math.isnan(icon_index) and 0 <= icon_index <= 9):
    return images['misc'][f'cloud_cover_{icon_index}']
  icon = images['misc']['cloud_cover_0'].copy()
  draw = ImageDraw.Draw(icon)
  text = "NaN" if math.isnan(icon_index) else str(icon_index)
  draw.text((icon.width//2, icon.height//2), text, font=fonts['font_md'], fill="black", anchor='mm')
  return icon


def utc_datetime_string_to_local_datetime(date_string: str) -> Datetime:
  return parse(date_string).replace(tzinfo=ZoneInfo('UTC')).astimezone(tz=None)


def get_weather_warning_level(temperature: float, time: Datetime, config: SectionProxy) -> WeatherWarning:
  if temperature >= config.getint('EXTREME_HIGH_TEMPERATURE_WARNING_THRESHOLD'):
    return WeatherWarning.CRITICAL

  if temperature >= config.getint('HIGH_TEMPERATURE_WARNING_THRESHOLD'):
    return WeatherWarning.WARNING

  if temperature <= config.getint('EXTREME_LOW_TEMPERATURE_WARNING_THRESHOLD'):
    return WeatherWarning.CRITICAL

  if temperature <= config.getint('LOW_TEMPERATURE_WARNING_THRESHOLD'):
    return WeatherWarning.WARNING

  if temperature >= config.getint('TROPICAL_NIGHT_TEMPERATURE_WARNING_THRESHOLD') and (time.hour > 21 or time.hour < 8):
    return WeatherWarning.WARNING

  return WeatherWarning.NONE


def is_supported_epd(epd_model: str) -> bool:
  return epd_model in SUPPORTED_EPD_MODELS
