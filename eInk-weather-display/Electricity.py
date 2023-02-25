import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from datetime import datetime, timedelta, date
from configparser import SectionProxy
from logging import Logger
import logging
import io
import requests
import json
from PIL import Image
from typing import Mapping, Optional, Dict, List, Tuple
import matplotlib.font_manager as fm
from PIL.Image import Dither
import matplotlib as mpl

BLACK = 0
WHITE = 1
GREEN = 2
BLUE = 3
RED = 4
YELLOW = 5
ORANGE = 6
CLEAN = 7

PALETTE = {
    'black':tuple(np.array([57, 48, 57])/255),
    'white':tuple(np.array([255, 255, 255])/255),
    'green':tuple(np.array([58, 91, 70])/255),
    'blue':tuple(np.array([61, 59, 94])/255),
    'red':tuple(np.array([156, 72, 75])/255),
    'yellow':tuple(np.array([208, 190, 71])/255),
    'orange':tuple(np.array([177, 106, 73])/255),
    'clean':tuple(np.array([255, 255, 255])/255)
}

link = 'https://andelenergi.dk/?obexport_format=csv&obexport_start=2022-08-10&obexport_end=2022-08-18&obexport_region=east'

region = 'east'
transport_tarrifs = [0.79, 2.06, 0.79, 0.37]  # Day, Evening, Late Evening, Night

logger = logging.getLogger(__name__)
logger.info('Getting price data')

def _make_El_price_URL(start_date: date, end_date: date, region: str) -> str:
    endpoint = "https://api.energidataservice.dk/dataset/"
    dataset = "Elspotprices?"
    parameters = "filter={\"PriceArea\":\"DK2\"}&start="+str(start_date)+"&end="+str(end_date)
    url = endpoint + dataset + parameters
    return url

def get_El_price(start_date, end_date, region):
    import requests
    import json

    url = _make_El_price_URL(start_date.strftime("%Y-%m-%dT%H:%M"), end_date.strftime("%Y-%m-%dT%H:%M"), region)

    print(url)

    NP_spotprices_json = requests.get(url).json()

    NP_spotprices = pd.DataFrame.from_dict(NP_spotprices_json['records'])

    NP_spotprices = NP_spotprices.sort_values(by='HourUTC', ascending=True)

    #print(NP_spotprices)
    NP_spotprices['Andel_DKK'] = NP_spotprices['SpotPriceDKK']/1000.*1.4+0.02
    NP_spotprices['Datetime_UTC'] = pd.to_datetime(NP_spotprices['HourUTC'])
    NP_spotprices['Datetime_DK'] = pd.to_datetime(NP_spotprices['HourDK'])
    NP_spotprices['HourDK'] = pd.to_datetime(NP_spotprices['HourDK'])
    NP_spotprices = NP_spotprices.set_index('Datetime_UTC')
    
    df = pd.DataFrame({
        'Date': NP_spotprices['Datetime_DK'].dt.date.astype(str),
        'Time': NP_spotprices['Datetime_DK'].dt.time.astype(str),
        'Hour': NP_spotprices['Datetime_DK'].dt.hour.astype(str),
        'Datetime': NP_spotprices['Datetime_DK'],
        'Price_el': NP_spotprices['Andel_DKK'],
        'Weekday': NP_spotprices['HourDK'].dt.day_name()
        })

    df['Weekday'] = df['Weekday'].str.slice(0, 3)
    df['WeekHour'] = df['Weekday'] + df['Hour']

    transport_hour_ranges = [
        (df["Hour"].astype(int)>=6) & (df["Hour"].astype(int)<16),   # Day
        (df["Hour"].astype(int)>=16) & (df["Hour"].astype(int)<21),  # Evening
        (df["Hour"].astype(int)>=21) & (df["Hour"].astype(int)<24),  # Late Evening
        (df["Hour"].astype(int)>=0) & (df["Hour"].astype(int)<6)    # Night
    ]
    df['Tariff'] = np.select(transport_hour_ranges, transport_tarrifs)
    df['Price'] = df['Price_el'] + df['Tariff']


    df_future = df[df['Datetime']>str(datetime.now()+timedelta(hours=-1))]
    df_future.reset_index(drop=True,inplace=True)
    new_data = False
    tomorrow = str(datetime.now().date()+timedelta(days=1)) 
    if tomorrow in df_future.Date.to_string():
        new_data = True
        logger.info('Prices for tomorrow available')
    else:
        logger.info('No price data for tomorrow')
    return df_future, new_data


def get_El_price_andel(start_date, end_date, region):
    url = _make_El_price_URL(start_date, end_date, region)
    try:
        el_data = pd.read_csv(url, decimal=',')
    except Exception as e:
        logger.exception('Error getting price data from: %s', url)
        return None, None
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
    df['Hour'] = times.hour.astype(str)
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' +df['Time'])
    df['Price_el'] = el_data2_st.values
    df['Weekday'] = df['Datetime'].dt.day_name()
    df['Weekday'] = df['Weekday'].str.slice(0, 3)
    df['WeekHour'] = df['Weekday']+df['Hour']
    print(df["Hour"].astype(int))
    transport_hour_ranges = [
        (df["Hour"].astype(int)>=6) & (df["Hour"].astype(int)<16),   # Day
        (df["Hour"].astype(int)>=16) & (df["Hour"].astype(int)<21),  # Evening
        (df["Hour"].astype(int)>=21) & (df["Hour"].astype(int)<24),  # Late Evening
        (df["Hour"].astype(int)>=0) & (df["Hour"].astype(int)<6)    # Night
    ]
    df['Tariff'] = np.select(transport_hour_ranges, transport_tarrifs)
    df['Price'] = df['Price_el'] + df['Tariff']


    df_future = df[df['Datetime']>str(datetime.now()+timedelta(hours=-1))]
    df_future.reset_index(drop=True,inplace=True)
    new_data = False
    tomorrow = str(datetime.now().date()+timedelta(days=1)) 
    if tomorrow in df_future.Date.to_string():
        new_data = True
        logger.info('Prices for tomorrow available')
    else:
        logger.info('No price data for tomorrow')
    return df_future, new_data

def make_El_panel(El_data, panel_size, colors=None, fonts=None):
    buf = io.BytesIO()
    vsize = panel_size[1]
    hsize = panel_size[0]
    dpi = 80
    factor = 6
    linew = factor
    mpl.rcParams['hatch.linewidth'] = linew
    fontsize = 27
    fig = plt.figure(figsize=((hsize/dpi*factor,vsize/dpi*factor)), frameon=False)
    ax = plt.subplot()
    font = 'barlow-condensed-regular.ttf'
    font_path = 'fonts/barlow-condensed.regular.ttf'  # the location of the font file
    font = fm.FontProperties(fname=font_path)  # get the font based on the font_path
    vals = El_data.Price
    hours = El_data.WeekHour

    El_data['Color'] = ['red' for i in vals]
    El_data['Hatch'] = ['red' for i in vals]

    #El_data.Color[El_data.Price < El_data.Price.quantile(.4)] = 'orange'
    #El_data.Hatch[El_data.Price < El_data.Price.quantile(.4)] = 'orange'
    
    El_data.Color[El_data.Price < 5] = 'orange'
    El_data.Hatch[El_data.Price < 5] = 'orange'

    El_data.Color[El_data.Price < 4] = 'yellow'
    El_data.Hatch[El_data.Price < 4] = 'orange'

    El_data.Color[El_data.Price < 3] = 'yellow'
    El_data.Hatch[El_data.Price < 3] = 'green'

    El_data.Color[El_data.Price < 2] = 'green'
    El_data.Hatch[El_data.Price < 2] = 'green'

    El_data['RGB'] = [PALETTE[col] for col in El_data['Color']]
    El_data['HatchRGB'] = [PALETTE[col] for col in El_data['Hatch']]

    barplot = ax.bar(El_data.WeekHour, El_data.Price, 0.4, color=El_data.RGB, edgecolor=El_data.HatchRGB, hatch='/', linewidth = linew)

    ax.set_xlim([-1, len(vals)])
    ax.set_ylim([0, max(max(ax.get_yticks()), max(vals))])
    ax.set_xticks(hours)
    ax.set_xticklabels(El_data.Hour)
    ax.grid(axis='y', linewidth=linew, color=PALETTE['black'] )
    for axis in ['top','bottom','left','right']:
        ax.spines[axis].set_linewidth(linew)

    # increase tick width
    ax.tick_params(width=linew,length=linew*4)

    for i, tick in enumerate(ax.get_xticklabels()):
        tick.set_fontproperties(font)
        tick.set_fontsize(fontsize*factor)
        if tick.get_text() == '0' or tick.get_text() == '1':
            tick.set_fontweight(weight="bold")
    for tick in ax.get_xticklabels()[1::2]:
        tick.set_visible(False)
    for tick in ax.get_yticklabels()[1::2]:
        tick.set_visible(False)
    for tick in ax.get_yticklabels():
        tick.set_fontproperties(font)
        tick.set_fontsize(fontsize*factor)

    if '0' in El_data.Hour.values:
        ind = El_data.index[El_data['Hour'] == '0'].tolist()
        if len(ind)>0: 
            ind1 = ind[0]
            print(ind)
            y_pos = ax.get_ylim()[1]-0.3
            ax.axvline(x = ind1, color = PALETTE['blue'], linewidth = linew, label = 'axvline - full height')
            if ind1>0:
                t = ax.text(float(ind1)-0.2, 
                        y_pos,
                        El_data.Weekday.iloc[ind1-1], 
                        horizontalalignment='right', 
                        verticalalignment='top',
                        fontproperties=font,
                        fontsize = fontsize*factor)
                t.set_bbox(dict(facecolor='white', alpha=0.8, edgecolor='white'))
            t = ax.text(float(ind1)+0.2, 
                    y_pos, 
                    El_data.Weekday.iloc[ind1]+' '+El_data.Date.iloc[ind1], 
                    horizontalalignment='left', 
                    verticalalignment='top',
                    fontproperties=font,
                    fontsize = fontsize*factor)
            t.set_bbox(dict(facecolor='white', alpha=0.8, edgecolor='white'))
    tit = plt.title('DKK/kWh', fontsize = fontsize*factor, loc='left',fontproperties=font)
    tit.set_fontweight(weight="bold")
            #plt.show()


    buf = io.BytesIO()

    fig.savefig(buf, format="png", dpi=dpi,bbox_inches='tight')
    fig.savefig('elpanel_plot.png', format="png", dpi=dpi)
    buf.seek(0)
    plot_image = Image.open(buf).convert("RGB")
    newsize = (hsize, vsize)
    im1 = plot_image.resize(newsize, Dither.NONE)
    #display(im1)
    buf.close()
    logger.info('Generated electricity price panel')
    return im1


