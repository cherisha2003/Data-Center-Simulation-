import pandas as pd
from dataclasses import replace
from pathlib import Path
from calibration import calibrate, experiment_summary, one_at_a_time_sensitivity
from model import simulate, annualize
DATA=Path(__file__).resolve().parents[1]/'data'

def climate():
    return pd.read_csv(DATA/'virginia_noaa_climate_2015_2025.csv',parse_dates=['date'])

def test_2023_electricity_and_water_match_benchmarks():
    r=calibrate(climate())
    assert abs(r.electricity_error_pct)<0.1
    assert abs(r.water_error_pct)<0.1

def test_water_buffer_is_conserved_and_bounded():
    r=calibrate(climate()); s=r.settings
    a=simulate(s,climate=climate())
    assert a.reservoir_ml.ge(0).all()
    assert a.reservoir_ml.le(s.storage_capacity_ml+1e-8).all()

def test_drought_reduces_water_dependent_operation():
    r=calibrate(climate());s=r.settings
    a=annualize(simulate(s,climate=climate()))
    b=annualize(simulate(replace(s,drought_severity=.60),climate=climate()))
    assert b[b.year.eq(2040)].electricity_gwh.iloc[0] < a[a.year.eq(2040)].electricity_gwh.iloc[0]

def test_energy_balance_and_units():
    r=calibrate(climate());a=simulate(r.settings,climate=climate())
    assert (a.electricity_gwh>=a.cooling_gwh).all()
    assert (a.water_use_ml<=a.water_demand_ml+1e-6).all()

def test_grid_limits_growth():
    s=calibrate(climate()).settings
    small=simulate(replace(s,grid_expansion_mw_per_year=50),climate=climate())
    large=simulate(replace(s,grid_expansion_mw_per_year=800),climate=climate())
    assert small.it_capacity_mw.iloc[-1] < large.it_capacity_mw.iloc[-1]

def test_sensitivity_has_two_values_per_parameter():
    s=calibrate(climate()).settings
    result=one_at_a_time_sensitivity(s,climate=climate())
    assert len(result)==10
    assert set(result.setting)=={'low','high'}

def test_reclaimed_water_separated_from_freshwater():
    s=calibrate(climate()).settings
    m=simulate(s,climate=climate())
    assert (abs(m.water_use_ml-m.freshwater_withdrawal_ml-m.reclaimed_water_ml)<1e-6).all()
    assert (m.freshwater_withdrawal_ml <= m.water_use_ml+1e-8).all()

def test_grid_power_not_exceeded():
    s=calibrate(climate()).settings
    m=simulate(s,climate=climate())
    from calendar import monthrange
    supplied_mw=[r.electricity_gwh*1000/(24*monthrange(int(r.year),int(r.month))[1]) for r in m.itertuples()]
    assert all(v<=g+1e-6 for v,g in zip(supplied_mw,m.grid_capacity_mw))
