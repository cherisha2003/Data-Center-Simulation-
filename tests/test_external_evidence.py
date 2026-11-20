from calibration import calibrate
from model import simulate
from external_evidence import crosscheck, load_external
import pandas as pd


def test_historical_growth_is_separate_from_scenario_growth():
    c=pd.read_csv('data/virginia_noaa_climate_2015_2025.csv')
    s=calibrate(c).settings
    assert s.historical_growth_pct == 25
    assert s.target_growth_pct == 8


def test_external_checks_and_calibration():
    c=pd.read_csv('data/virginia_noaa_climate_2015_2025.csv')
    cal=calibrate(c)
    df=crosscheck(simulate(cal.settings,c))
    assert abs(cal.electricity_error_pct)<0.01
    assert abs(cal.water_error_pct)<0.01
    holdout=df[df.role=='HISTORICAL CROSS-CHECK']
    assert set(holdout.year)=={2019,2021,2022,2024}
    assert holdout.within_illustrative_chart_band.all()
    assert not df.loc[df.year.eq(2015),'role'].iloc[0]=='HISTORICAL CROSS-CHECK'


def test_approximate_source_labels():
    x=load_external()
    assert len(x)>=6
    assert x.data_kind.str.contains('APPROXIMATE').all()
    assert x.uncertainty_gwh.gt(0).all()
