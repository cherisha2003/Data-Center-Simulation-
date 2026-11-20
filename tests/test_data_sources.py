import pandas as pd
from data_sources import parse_climate_csv, parse_observed_electricity
from model import Settings, simulate

def test_temperature_parser():
    climate=parse_climate_csv('date,value\n2015-01,32\n2015-02,50\n', 'temperature_c')
    assert len(climate)==2 and abs(climate.temperature_c.iloc[0])<1e-8

def test_precip_parser():
    climate=parse_climate_csv('date,value\n2015-01,1\n', 'precipitation_mm')
    assert climate.precipitation_mm.iloc[0] == 25.4

def test_eia_state_only_not_dc():
    raw=pd.DataFrame({'State':['VA','Georgia','Virginia'],'Year':[2015,2015,2016],'Sales':[1000,99999,2000]})
    out=parse_observed_electricity(raw,'Year','State','Sales','MWh')
    assert out.virginia_total_sales_gwh.tolist()==[1.,2.]
    assert 'NOT DC-ONLY' in out.data_type.iloc[0]

def test_water_shortage_can_throttle_electricity():
    baseline=simulate(Settings(end_year=2016))
    stressed=simulate(Settings(end_year=2016,monthly_recharge_ml=1,community_demand_ml=2000,water_storage_ml=100))
    assert stressed.electricity_gwh.sum() < baseline.electricity_gwh.sum()
    assert (stressed.reservoir_ml>=0).all()

def test_observed_climate_modifies_2015_ambient():
    dummy=pd.DataFrame({'year':[2015],'month':[1],'temperature_c':[33.0],'precipitation_mm':[100.0]})
    out=simulate(Settings(end_year=2016),climate=dummy)
    assert out.iloc[0].ambient_c == 33.0
    assert out.iloc[0].climate_source == 'OBSERVED NOAA VA STATEWIDE'
