"""Virginia data center system dynamics — calibrated research prototype."""
from dataclasses import replace
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from model import simulate, annualize, variants
from benchmarks import load_benchmarks, benchmark_2023
from calibration import calibrate, experiment_summary, one_at_a_time_sensitivity
from diagnostics import climate_diagnostics, drought_diagnostics
from science_audit import internal_checks, historical_context
from emissions_data import load_eia_generation_rates
from external_evidence import crosscheck

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'

@st.cache_data(show_spinner=False)
def historical_inputs():
    c = pd.read_csv(DATA/'virginia_noaa_climate_2015_2025.csv',parse_dates=['date'])
    e = pd.read_csv(DATA/'virginia_eia_state_total_sales.csv')
    return c,e

@st.cache_data(show_spinner=False)
def calibration_from_file():
    c,_=historical_inputs()
    return calibrate(c)

st.set_page_config(page_title='Virginia Data Center | Systems Simulation',layout='wide')
st.markdown('''<style>
.block-container{max-width:1330px;padding-top:1.35rem}
h1,h2,h3{letter-spacing:-.026em}
[data-testid="stMetric"]{background:rgba(117,119,123,.08);padding:14px;border-radius:11px}
</style>''',unsafe_allow_html=True)
st.title('Virginia Data Center Systems Simulation')
st.caption('CSC 8840 · Virginia case study · Monthly stock–flow model · 2015–2040')
st.info('2023 electricity and water outputs are fitted to published Virginia estimates. Climate and statewide electricity observations are real. The water buffer and grid allocation are hypothetical local infrastructure, not observed Virginia facilities. Calibration is not independent historical validation.')
climate, state_eia=historical_inputs()
cal = calibration_from_file()
base=cal.settings

with st.sidebar:
    st.header('Scenario controls')
    st.caption('Calibrated 2023 benchmark; changes below explore alternative futures and operating conditions.')
    scenario=st.selectbox('Scenario',list(variants(base).keys()))
    st.divider()
    st.caption('These manual changes will move the model away from its benchmark-calibrated baseline.')
    growth=st.slider('IT capacity growth (%/year)',0.0,18.0,float(base.target_growth_pct),0.5)
    replenishment=st.slider('Illustrative replenishment (ML/month)',600,4500,int(base.monthly_recharge_ml),100)
    gridexp=st.slider('Grid expansion (MW/year)',0,800,int(base.grid_expansion_mw_per_year),25)
    warming=st.slider('Warming by 2040 (°C)',0.0,5.0,float(base.warming_c_by_2040),0.25)
    ramp=st.slider('Maximum monthly recovery (percentage points)',2,20,int(base.operating_ramp_up_per_month*100),1)
    st.caption('2023 fit only applies to the original baseline values. 2015–2024 values are reconstructed, not observations. Historical growth (25%) is separate from future scenario growth.')
manual=replace(base,target_growth_pct=growth,monthly_recharge_ml=replenishment,
               grid_expansion_mw_per_year=gridexp,warming_c_by_2040=warming,
               operating_ramp_up_per_month=ramp/100)
active=variants(manual)[scenario]
monthly=simulate(active,climate=climate)
annual=annualize(monthly)

tabs=st.tabs(['Model & calibration','Live system view','Scenario experiments','Sensitivity analysis','Mechanism checks','Historical evidence','Methods & limitations','Scientific audit','External historical cross-check'])

with tabs[0]:
    st.subheader('Calibrating the model against the 2023 published benchmarks')
    col=st.columns(4)
    col[0].metric('2023 electricity estimate','32,000 GWh')
    col[1].metric('Calibrated model',f'{cal.electricity_gwh:,.0f} GWh')
    col[2].metric('2023 facility water estimate',f'{cal.target_water_ml:,.0f} ML')
    col[3].metric('Calibrated model',f'{cal.water_ml:,.0f} ML')
    st.caption(f'Baseline fit errors: electricity {cal.electricity_error_pct:+.5f}%; total water {cal.water_error_pct:+.5f}%. These are calibration errors, not test-set errors.')
    st.markdown('#### Historical reconstruction and scenario projections')
    fig,ax=plt.subplots(figsize=(10.5,4.1))
    hist=annual[annual.year<=2024]
    fut=annual[annual.year>=2025]
    ax.plot(hist.year,hist.electricity_gwh,lw=2,label=f'{scenario}: model reconstruction (2015–2024)')
    ax.plot(fut.year,fut.electricity_gwh,ls='--',lw=2,label='Scenario projection (2025–2040)')
    ax.scatter([2023],[cal.target_electricity_gwh],color='black',s=55,zorder=4,label='2023 EPRINC research estimate')
    ax.set(xlabel='Year',ylabel='Data-center facility electricity (GWh/year)')
    ax.grid(alpha=.2);ax.legend(fontsize=8)
    st.pyplot(fig);plt.close(fig)
    st.markdown('#### 2023 benchmark check for the current settings')
    y=annual.query('year == 2023').iloc[0]
    benchmark_table=pd.DataFrame([
        {'Quantity':'Facility electricity','Source estimate':cal.target_electricity_gwh,'Current model':y.electricity_gwh,'Unit':'GWh/year','Difference %':100*(y.electricity_gwh/cal.target_electricity_gwh-1)},
        {'Quantity':'Facility water (all sources)','Source estimate':cal.target_water_ml,'Current model':y.water_use_ml,'Unit':'ML/year','Difference %':100*(y.water_use_ml/cal.target_water_ml-1)},
    ])
    st.dataframe(benchmark_table,hide_index=True)
    st.warning('Fit is expected for Base case at the default settings because those two 2023 targets were used to estimate the starting capacity and water coefficient. A different scenario or edited controls may not match the targets.')
    st.download_button('Export annual model results',annual.to_csv(index=False),'v8_annual_scenario.csv','text/csv')

with tabs[1]:
    st.subheader('Watch the connected system, month by month')
    st.caption('Use the month control to advance the model. The diagram is driven by the same simulation records as the graphs, not a decorative animation.')
    index=st.slider('Simulation month',0,len(monthly)-1,120,1)
    r=monthly.iloc[index]
    st.markdown(f'#### {r.date.strftime("%B %Y")} — {scenario}')
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Facility electricity',f'{r.electricity_gwh:,.0f} GWh')
    c2.metric('Water use',f'{r.water_use_ml:,.0f} ML')
    c3.metric('Operational CO₂',f'{r.emissions_tonnes:,.0f} tonnes')
    c4.metric('Actual IT utilization',f'{100*r.actual_utilization:.1f}%')
    st.markdown('#### Connected system states')
    p1,p2,p3=st.columns(3)
    with p1:
        st.markdown('**IT facility and grid**')
        st.progress(float(min(1,max(0,r.it_capacity_mw/r.grid_capacity_mw))))
        st.caption(f'Installed IT: {r.it_capacity_mw:,.0f} MW | Grid allocation: {r.grid_capacity_mw:,.0f} MW')
        st.caption('Grid headroom limits infrastructure expansion.')
    with p2:
        st.markdown('**Illustrative shared-water buffer**')
        st.progress(float(min(1,max(0,r.reservoir_ml/active.storage_capacity_ml))))
        st.caption(f'Stored: {r.reservoir_ml:,.0f} ML of {active.storage_capacity_ml:,.0f} ML')
        st.caption(f'Replenishment: {r.recharge_ml:,.0f} ML | Freshwater withdrawn: {r.freshwater_withdrawal_ml:,.0f} ML | Reclaimed: {r.reclaimed_water_ml:,.0f} ML')
    with p3:
        st.markdown('**Environmental resource indicators**')
        stress=max(0.0,min(1.0,1-r.reservoir_ml/active.storage_capacity_ml))
        st.progress(float(stress))
        st.caption(f'Illustrative water-buffer depletion: {100*stress:.1f}%')
        st.caption('Not measured ecological damage or an ecosystem health score.')
    fig,ax=plt.subplots(figsize=(10.5,3.8))
    ax.plot(monthly.date,monthly.reservoir_ml,label='Modeled water buffer (ML)',lw=1.5)
    ax.axvline(r.date,ls='--',color='black',label='Selected month')
    ax.set(ylabel='Water buffer (ML)',xlabel='Time');ax.grid(alpha=.2);ax.legend()
    st.pyplot(fig);plt.close(fig)
    st.markdown('#### What happens when water is scarce?')
    st.write('The simulation allocates modeled community water demand first. Only the assumed freshwater fraction is deducted from the buffer; the remaining facility water is classified as reclaimed. Lower freshwater availability can limit utilization. The ratio and availability of reclaimed water are scenario assumptions, not a verified local supply model.')
    st.download_button('Export month-by-month simulation',monthly.to_csv(index=False),'monthly_simulation.csv','text/csv')

with tabs[2]:
    st.subheader('Compare controlled experiments')
    frames,table=experiment_summary(manual,climate=climate)
    pick=st.multiselect('Scenario comparisons',list(frames),default=['Base case','Drought stress','Efficient cooling'])
    option=st.selectbox('Output',['electricity_gwh','water_use_ml','reservoir_ml','emissions_tonnes','unmet_water_ml','it_capacity_mw'])
    fig,ax=plt.subplots(figsize=(10.5,4.2))
    for name in pick:
        _,a=frames[name]
        ax.plot(a.year,a[option],label=name,lw=1.9)
    ax.set(xlabel='Year',ylabel=option);ax.grid(alpha=.2)
    if pick:ax.legend()
    st.pyplot(fig);plt.close(fig)
    st.markdown('#### Numerical comparison — 2040')
    compare=table[table.year.eq(2040)].copy()
    base_row=compare[compare.scenario.eq('Base case')].iloc[0]
    for col in ['electricity_gwh','water_use_ml','co2_mt']:
        v=base_row[col]
        compare[col+'_vs_base_pct']=np.nan if v==0 else 100*(compare[col]/v-1)
    st.dataframe(compare.round(2),hide_index=True)
    st.download_button('Export experiment comparison',table.to_csv(index=False),'v8_experiments.csv','text/csv')
    st.caption('Experiments share the same calibrated starting values. Uncertainty in historical calibration and assumed physical infrastructure remains.')

with tabs[3]:
    st.subheader('One-at-a-time sensitivity analysis')
    st.write('We change one parameter at a time by ±20%, with the calibrated 2015 conditions fixed. We do not refit the model after each change.')
    sensitivity=one_at_a_time_sensitivity(base,climate=climate)
    st.dataframe(sensitivity.round(3),hide_index=True)
    st.download_button('Export sensitivity analysis',sensitivity.to_csv(index=False),'v8_sensitivity.csv','text/csv')
    st.caption('Sensitivity results reflect the defined model and input assumptions. This is not a statistical confidence interval or a probability forecast.')

with tabs[4]:
    st.subheader('Why do drought and warming change the model?')
    st.caption('These comparisons are diagnosis of model mechanisms, not measured Virginia outcomes.')
    st.markdown('#### Climate: cooling energy versus overall operations')
    diag=climate_diagnostics(manual,climate)
    st.dataframe(diag.round(3),hide_index=True)
    fig,ax=plt.subplots(figsize=(10,3.8))
    for label in diag.case.unique():
        selection=diag[diag.case.eq(label)]
        ax.plot(selection.year,selection.electricity_gwh,marker='o',label=label)
    ax.set(xlabel='Year',ylabel='Facility electricity (GWh/year)')
    ax.grid(alpha=.2);ax.legend(fontsize=8)
    st.pyplot(fig);plt.close(fig)
    st.info('When infrastructure constrains demand, added cooling overhead can reduce allowed IT activity or installed capacity. Hence warmer conditions may increase PUE and cooling water per unit of work without increasing total facility electricity. The ample-resources cases isolate the direct cooling effect and are hypothetical control experiments.')
    st.markdown('#### Drought: curtailment, recovery and community water shortage')
    d_diag=drought_diagnostics(manual,climate)
    st.dataframe(d_diag.round(2),hide_index=True)
    st.caption('Recovery is capped at the configured percentage points per month; curtailment can be immediate for safety. Cycles remain possible because recharge, community demand, and reservoir rules vary seasonally. The recovery cap is an explicit operational assumption, not a measured Virginia policy.')
    st.download_button('Export climate mechanism check',diag.to_csv(index=False),'v6_climate_diagnostics.csv','text/csv')
    st.download_button('Export drought mechanism check',d_diag.to_csv(index=False),'v6_drought_diagnostics.csv','text/csv')

with tabs[5]:
    st.subheader('Public datasets and research benchmarks')
    st.markdown('**Observed NOAA-derived statewide climate:** 2015–2025 monthly temperature and precipitation')
    st.dataframe(climate.head(15),hide_index=True)
    st.markdown('**Observed EIA electricity sales:** Virginia total, all customer sectors — not facility-only')
    st.dataframe(state_eia,hide_index=True)
    st.markdown('**Published data-center-specific research estimates:**')
    st.dataframe(load_benchmarks(),hide_index=True)
    st.markdown('**Sources**')
    st.markdown('- NOAA nClimDiv Virginia data: https://api.climatedata.dev/v1/us-climate/tavg/us-va.csv and https://api.climatedata.dev/v1/us-climate/pcpn/us-va.csv\n- EIA-861 state electricity: https://www.eia.gov/electricity/data/state/index.php\n- EPRINC Virginia data center electricity: https://eprinc.org/virginia-electricity-demand-growth-the-case-of-data-centers/\n- JLARC Virginia data centers: https://jlarc.virginia.gov/landing-2024-data-centers-in-virginia.asp')
    st.warning('Statewide temperature and precipitation are not a measured local reservoir inflow. Statewide electricity sales do not directly validate facility consumption. The 2019 derived water estimate is not held-out test data.')

with tabs[6]:
    st.subheader('Model definition and explicit assumptions')
    st.markdown('**Stocks:** installed IT capacity, grid allocation, stylized water buffer, cumulative CO₂. **Flows:** IT additions, grid allocation growth, recharge, withdrawals, CO₂ additions. **Feedback:** grid headroom restricts installed capacity; low water reduces water-dependent utilization; reopening is ramp-limited, while emergency curtailment can be immediate.')
    st.latex(r'K_{t+1}=K_t+\min(gK_t/12,\,H^{grid}_t)')
    st.latex(r'W_{t+1}=\operatorname{clip}(W_t+R_t-D^{community,served}_t-D^{freshwater}_t,0,W_{max})')
    st.latex(r'E^{facility}_t=K_t u_t h_t PUE_t/1000')
    st.latex(r'CO_{2,t}=1000\,E^{facility}_t I^{grid}_t')
    st.markdown('**Benchmarks used for calibration:** EPRINC 2023 electricity ~32,000 GWh; JLARC 2023 water ~2.1 billion US gallons. These are estimates. Model does not independently validate them.')
    st.markdown('**Explicit scenario assumptions:** grid capacity and its expansion; resource-buffer size and replenishment; community water demand; assumed freshwater share of facility water (`65%`); future warming; grid carbon factor and decarbonization; growth rate; cooling response; no explicit alternate cooling system.')
    st.caption('New recovery-rule assumption: monthly utilization can increase by no more than 6 percentage points by default. Community unmet demand is recorded when supply is insufficient. Neither assumption is a verified local operating policy.')
    st.warning('The model is not a hydrological forecast for Virginia and the depletion fraction is not a measured environmental damage index. Published benchmark fit is calibration only. Reliable historical validation requires independent facility-only annual records.')
    st.code(f'calibrated_2015_it_capacity_mw = {base.initial_capacity_mw:.3f}\ncalibrated_water_use_l_per_it_kwh = {base.water_use_l_kwh:.5f}\ncalibration_runs = {cal.iterations}',language='text')

with tabs[7]:
    st.subheader('Scientific audit — provenance, conservation, and plausibility')
    st.info('Virginia data-center electricity and water use are fitted to *one* year of published estimates (2023). The EIA sales data are statewide context, not data-center measurements. The shared-water buffer is illustrative, not an observed watershed.')
    st.markdown('#### Real EIA Virginia electric-generation CO₂ output rates (2021–2024)')
    rates=load_eia_generation_rates()
    st.dataframe(rates,hide_index=True)
    st.caption('Generation output rates, not Virginia electricity consumption mix or the marginal grid rate. Emissions before 2021 use the 2021 value as an explicitly labeled proxy. After 2024, the 2024 value changes under the user-selected annual decarbonization assumption (default 1.7%).')
    st.markdown('#### Exactly which emissions factor drives the simulation?')
    st.dataframe(annual[['year','electricity_gwh','electricity_co2_kg_kwh','emissions_tonnes']].head(26),hide_index=True)
    st.markdown('#### Internal model consistency checks')
    st.dataframe(internal_checks(monthly,active),hide_index=True)
    st.caption('Passing these checks means the equations conserve modeled flows and respect configured capacities. This does not establish historical predictive validity.')
    st.markdown('#### Plausibility context: DC reconstructed demand compared with observed statewide sales')
    state_context=historical_context(monthly,state_eia)
    st.dataframe(state_context,hide_index=True)
    st.caption('Not a calibration or validation target; these two quantities have different definitions. Future demand should not be represented as an observed Virginia electricity forecast.')
    st.markdown('#### Evidence hierarchy')
    st.markdown("""- **Observed**: NOAA-derived statewide monthly climate, EIA state-total sales, EIA in-state power-generation CO₂ rates (2021–2024).
- **Published estimates used for calibration**: EPRINC 2023 DC electricity 32 TWh and JLARC 2023 water use 2.1 billion gallons.
- **Derived assumptions**: base IT capacity, facility water intensity.
- **Scenario assumptions**: growth, water-buffer recharge/storage, grid allocation, community demand, future temperature, future decarbonization and reclaimed supply.
- **Not demonstrated**: independent annual data-center electricity/water validation, regional watershed forecasts, actual local community harm, net regional carbon footprint. """)
    st.download_button('Export scientific audit',internal_checks(monthly,active).to_csv(index=False),'scientific_audit.csv','text/csv')

with tabs[8]:
    st.subheader('External historical cross-check — Virginia Energy Plan (2026)')
    st.info('This check uses approximate values read from Figure 8 of the 2026 Virginia Energy Plan, which separates data-center electricity from other sectors. The figures are not individual metered observations and have chart-reading uncertainty. The model is still not independently validated as a site-level predictor.')
    st.markdown('**Historical growth choice:** 25%/year through 2023 (informed by the approximate 2015–2023 trajectory), followed by the selected 8%/year baseline scenario from 2024 onward. The 2015 chart value helped set this assumption and is **not held out**. 2023 electricity is fitted to EPRINC and is **not held out**.')
    checks = crosscheck(monthly)
    shown = checks[['year','dc_electricity_gwh_approx','electricity_gwh','difference_gwh','difference_pct','role','within_illustrative_chart_band']]
    st.dataframe(shown.round(2), hide_index=True)
    holdout = checks[checks.role.eq('HISTORICAL CROSS-CHECK')]
    st.metric('Mean absolute percent difference in historical chart cross-checks',f"{holdout.difference_pct.abs().mean():.1f}%")
    st.caption('The summary uses 2019, 2021, 2022 and 2024 only. Because the external estimates are approximate chart readings and share sector definitions with public data, this is an independent-source plausibility cross-check, NOT precise statistical validation. It is also limited by the selected historical growth shape.')
    fig,ax=plt.subplots(figsize=(10,4))
    ax.plot(annual[annual.year.le(2025)].year,annual[annual.year.le(2025)].electricity_gwh,label='Model reconstruction / scenario',lw=2)
    ax.errorbar(checks.year,checks.dc_electricity_gwh_approx,yerr=checks.uncertainty_gwh,fmt='o',capsize=3,label='2026 Energy Plan chart (approx. ±2 TWh visual range)')
    ax.axvline(2023,ls=':',color='gray',label='2023 electricity calibration')
    ax.set(xlabel='Year',ylabel='Annual DC electricity (GWh)'); ax.grid(alpha=.2); ax.legend(fontsize=8)
    st.pyplot(fig);plt.close(fig)
    st.markdown('Source: [Virginia Energy Plan 2026, Figure 8, p. 17](https://www.energy.virginia.gov/public/documents/Virginia%20Energy%20Plan/2026_Virginia_Energy_Plan.pdf)')
    st.warning('Do not call this a measured annual DC electricity validation series. Figure values are approximate, and the 2015 point informed our model. This check says the historical trajectory is plausible at the graph’s precision; it does not prove future behavior.')
    st.download_button('Export independent-source cross-check',checks.to_csv(index=False),'external_historical_crosscheck.csv','text/csv')
