"""Independent historical observations and documented import pathways.

Statewide observations are contextual inputs: none is a measurement of data-center-only output.
"""
from io import BytesIO
import pandas as pd
import requests

CLIMATE_TAVG = 'https://api.climatedata.dev/v1/us-climate/tavg/us-va.csv'
CLIMATE_PCPN = 'https://api.climatedata.dev/v1/us-climate/pcpn/us-va.csv'
EIA_URL = 'https://www.eia.gov/electricity/data/state/index.php'


def parse_climate_csv(text: str, field: str) -> pd.DataFrame:
    from io import StringIO
    raw = pd.read_csv(StringIO(text))
    required = {'date','value'}
    if not required.issubset(raw):
        raise ValueError('Climate data requires date and value columns.')
    result = raw[['date','value']].copy()
    result['date'] = pd.to_datetime(result['date'], errors='coerce')
    result['value'] = pd.to_numeric(result['value'], errors='coerce')
    result = result.dropna().drop_duplicates('date').sort_values('date')
    result = result[result.date.dt.year.between(2015, 2025)]
    if field == 'temperature_c':
        result[field] = (result.value - 32) * 5 / 9
    elif field == 'precipitation_mm':
        result[field] = result.value * 25.4
    else:
        raise ValueError('Unknown climate variable')
    return result[['date',field]].reset_index(drop=True)


def get_virginia_climate(timeout=20):
    """Fetch real historical statewide NOAA nClimDiv data (via published CSV mirror)."""
    frames=[]
    for url,field in [(CLIMATE_TAVG,'temperature_c'),(CLIMATE_PCPN,'precipitation_mm')]:
        response=requests.get(url,timeout=timeout)
        response.raise_for_status()
        frames.append(parse_climate_csv(response.text,field))
    combined=frames[0].merge(frames[1],on='date',how='inner')
    if combined.empty:
        raise ValueError('No matching Virginia climate observations found.')
    combined['year']=combined.date.dt.year
    combined['month']=combined.date.dt.month
    return combined


def parse_observed_electricity(data, year_col, state_col, value_col, unit='MWh', state_value='Virginia'):
    """Convert an uploaded EIA worksheet/CSV to VA state total annual electricity context.

    Input state filtering and column mapping are explicit, as EIA worksheets change schemas.
    Do NOT call the result data-center-only consumption.
    """
    x=data.copy()
    x=x.loc[x[state_col].astype(str).str.strip().str.lower().isin(
        ['virginia','va'] if not state_value else [state_value.strip().lower(), 'va'])]
    x['year']=pd.to_numeric(x[year_col],errors='coerce')
    x['value']=pd.to_numeric(x[value_col].astype(str).str.replace(',','',regex=False),errors='coerce')
    factor={'MWh':1/1000,'GWh':1,'TWh':1000,'thousand MWh':1}
    if unit not in factor:raise ValueError('Unsupported input unit')
    x=x.dropna(subset=['year','value'])
    x=x[x.year.between(2015,2025)]
    x=x.groupby('year',as_index=False)['value'].sum()
    x['year']=x.year.astype(int)
    x['virginia_total_sales_gwh']=x.value*factor[unit]
    x['data_type']='OBSERVED STATE-TOTAL / NOT DC-ONLY'
    return x[['year','virginia_total_sales_gwh','data_type']]
