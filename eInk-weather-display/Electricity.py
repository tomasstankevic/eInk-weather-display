import io
import logging
from datetime import datetime, timedelta

import matplotlib as mpl
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import requests
from matplotlib import pyplot as plt
from PIL import Image
from PIL.Image import Dither

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

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig()

# Define region
REGION = 'east'

# Define tariff rates for get_El_price
transport_tarrifs = [1.32, 1.67, 1.32, 1.25]  # Day, Evening, Late Evening, Night

def _make_El_price_URL(start_date: str, end_date: str, region: str) -> str:
    endpoint = "https://api.energidataservice.dk/dataset/"
    dataset = "Elspotprices?"
    parameters = f"filter={{\"PriceArea\":\"DK2\"}}&start={start_date}&end={end_date}"
    url = endpoint + dataset + parameters
    return url

def _make_El_price_URL_andel(start_date: str, end_date: str, region: str) -> str:
    url = (
        "https://andelenergi.dk/?obexport_format=csv"
        f"&obexport_start={start_date}"
        f"&obexport_end={end_date}"
        f"&obexport_region={region}"
        "&obexport_tax=0&obexport_product_id=1%231%23TIMEENERGI"
    )
    return url

def check_new_data_availability(df: pd.DataFrame) -> bool:
    tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
    if tomorrow in df['Date'].values:
        logger.info('Prices for tomorrow available')
        return True
    else:
        logger.info('No price data for tomorrow')
        return False

def assign_tariff(hour: int) -> float:
    if 6 <= hour < 16:
        return transport_tarrifs[0]  # Day
    elif 16 <= hour < 21:
        return transport_tarrifs[1]  # Evening
    elif 21 <= hour < 24:
        return transport_tarrifs[2]  # Late Evening
    else:
        return transport_tarrifs[3]  # Night

def get_El_price(start_date, end_date, region):
    url = _make_El_price_URL(
        start_date.strftime("%Y-%m-%dT%H:%M"),
        end_date.strftime("%Y-%m-%dT%H:%M"),
        region
    )

    logger.info(f"Fetching data from: {url}")

    NP_spotprices_json = requests.get(url).json()
    NP_spotprices = pd.DataFrame.from_dict(NP_spotprices_json['records'])

    # Sort data in ascending order
    NP_spotprices = NP_spotprices.sort_values(by='HourUTC', ascending=True)

    # Calculate 'Andel_DKK'
    NP_spotprices['Andel_DKK'] = NP_spotprices['SpotPriceDKK'] / 1000.0 * 1.4 + 0.02

    # Parse datetime columns
    NP_spotprices['Datetime_DK'] = pd.to_datetime(NP_spotprices['HourDK'])
    NP_spotprices['Datetime_UTC'] = pd.to_datetime(NP_spotprices['HourUTC'])
    NP_spotprices = NP_spotprices.set_index('Datetime_UTC')

    # Create DataFrame 'df'
    df = pd.DataFrame({
        'Date': NP_spotprices['Datetime_DK'].dt.date.astype(str),
        'Time': NP_spotprices['Datetime_DK'].dt.time.astype(str),
        'Hour': NP_spotprices['Datetime_DK'].dt.hour,
        'Datetime': NP_spotprices['Datetime_DK'],
        'Price_el': NP_spotprices['Andel_DKK'],
        'Weekday': NP_spotprices['Datetime_DK'].dt.day_name().str.slice(0, 3)
    })

    df['WeekHour'] = df['Weekday'] + df['Hour'].astype(str)

    # Assign tariff using predefined rates and time ranges
    df['Tariff'] = df['Hour'].apply(assign_tariff)

    # Calculate total price
    df['Price'] = df['Price_el'] + df['Tariff']

    # Filter future data
    df_future = df[df['Datetime'] > datetime.now() - timedelta(hours=1)]
    df_future.reset_index(drop=True, inplace=True)

    # Check for new data availability
    new_data = check_new_data_availability(df_future)

    return df_future, new_data

def get_El_price_andel(start_date, end_date, region):
    url = _make_El_price_URL_andel(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        region
    )
    logger.info(f"Fetching data from: {url}")

    try:
        el_data = pd.read_csv(url, decimal=',', sep=',', encoding='utf-8')
    except Exception:
        logger.exception('Error getting price data from: %s', url)
        return None, None

    # Parse 'Start' column to datetime
    el_data['Datetime_DK'] = pd.to_datetime(el_data['Start'], format='%d.%m.%Y - %H:%M')

    # Convert numeric columns from string to float
    numeric_cols = ['Elpris', 'Transport og afgifter', 'Total']
    for col in numeric_cols:
        el_data[col] = el_data[col].astype(str).str.replace(',', '.').astype(float)

    # Sort data in ascending order
    el_data = el_data.sort_values(by='Datetime_DK', ascending=True)

    # Extract date and time components
    el_data['Date'] = el_data['Datetime_DK'].dt.date.astype(str)
    el_data['Time'] = el_data['Datetime_DK'].dt.time.astype(str)
    el_data['Hour'] = el_data['Datetime_DK'].dt.hour
    el_data['Weekday'] = el_data['Datetime_DK'].dt.day_name().str.slice(0, 3)
    el_data['WeekHour'] = el_data['Weekday'] + el_data['Hour'].astype(str)

    # Use 'Total' price and 'Transport og afgifter' directly from CSV
    el_data['Price'] = el_data['Total']
    el_data['Tariff'] = el_data['Transport og afgifter']
    el_data['Price_el'] = el_data['Elpris']

    # Filter future data
    df_future = el_data[el_data['Datetime_DK'] > datetime.now() - timedelta(hours=1)]
    df_future.reset_index(drop=True, inplace=True)

    # Check for new data availability
    new_data = check_new_data_availability(df_future)

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

    ax.bar(El_data.WeekHour, El_data.Price, 0.4, color=El_data.RGB, edgecolor=El_data.HatchRGB, hatch='/', linewidth = linew)

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


