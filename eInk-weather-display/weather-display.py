#!/usr/bin/python
# -*- coding:utf-8 -*-
import configparser
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import log
import logging
import utils
from icons import get_weather_images
import refresh
import ctypes
from typing import Optional
from type_alias import Icons, Fonts
from inky.inky_uc8159 import Inky, DESATURATED_PALETTE, SATURATED_PALETTE
import time

CONFIG_FILENAME = 'config.ini'


def main_loop(panel_size: tuple[int, int], fonts: Fonts, images: Icons, config: configparser.SectionProxy, epd_so: Optional[ctypes.CDLL]) -> None:
  logger = logging.getLogger(__name__)
  logger.info("main_loop() started")
  wakeup_time = datetime.datetime.now()
  #if ((wakeup_time.minute - 5) % config.getint('REFRESH_FULL_INTERVAL') == 0):
  refresh.refresh(panel_size, fonts, images, config, epd_so, True)
  #elif (wakeup_time.minute % config.getint('REFRESH_PARTIAL_INTERVAL') == 0):
  #  refresh.refresh(panel_size, fonts, images, config, epd_so, False)

def white_Inky(inky):
  for _ in range(2):
      for y in range(inky.height - 1):
          for x in range(inky.width - 1):
              inky.set_pixel(x, y, inky.WHITE)

      inky.show()
      time.sleep(30)

def main():
  log.setup()
  logger = logging.getLogger(__name__)
  logger.info("App starting")
  try:
    utils.check_python_version()
    logger.info(f'Reading config file "{CONFIG_FILENAME}"')
    with open(CONFIG_FILENAME) as f:
      config_parser = configparser.ConfigParser()
      config_parser.read_file(f)
      logger.info('Config: %s', config_parser.items('general'))
      config = config_parser['general']

      fonts = utils.get_fonts(config)
      images = get_weather_images()

      #logger.info('Import epd control library')
      #(epd_so, panel_size) = utils.get_epd_data(config)

      inky = Inky()

      white_Inky(inky)

      panel_size = inky.resolution

      logger.info("Initial refresh")
      refresh.refresh(panel_size, fonts, images, config, inky, True)  # Once in the beginning

      #time.sleep(10)
      #refresh.refresh(panel_size, fonts, images, config, inky, True)  # Once in the beginning

      logger.info('Starting scheduler')
      scheduler = BlockingScheduler()
      scheduler.add_job(lambda: main_loop(panel_size, fonts, images, config, inky), 'cron', hour='17', minute = '01')
      scheduler.start()

  except FileNotFoundError as e:
    logger.exception(f'Error opening file "{CONFIG_FILENAME}": %s', str(e))

  except KeyboardInterrupt:
    logger.warning("KeyboardInterrupt error")

  except Exception as e:
    logger.exception('Unexpected error: %s', str(e))


if __name__ == "__main__":
  main()
