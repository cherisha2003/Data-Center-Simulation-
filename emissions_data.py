"""EIA Virginia electricity-generation CO2 rates and explicitly labeled projections.

The EIA generation-output rate is not the delivered-grid consumption intensity:
Virginia imports electricity. Treat this as a documented scenario proxy,
not metered data-center emissions or a marginal emissions factor.
"""
from pathlib import Path
import pandas as pd
from functools import lru_cache

SOURCE=Path(__file__).resolve().parent/'data'/'virginia_eia_generation_co2_rate_2021_2024.csv'

@lru_cache(maxsize=1)
def load_eia_generation_rates():
    d=pd.read_csv(SOURCE).sort_values('year')
    assert d.year.tolist()==[2021,2022,2023,2024]
    return d

@lru_cache(maxsize=256)
def rate_for_year(year, base_kg_kwh=0.34, cleaning_pct=1.7, use_eia=True):
    if not use_eia:
        return (float(base_kg_kwh)*(1-cleaning_pct/100)**(year-2015), 'ASSUMED FACTOR AND DECLINE')
    d=load_eia_generation_rates()
    measured=dict(zip(d.year.astype(int),d.co2_kg_per_kwh))
    if year in measured:
        return (float(measured[year]),'EIA OBSERVED GENERATION OUTPUT RATE (proxy)')
    if year<2021:
        return (float(measured[2021]),'2021 EIA PROXY FOR 2015–2020 (NOT OBSERVED FOR YEAR)')
    return (float(measured[2024]*(1-cleaning_pct/100)**(year-2024)),
            'POST-2024 SCENARIO: 2024 EIA RATE WITH ASSUMED ANNUAL DECLINE')
