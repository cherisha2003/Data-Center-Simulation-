from dataclasses import replace
from model import Settings, simulate, annualize

def test_monthly_resolution():
    x=simulate(Settings());assert len(x)==26*12

def test_reservoir_stays_bounded():
    x=simulate(Settings(drought_severity=.75));assert x.reservoir_ml.min()>=0;assert x.reservoir_ml.max()<=22000

def test_monthly_seasonality():
    x=simulate(Settings());assert x.query('year == 2020').cooling_gwh.nunique()>2

def test_annual_energy_conservation():
    x=simulate(Settings());assert abs(x.electricity_gwh.sum()-annualize(x).electricity_gwh.sum())<1e-7

def test_drought_changes_reservoir():
    s=Settings(); a=simulate(s); b=simulate(replace(s,drought_severity=.70)); assert b.query("year == 2020").reservoir_ml.mean() < a.query("year == 2020").reservoir_ml.mean()

def test_grid_constraints_change_capacity():
    s=Settings(); a=simulate(replace(s,grid_expansion_mw_per_year=10)); b=simulate(replace(s,grid_expansion_mw_per_year=300)); assert b.it_capacity_mw.iloc[-1]>a.it_capacity_mw.iloc[-1]

def test_efficiency_reduces_cooling():
    s=Settings();a=simulate(s);b=simulate(replace(s,cooling_efficiency=.75)); assert b.cooling_gwh.sum()<a.cooling_gwh.sum()
