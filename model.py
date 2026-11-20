"""Monthly system-dynamics sandbox for data-center infrastructure and resources.

All defaults are scenario assumptions, not observed Virginia time series.
Time step is one month; stocks are updated from flows, and constraints feed back.
"""
from dataclasses import dataclass, replace
import calendar
import math
import pandas as pd
from emissions_data import rate_for_year

@dataclass(frozen=True)
class Settings:
    start_year: int = 2015
    end_year: int = 2040
    initial_capacity_mw: float = 500.0
    target_growth_pct: float = 8.0
    historical_growth_pct: float | None = None  # separate historical expansion rate; 2024+ follows scenario growth
    grid_capacity_mw: float = 1050.0
    grid_expansion_mw_per_year: float = 115.0
    water_storage_ml: float = 15000.0
    storage_capacity_ml: float = 22000.0
    monthly_recharge_ml: float = 1700.0
    community_demand_ml: float = 1150.0
    water_use_l_kwh: float = 0.65
    freshwater_fraction: float = 0.65  # assumed share of total facility water drawing on freshwater buffer
    electricity_carbon_kg_kwh: float = 0.34
    use_eia_generation_rate: bool = True  # use documented 2021-24 output rate proxy
    grid_cleaning_pct: float = 1.7
    warming_c_by_2040: float = 2.0
    seasonal_temp_amplitude_c: float = 12.0
    cooling_weather_sensitivity: float = 0.020
    utilization: float = 0.80
    water_restriction_threshold: float = 0.30
    cooling_efficiency: float = 1.0
    water_efficiency: float = 1.0
    drought_severity: float = 0.0
    grid_investment: float = 1.0
    operating_ramp_up_per_month: float = 0.06  # assumption: recovery limited to 6 percentage points monthly


def simulate(s: Settings, climate=None) -> pd.DataFrame:
    if s.start_year >= s.end_year:
        raise ValueError('End year must be greater than start year')
    if s.initial_capacity_mw <= 0 or s.grid_capacity_mw <= 0:
        raise ValueError('Capacities must be positive')
    if not 0 < s.utilization <= 1:
        raise ValueError('Utilization must be (0,1]')
    if s.water_storage_ml < 0 or s.storage_capacity_ml <= 0:
        raise ValueError('Invalid reservoir values')
    if s.target_growth_pct < 0 or s.water_use_l_kwh < 0:
        raise ValueError('Invalid growth or water use')
    if not 0 < s.freshwater_fraction <= 1:
        raise ValueError('Freshwater share must be (0,1]')
    if not 0 < s.operating_ramp_up_per_month <= 1:
        raise ValueError('Operating ramp-up must be (0,1]')
    capacity = s.initial_capacity_mw
    grid_capacity = s.grid_capacity_mw
    reservoir = min(s.water_storage_ml, s.storage_capacity_ml)
    cumulative_co2 = 0.0
    cumulative_water = 0.0
    previous_utilization = s.utilization
    rows = []
    climate_lookup = {}
    monthly_precip_normals = {}
    if climate is not None and not climate.empty:
        climate_lookup = {(int(r.year), int(r.month)): (float(r.temperature_c), float(r.precipitation_mm))
                          for r in climate.itertuples()}
        monthly_precip_normals = climate.groupby('month')['precipitation_mm'].mean().to_dict()
    for i in range((s.end_year-s.start_year+1)*12):
        year = s.start_year + i//12
        month = i%12 + 1
        elapsed = i/12
        hours = 24 * calendar.monthrange(year, month)[1]
        trend = s.warming_c_by_2040 * min(1.0, max(0.0, elapsed/25))
        # Seasonal fallback is used when there is no observed temperature input.
        seasonal_temp = s.seasonal_temp_amplitude_c * math.cos(2*math.pi*(month-7)/12)
        ambient = 14 + seasonal_temp + trend
        # Use actual statewide observed temperature in 2015–2024 when available.
        # Post-2024 temperatures remain explicitly hypothetical scenario forcings.
        climate_source = 'SCENARIO / ASSUMED'
        if year <= 2024 and (year,month) in climate_lookup:
            ambient = climate_lookup[(year,month)][0]
            climate_source = 'OBSERVED NOAA VA STATEWIDE'
        heat_index = max(0.0, ambient-18.0)
        cooling_multiplier = max(0.6, (1+s.cooling_weather_sensitivity*heat_index)*s.cooling_efficiency)
        pue = 1.16 + 0.22 * cooling_multiplier
        # Recharge varies by season and by the chosen drought scenario.
        seasonal_rain = 1 + 0.22 * math.cos(2*math.pi*(month-3)/12)
        drought_multiplier = 1 - s.drought_severity * (0.6+0.4*math.sin(2*math.pi*i/(12*5))**2)
        # Observed statewide precipitation can modulate recharge; this is not
        # a calibrated site-specific hydrology or a measured reservoir level.
        if year <= 2024 and (year,month) in climate_lookup:
            pcp = climate_lookup[(year,month)][1]
            normal = monthly_precip_normals.get(month, pcp)
            if normal > 0:
                seasonal_rain = max(0.15, min(2.5, pcp/normal))
        recharge = s.monthly_recharge_ml * seasonal_rain * max(0.05,drought_multiplier)
        # Limit new IT capacity to the power that the grid can support.
        required_facility_mw = capacity*s.utilization*pue
        headroom = max(0.0, grid_capacity - required_facility_mw)
        effective_growth_pct = (s.historical_growth_pct if year <= 2023 and s.historical_growth_pct is not None else s.target_growth_pct)
        potential_growth = capacity*effective_growth_pct/1200
        allowed_growth = min(potential_growth, headroom/max(s.utilization*pue,0.01))
        capacity_added = max(0.0,allowed_growth)
        # Allocate community water first. A shortage in the remaining supply
        # reduces the facility load for the current month.
        reservoir_at_start_ml = reservoir
        water_fraction = reservoir/s.storage_capacity_ml
        reserve_throttling = max(0.0, min(1.0,water_fraction/max(s.water_restriction_threshold,0.01)))
        intended_utilization = s.utilization*reserve_throttling
        desired_it_gwh = capacity*intended_utilization*hours/1000
        water_per_it_gwh = s.water_use_l_kwh*s.water_efficiency*(1+0.015*heat_index)
        desired_water_ml = desired_it_gwh*water_per_it_gwh
        community_served_ml = min(s.community_demand_ml, reservoir+recharge)
        community_shortage_ml = max(0.0, s.community_demand_ml-community_served_ml)
        resource_available = max(0.0,reservoir+recharge-community_served_ml)
        freshwater_demand_ml = desired_water_ml*s.freshwater_fraction
        availability_ratio = (min(1.0,resource_available/freshwater_demand_ml)
                              if freshwater_demand_ml > 0 else 1.0)
        grid_ratio = min(1.0,grid_capacity/max(capacity*intended_utilization*pue,1e-9))
        # The facility can curtail immediately, but recovery is gradual.
        resource_limited_utilization = intended_utilization*min(availability_ratio,grid_ratio)
        actual_utilization = min(resource_limited_utilization,
                                 previous_utilization+s.operating_ramp_up_per_month)
        previous_utilization = actual_utilization
        it_gwh = capacity*actual_utilization*hours/1000
        facility_gwh = it_gwh*pue
        cooling_gwh = facility_gwh-it_gwh
        water_ml = desired_water_ml
        actual_water_ml = it_gwh*water_per_it_gwh
        freshwater_withdrawal_ml = actual_water_ml*s.freshwater_fraction
        reclaimed_water_ml = actual_water_ml-freshwater_withdrawal_ml
        unmet_water_ml = max(0.0,water_ml-actual_water_ml)
        spill = max(0.0,reservoir+recharge-community_served_ml-freshwater_withdrawal_ml-s.storage_capacity_ml)
        reservoir = max(0.0,min(s.storage_capacity_ml,reservoir+recharge-community_served_ml-freshwater_withdrawal_ml))
        intensity, emissions_rate_source = rate_for_year(
            year, s.electricity_carbon_kg_kwh, s.grid_cleaning_pct, s.use_eia_generation_rate)
        co2_tonnes = facility_gwh*intensity*1000
        cumulative_co2 += co2_tonnes
        cumulative_water += actual_water_ml
        rows.append({'year':year,'month':month,'date':pd.Timestamp(year,month,1),
                     'it_capacity_mw':capacity,'grid_capacity_mw':grid_capacity,
                     'capacity_added_mw':capacity_added,'ambient_c':ambient,
                     'temperature_anomaly_c':trend,'climate_source':climate_source,'reservoir_ml':reservoir,
                     'recharge_ml':recharge,'reservoir_start_ml':reservoir_at_start_ml,
                     'community_served_ml':community_served_ml,
                     'community_shortage_ml':community_shortage_ml,'pue':pue,'actual_utilization':actual_utilization,
                     'electricity_gwh':facility_gwh,'cooling_gwh':cooling_gwh,
                     'water_demand_ml':water_ml,'water_use_ml':actual_water_ml,
                     'freshwater_withdrawal_ml':freshwater_withdrawal_ml,'reclaimed_water_ml':reclaimed_water_ml,
                     'unmet_water_ml':unmet_water_ml,'spillage_ml':spill,
                     'emissions_tonnes':co2_tonnes,'electricity_co2_kg_kwh':intensity,
                     'emissions_rate_source':emissions_rate_source,
                     'cumulative_emissions_tonnes':cumulative_co2,
                     'cumulative_water_ml':cumulative_water,'data_type':'SIMULATED / NOT OBSERVED'})
        capacity += capacity_added
        grid_capacity += s.grid_expansion_mw_per_year*s.grid_investment/12
    return pd.DataFrame(rows)


def variants(s: Settings):
    return {
       'Base case':s,
       'Hotter future':replace(s,warming_c_by_2040=4.0),
       'Drought stress':replace(s,drought_severity=0.60),
       'Efficient cooling':replace(s,cooling_efficiency=0.78,water_efficiency=0.75),
       'Grid investment':replace(s,grid_investment=1.8),
       'Rapid expansion':replace(s,target_growth_pct=min(25,s.target_growth_pct+5)),
    }


def annualize(df: pd.DataFrame):
    flows = ['electricity_gwh','cooling_gwh','water_demand_ml','water_use_ml','freshwater_withdrawal_ml','reclaimed_water_ml','unmet_water_ml','emissions_tonnes','recharge_ml','capacity_added_mw','community_served_ml','community_shortage_ml']
    stocks = ['it_capacity_mw','grid_capacity_mw','reservoir_ml','cumulative_emissions_tonnes','cumulative_water_ml']
    means = ['ambient_c','pue','actual_utilization','temperature_anomaly_c','electricity_co2_kg_kwh']
    spec = {**{x:'sum' for x in flows}, **{x:'last' for x in stocks}, **{x:'mean' for x in means}}
    return df.groupby('year',as_index=False).agg(spec)


def historical_comparison(observed, annual, variable='electricity_gwh'):
    needed={'year','observed_dc_electricity_gwh'}
    if not needed.issubset(observed.columns):
        raise ValueError('Expected year, observed_dc_electricity_gwh')
    x=observed[['year','observed_dc_electricity_gwh']].copy()
    for col in x: x[col]=pd.to_numeric(x[col],errors='coerce')
    x=x.dropna().drop_duplicates('year')
    x=x[x.year.between(2015,2024)]
    return x.merge(annual[['year',variable]],on='year',how='inner')
