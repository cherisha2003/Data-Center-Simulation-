from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from model import simulate, variants, annualize
from calibration import calibrate
from diagnostics import climate_diagnostics,drought_diagnostics

CLIMATE=pd.read_csv(Path(__file__).resolve().parents[1]/'data/virginia_noaa_climate_2015_2025.csv')
BASE=calibrate(CLIMATE).settings

def test_2023_calibration_maintained():
    y=annualize(simulate(BASE,CLIMATE)).query('year == 2023').iloc[0]
    assert abs(y.electricity_gwh-32000)<1
    assert abs(y.water_use_ml-7949.3647464)<1

def test_max_monthly_recovery():
    x=simulate(variants(BASE)['Drought stress'],CLIMATE)
    assert (x.actual_utilization.diff().dropna()<=BASE.operating_ramp_up_per_month+1e-9).all()

def test_water_balance_and_nonnegativity():
    x=simulate(variants(BASE)['Drought stress'],CLIMATE)
    assert x.reservoir_ml.min()>=0
    assert (x.community_shortage_ml>=0).all()
    assert (x.community_served_ml<=BASE.community_demand_ml+1e-9).all()
    assert (x.freshwater_withdrawal_ml<=x.water_use_ml+1e-9).all()

def test_drought_diagnostics():
    x=drought_diagnostics(BASE,CLIMATE)
    assert len(x)==2
    assert (x.max_monthly_utilization_rebound_pp<=6.001).all()

def test_warming_diagnostics():
    x=climate_diagnostics(BASE,CLIMATE)
    assert len(x)==12
    b=x.query('case == "Baseline, ample resources" and year == 2040').iloc[0]
    w=x.query('case == "Warmer, ample resources" and year == 2040').iloc[0]
    assert w.mean_pue>b.mean_pue
    assert w.electricity_gwh>b.electricity_gwh
