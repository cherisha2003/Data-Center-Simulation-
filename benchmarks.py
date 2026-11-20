"""Source-labeled historical benchmarks; not direct metering nor independent validation."""
from pathlib import Path
import pandas as pd
GALLON_TO_L = 3.785411784
DATA_DIR = Path(__file__).resolve().parent / 'data'

def load_benchmarks():
    return pd.read_csv(DATA_DIR / 'published_dc_benchmarks.csv')

def benchmark_2023():
    a = load_benchmarks()
    electricity = float(a[(a.year==2023)&(a.measure=='dc_electricity')].value.iloc[0])
    water = float(a[(a.year==2023)&(a.measure=='dc_water_total')].value.iloc[0])
    intensity = water * 1e6 * GALLON_TO_L / (electricity * 1e6) # L/kWh facility consumption
    return {'electricity_gwh': electricity, 'water_million_gal': water, 'water_l_per_facility_kwh': intensity}

def anchored_growth(growth_rate_pct=8.0, start=2015, end=2040):
    """Transparent anchored scenario, NOT an independently validated forecast."""
    if not 0 <= growth_rate_pct <= 30:
        raise ValueError('Growth rate should be between 0 and 30%')
    b = benchmark_2023()
    rows=[]
    for yr in range(start,end+1):
        # Year 2023 is a calibration anchor; other values are estimated / hypothetical.
        electricity = b['electricity_gwh']*(1+growth_rate_pct/100)**(yr-2023)
        water = electricity * b['water_l_per_facility_kwh']/GALLON_TO_L # million gallons per GWh: cancels 1e6 factors
        rows.append({'year':yr,'dc_electricity_gwh':electricity,'dc_total_water_million_gal':water,
                     'series_status':'2023 RESEARCH-BASED CALIBRATION ANCHOR' if yr==2023 else 'MODEL RECONSTRUCTION' if yr<2025 else 'SCENARIO PROJECTION'})
    return pd.DataFrame(rows)
