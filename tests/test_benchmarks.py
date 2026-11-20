from benchmarks import benchmark_2023, anchored_growth

def test_benchmarks():
    b=benchmark_2023()
    assert b['electricity_gwh']==32000
    assert 0.2 < b['water_l_per_facility_kwh'] < 0.3

def test_anchor():
    d=anchored_growth(8)
    assert len(d)==26
    assert d.query('year == 2023').iloc[0].dc_electricity_gwh==32000
    assert d.query('year == 2023').iloc[0].dc_total_water_million_gal==2100
    assert d.query('year == 2040').iloc[0].dc_electricity_gwh > 32000
