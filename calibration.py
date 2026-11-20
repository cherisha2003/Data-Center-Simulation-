"""Transparent 2023 benchmark calibration for the monthly stock/flow simulator.

The electricity and water targets are two published estimates, not a yearly
observed dataset. Model fit at the calibration year is not independent validation.
"""
from dataclasses import dataclass, replace
import numpy as np
import pandas as pd
from model import Settings, simulate, annualize
from benchmarks import benchmark_2023, GALLON_TO_L

@dataclass(frozen=True)
class CalibrationResult:
    settings: Settings
    electricity_error_pct: float
    water_error_pct: float
    target_electricity_gwh: float
    target_water_ml: float
    electricity_gwh: float
    water_ml: float
    iterations: int


def reference_settings() -> Settings:
    """Regional infrastructure thought experiment; NOT a measured watershed.

    High baseline capacity for the grid and water buffer keeps the calibration
    year unconstrained. The physical buffer and its inflow are scenario values.
    """
    return Settings(
        initial_capacity_mw=500.0, target_growth_pct=8.0,
        historical_growth_pct=25.0,  # exploratory early growth, informed by 2015-to-2023 state energy plan trend
        grid_capacity_mw=4000.0, grid_expansion_mw_per_year=400.0,
        water_storage_ml=28000.0, storage_capacity_ml=40000.0,
        monthly_recharge_ml=2600.0, community_demand_ml=1150.0,
        water_use_l_kwh=0.34, utilization=0.80,
        warming_c_by_2040=2.0, electricity_carbon_kg_kwh=0.34,
        water_restriction_threshold=0.15,
    )


def _year_values(settings, climate, year=2023):
    annual = annualize(simulate(settings, climate=climate))
    return annual.loc[annual.year.eq(year)].iloc[0]


def calibrate(climate=None, growth_pct=8.0, base=None) -> CalibrationResult:
    """Fit initial IT capacity and total-water-use intensity to 2023 estimates.

    The calibration uses full stock/flow model runs, not a separate exponential
    approximation. Simple bounded iterations keep the procedure inspectable.
    """
    target = benchmark_2023()
    target_e = target['electricity_gwh']
    target_w = target['water_million_gal'] * GALLON_TO_L # million gallons -> ML
    s = replace(base or reference_settings(), target_growth_pct=float(growth_pct))
    # First solve electricity with a wide, nonbinding water buffer and the
    # provisional water intensity; then adjust intensity. Iterate because water
    # restrictions can couple both outputs.
    loops = 0
    for j in range(5):
        low, high = 100.0, 6500.0
        for k in range(25):
            middle = (low + high) / 2
            y = _year_values(replace(s,initial_capacity_mw=middle),climate)
            if y.electricity_gwh < target_e:
                low = middle
            else:
                high = middle
        s = replace(s, initial_capacity_mw=(low+high)/2)
        y = _year_values(s,climate)
        # Actual water is in ML, IT load in GWh, L/kWh IT = ML/GWh IT.
        it_energy = y.electricity_gwh - y.cooling_gwh
        if it_energy <= 0:
            raise ValueError('No IT energy during calibration')
        # water model multiplies nominal intensity by (1 + 0.015 * heat_index),
        # so infer the climate-weighted IT load first.
        monthly = simulate(s,climate=climate)
        m = monthly[monthly.year.eq(2023)]
        weighted_it = sum((r.electricity_gwh - r.cooling_gwh) *
                          (1+0.015*max(0.0,r.ambient_c-18.0))
                          for r in m.itertuples())
        if weighted_it <= 0:
            raise ValueError('Invalid weighted IT electricity')
        s = replace(s,water_use_l_kwh=target_w/weighted_it)
        loops += 1
    y = _year_values(s,climate)
    return CalibrationResult(
        settings=s,
        electricity_error_pct=100*(y.electricity_gwh-target_e)/target_e,
        water_error_pct=100*(y.water_use_ml-target_w)/target_w,
        target_electricity_gwh=target_e,target_water_ml=target_w,
        electricity_gwh=float(y.electricity_gwh),water_ml=float(y.water_use_ml),
        iterations=loops,
    )


def experiment_summary(settings, climate=None):
    """Use the same calibrated initial conditions for every scenario."""
    from model import variants
    frames = {}
    rows = []
    for name, cfg in variants(settings).items():
        monthly = simulate(cfg,climate=climate)
        annual = annualize(monthly)
        frames[name] = (monthly, annual)
        for year in [2023,2030,2040]:
            a = annual.loc[annual.year.eq(year)].iloc[0]
            rows.append({'scenario':name,'year':year,
                         'electricity_gwh':a.electricity_gwh,
                         'water_use_ml':a.water_use_ml,
                         'water_shortage_ml':a.unmet_water_ml,
                         'reservoir_ml':a.reservoir_ml,
                         'co2_mt':a.emissions_tonnes/1e6,
                         'capacity_mw':a.it_capacity_mw,
                         'utilization':a.actual_utilization})
    return frames, pd.DataFrame(rows)


def one_at_a_time_sensitivity(base, climate=None, range_fraction=0.2):
    """Vary one already-calibrated parameter; do NOT re-fit each perturbation."""
    changes = {'growth':('target_growth_pct',max(0,base.target_growth_pct*(1-range_fraction)),base.target_growth_pct*(1+range_fraction)),
               'water intensity':('water_use_l_kwh',base.water_use_l_kwh*(1-range_fraction),base.water_use_l_kwh*(1+range_fraction)),
               'grid expansion':('grid_expansion_mw_per_year',base.grid_expansion_mw_per_year*(1-range_fraction),base.grid_expansion_mw_per_year*(1+range_fraction)),
               'replenishment':('monthly_recharge_ml',base.monthly_recharge_ml*(1-range_fraction),base.monthly_recharge_ml*(1+range_fraction)),
               'warming':('warming_c_by_2040',max(0,base.warming_c_by_2040*(1-range_fraction)),base.warming_c_by_2040*(1+range_fraction))}
    rows=[]
    for name,(field,low,high) in changes.items():
        for label, value in [('low',low),('high',high)]:
            cfg=replace(base,**{field:value})
            y=annualize(simulate(cfg,climate=climate)).query('year == 2040').iloc[0]
            rows.append({'parameter':name,'setting':label,'value':value,'year':2040,
                         'electricity_gwh':y.electricity_gwh,'water_use_ml':y.water_use_ml,
                         'emissions_mt':y.emissions_tonnes/1e6,'end_water_ml':y.reservoir_ml})
    return pd.DataFrame(rows)
