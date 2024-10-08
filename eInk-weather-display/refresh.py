import logging
from configparser import SectionProxy
from datetime import datetime, timedelta
from multiprocessing import Process
from timeit import default_timer as timer
from Electricity import get_El_price_andel, make_El_panel
from forecast_panel import get_forecasts_panel
from PIL import Image, ImageDraw
from type_alias import Fonts, Icons
from weather import get_forecast_data

PROCESS_TIMEOPUT = 240  # In seconds
SATURATION = 1

def refresh(panel_size: tuple[int, int], fonts: Fonts, images: Icons, config: SectionProxy, inky, init: bool) -> None:
    logger = logging.getLogger(__name__)
    logger.info('Refresh started')
    start_time = timer()
    now = datetime.today()

    # Fetch data
    start_fetch_time = timer()
    forecast_data = get_forecast_data(config, 7, 6, logger)
    elapsed_fetch_time = timer() - start_fetch_time
    El_data = None
    while El_data is None:
        El_data, new_data = get_El_price_andel(now.date()-timedelta(hours=2), now.date() + timedelta(days=2), region='east')


    # Draw individual panels
    logger.info('Drawing panels')
    start_draw_time = timer()
    (forecasts_panel, position) = get_forecasts_panel(forecast_data, images, fonts, config)
    El_panel = make_El_panel(El_data, (600, 248))

    # Paste the panels on the main image
    logger.info('Pasting panels')
    full_image = Image.new('RGB', (panel_size[0], panel_size[1]), (255, 255, 255))
    full_image.paste(forecasts_panel, (0, panel_size[1] - forecasts_panel.height))
    full_image.paste(El_panel, (0, 0))
    elapsed_draw_time = timer() - start_draw_time

    if (config.getboolean('DRAW_BORDERS')):
      border_color = (0,0,0)
      draw_width = 2
      draw = ImageDraw.Draw(full_image)
      draw.line([0, panel_size[1] - forecasts_panel.height, panel_size[0], panel_size[1] - forecasts_panel.height], fill=border_color, width=draw_width)
      
    if (config.getboolean('FILE_OUTPUT')):
      filename = config.get('OUTPUT_FILENAME')
      logger.info(f'Saving image to {filename}')
      full_image.save(filename)
      elapsed_refresh_time = 0
    else:
      filename = config.get('OUTPUT_FILENAME')
      logger.info(f'Saving image to {filename}')
      full_image.save(filename)

      logger.info(f'Sending image to EPD, {"full" if init else "partial"} refresh')
      if (config.getboolean('MIRROR_HORIZONTAL')):
        full_image = full_image.transpose(Image.FLIP_LEFT_RIGHT)
      image_bytes = full_image.rotate(0 if not config.getboolean('ROTATE_180') else 180, expand=True)
      if (inky):
        start_refresh_time = timer()
        try:
          inky.set_image(image_bytes, saturation=1)
          inky.set_border(inky.WHITE)
          p = Process(target=inky.show)
          p.start()
          p.join(PROCESS_TIMEOPUT)
          logger.debug(f'Exit code: {p.exitcode}')
          if (p.exitcode is None):
            logger.error('Timeout - An error occured during Inky.show')
          p.terminate()
        except Exception as e:
          logger.exception('Unexpected error: %s', str(e))
        finally:
          elapsed_refresh_time = timer() - start_refresh_time
      else:
        raise Exception('epd_so not defined')

    elapsed_time = timer() - start_time
    logger.info(f'Total time: {round(elapsed_time, 1)} s, refresh: {round(elapsed_refresh_time, 1)} s, API fetch: {round(elapsed_fetch_time, 1)} s, draw time: {round(elapsed_draw_time, 1)} s')
    logger.info('Refresh complete')
    return full_image
