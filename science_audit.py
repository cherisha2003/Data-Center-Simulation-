"""Reproducible conservation checks, provenance, and plausibility context.
These are *internal model checks*, not predictive validation against independent data.
"""
import pandas as pd
import numpy as np
from model import annualize,simulate
from emissions_data import load_eia_generation_rates


def internal_checks(monthly, settings):
    if monthly.empty: raise ValueError('Empty simulation output')
    d=monthly
    end=d.reservoir_ml.to_numpy()
    expected=d.reservoir_start_ml+d.recharge_ml-d.community_served_ml-d.freshwater_withdrawal_ml-d.spillage_ml
    residual=end-expected.to_numpy()
    facility_load=d.it_capacity_mw*d.actual_utilization*d.pue
    errors={
        'water_balance_max_abs_ml':float(abs(residual).max()),
        'water_below_zero_months':int((end < -1e-7).sum()),
        'water_above_capacity_months':int((end>settings.storage_capacity_ml+1e-7).sum()),
        'monthly_grid_capacity_excess_max_mw':float(max(0,(facility_load-d.grid_capacity_mw).max())),
        'freshwater_fraction_max_abs_ml':float((d.water_use_ml-d.freshwater_withdrawal_ml-d.reclaimed_water_ml).abs().max()),
        'carbon_accounting_max_abs_tonnes':float((d.electricity_gwh*d.electricity_co2_kg_kwh*1000-d.emissions_tonnes).abs().max()),
        'missing_historical_months_2015_2024':int(120-sum((d.year<=2024)&(d.climate_source=='OBSERVED NOAA VA STATEWIDE'))),
    }
    return pd.DataFrame([{'check':k,'value':v,'pass':(v<1e-5)} for k,v in errors.items()])


def historical_context(monthly,state_eia):
    d=annualize(monthly)
    z=d.merge(state_eia[['year','virginia_total_sales_gwh']],on='year',how='inner')
    z['modeled_dc_to_state_sales_pct']=100*z.electricity_gwh/z.virginia_total_sales_gwh
    z['interpretation']='RATIO OF RECONSTRUCTED DC DEMAND TO OBSERVED STATEWIDE SALES; NOT VALIDATION'
    return z[['year','electricity_gwh','virginia_total_sales_gwh','modeled_dc_to_state_sales_pct','interpretation']]
