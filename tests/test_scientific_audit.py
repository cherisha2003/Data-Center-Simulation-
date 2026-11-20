import pandas as pd
from emissions_data import rate_for_year, load_eia_generation_rates
from calibration import calibrate
from model import simulate, annualize
from science_audit import internal_checks, historical_context
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_eia_2023_rate_exact():
    v,source=rate_for_year(2023)
    assert abs(v-594*0.00045359237)<1e-8
    assert 'EIA' in source

def test_future_is_scenario_not_observation():
    _,source=rate_for_year(2030)
    assert 'SCENARIO' in source

def test_2015_is_labeled_proxy():
    _,source=rate_for_year(2015)
    assert 'NOT OBSERVED' in source

def test_mass_balance_and_capacity():
    c=pd.read_csv(ROOT/'data'/'virginia_noaa_climate_2015_2025.csv')
    cal=calibrate(c)
    rows=internal_checks(simulate(cal.settings,climate=c),cal.settings)
    assert rows['pass'].all(),rows.to_string(index=False)

def test_context_is_not_dc_only_observation():
    c=pd.read_csv(ROOT/'data'/'virginia_noaa_climate_2015_2025.csv')
    e=pd.read_csv(ROOT/'data'/'virginia_eia_state_total_sales.csv')
    z=historical_context(simulate(calibrate(c).settings,climate=c),e)
    assert len(z)>=10
    assert z.iloc[0].modeled_dc_to_state_sales_pct>0
    assert z.iloc[0].interpretation.startswith('RATIO')
