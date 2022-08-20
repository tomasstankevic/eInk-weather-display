import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from datetime import datetime, timedelta, date
from configparser import SectionProxy
from logging import Logger
import logging
import io
from PIL import Image
from typing import Mapping, Optional, Dict, List, Tuple

link = 'https://andelenergi.dk/?obexport_format=csv&obexport_start=2022-08-10&obexport_end=2022-08-18&obexport_region=east'

region = 'east'
transport_overhead = 1.59 #DKK

logger = logging.getLogger(__name__)
logger.info('Getting price data')

def _make_El_price_URL(start_date: date, end_date: date, region: str) -> str:
    url = 'https://andelenergi.dk/?obexport_format=csv&obexport_start='+str(start_date)+'&obexport_end='+str(end_date)+'&obexport_region='+region
    return url

def get_El_price(start_date, end_date, region):
    url = _make_El_price_URL(start_date, end_date, region)
    try:
        el_data = pd.read_csv(url, decimal=',')
    except Exception as e:
        logger.exception('Error getting price data from: %s', url)
        return None
    el_data.Date = pd.to_datetime(el_data.Date)#.dt.date
    el_data2 = el_data.set_index('Date')
    el_data2.columns = pd.to_datetime(el_data2.columns)
    el_data2_st = el_data2.stack()
    dates = el_data2_st.index.get_level_values(0) 
    times = el_data2_st.index.get_level_values(1) 
    times.to_pydatetime()

    df = pd.DataFrame(columns= ['Date', 'Time', 'Datetime','Price'])
    df['Date'] = dates.date.astype(str)
    df['Time'] = times.time.astype(str)
    df['Hour'] = times.hour.astype(int)
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' +df['Time'])
    df['Price'] = el_data2_st.values+transport_overhead
    df['Weekday'] = df['Datetime'].dt.day_name()
    df['Weekday'] = df['Weekday'].str.slice(0, 3)

    df_future = df[df['Datetime']>str(datetime.now())]
    return df_future

def make_El_panel(El_data, panel_size, colors=None, fonts=None):
    buf = io.BytesIO()
    vsize = panel_size[1]
    hsize = panel_size[0]
    dpi = 80
    factor = 3
    fig = plt.figure(figsize=((hsize/dpi*factor,vsize/dpi*factor)), frameon=False)
    ax = plt.subplot()
    vals = El_data.Price
    hours = El_data.Hour
    colors = ["green" if i < 3 else "red" for i in vals]
    barplot = ax.bar(El_data.Hour, El_data.Price, 0.3, color=colors)
    ax.set_xlim([min(El_data.Hour)-0.5, max(El_data.Hour)+0.5])
    ax.set_xticks(hours)
    ax.grid(axis='y', linewidth=1, color='k')
    for axis in ['top','bottom','left','right']:
        ax.spines[axis].set_linewidth(3)

    # increase tick width
    ax.tick_params(width=3)

    for tick in ax.get_xticklabels():
        tick.set_fontname('barlow-condensed')
        tick.set_fontsize(14*factor)
    for tick in ax.get_xticklabels()[1::2]:
        tick.set_visible(False)
    for tick in ax.get_yticklabels():
        tick.set_fontname('barlow-condensed')
        tick.set_fontsize(14*factor)

    buf = io.BytesIO()

    fig.savefig(buf, format="png", dpi=dpi,bbox_inches='tight')
    fig.savefig('elpanel_plot.png', format="png", dpi=dpi)
    buf.seek(0)
    plot_image = Image.open(buf).convert("RGB")
    newsize = (hsize, vsize)
    im1 = plot_image.resize(newsize)
    #display(im1)
    buf.close()
    return im1



    #ax = El_data.plot.bar(x='Hour', y='Price', rot=0, figsize=(panel_size[0]/dpi,panel_size[1]/dpi))
    #fig = ax.get_figure()
    #fig.savefig(buf, format="png", dpi=dpi)
    #fig.savefig('elpanel_plot.png', format="png", dpi=dpi)
    #buf.seek(0)

    #plot_image = Image.open(buf).convert("RGB")
    #image = Image.new("RGB", (panel_size[0], panel_size[1]), (255, 255, 255))
    #image.paste(plot_image, (0, 0))
    #image.save('elpanel_image.png')
    #return plot_image



