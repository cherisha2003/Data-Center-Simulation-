"""Model diagnostics for the climate, water and infrastructure feedbacks.

These are comparisons between model runs, not independent validation.
"""
from dataclasses import replace
import pandas as pd
from model import simulate, variants, annualize


def climate_diagnostics(settings, climate=None):
    """Separate change in cooling requirement from available electricity."""
    scenarios = {
        'Baseline, constrained': settings,
        'Warmer, constrained': replace(settings, warming_c_by_2040=4.0),
        'Baseline, ample resources': replace(settings, grid_capacity_mw=100000.,
            grid_expansion_mw_per_year=10000., storage_capacity_ml=1e9,
            water_storage_ml=1e9, monthly_recharge_ml=1e8),
        'Warmer, ample resources': replace(settings, warming_c_by_2040=4.0,
            grid_capacity_mw=100000., grid_expansion_mw_per_year=10000.,
            storage_capacity_ml=1e9, water_storage_ml=1e9, monthly_recharge_ml=1e8),
    }
    out=[]
    for name,s in scenarios.items():
        monthly=simulate(s,climate)
        yearly=annualize(monthly)
        for year in [2030,2035,2040]:
            r=yearly[yearly.year.eq(year)].iloc[0]
            out.append({'case':name,'year':year,
                        'electricity_gwh':r.electricity_gwh,
                        'cooling_gwh':r.cooling_gwh,
                        'mean_pue':r.pue,
                        'water_use_ml':r.water_use_ml,
                        'installed_it_mw':r.it_capacity_mw,
                        'mean_utilization':r.actual_utilization})
    return pd.DataFrame(out)


def drought_diagnostics(settings, climate=None):
    rows=[]
    for name in ['Base case','Drought stress']:
        df=simulate(variants(settings)[name],climate)
        forecast=df[df.year.between(2025,2040)].copy()
        diff=forecast.actual_utilization.diff().dropna()
        rows.append({'scenario':name,
            'max_monthly_utilization_rebound_pp':100*max(0,diff.max()),
            'min_utilization_pct':100*forecast.actual_utilization.min(),
            'months_below_25pct_utilization':int((forecast.actual_utilization<0.25).sum()),
            'community_water_shortage_ml':forecast.community_shortage_ml.sum(),
            'facility_unmet_water_demand_ml':forecast.unmet_water_ml.sum(),
            'minimum_buffer_ml':forecast.reservoir_ml.min()})
    return pd.DataFrame(rows)
