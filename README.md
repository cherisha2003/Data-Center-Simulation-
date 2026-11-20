# Virginia Data Center Systems Simulation

## Run on macOS

Unzip into `~/Desktop/Virginia_DataCenter_Simulation_v8`. In Terminal:

```bash
cd ~/Desktop/Virginia_DataCenter_Simulation_v8
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --no-cache-dir -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. Do not include `.venv` or Python caches in the submitted ZIP.

## What's new

The same monthly stock-flow engine now calibrates its *2015 IT capacity* and its *total-water-use coefficient* using **published 2023 Virginia data-center electricity and water estimates**. The calibration runs the actual simulation rather than constructing an unrelated exponential plot. It uses EPRINC electricity 32,000 GWh and JLARC water use 2.1 billion US gallons (7,949 ML). The calibrated baseline is about 1,677 MW in 2015 and about 0.337 L/kWh of IT energy. It fits these targets, by construction; this is NOT independent validation.

Model experiments share initial calibrated settings. Scenario controls run without refitting the benchmark unless the app restarts a baseline calibration for its default settings. The app includes a live month scrubber, model-driven resource state display, scenario comparison and one-at-a-time sensitivity analysis.


## Model and data limitations

Only 2023 facility electricity and total facility water estimates are calibration targets; this is not a verified annual historical facility-only time series. The water buffer and community demand are an *illustrative shared resource*, not a hydrologic representation of a single Virginia locality. Future climate parameters are hypothetical; published data center growth projections should be used to contextualize the aggressive 2040 outcome. This prototype is suitable for controlled scenario analysis, not a point forecast of actual 2040 Virginia demand.

## Datasets

- `data/virginia_noaa_climate_2015_2025.csv`: genuine Virginia statewide NOAA-derived temperature and precipitation observations. Used as forcing for 2015–2024. Beyond this period, weather is a scenario assumption.
- `data/virginia_eia_state_total_sales.csv`: observed Virginia-wide electricity sales across sectors, used as state context only; not direct data-center measurement.
- `data/published_dc_benchmarks.csv`: two 2023 data-center estimates used for calibration and a derived 2019 entry **not used for validation**.

## Model assumptions to state in presentation

The model is a *regional thought experiment* constrained by real statewide climate and source-tracked data-center benchmarks. Its water buffer, replenishment, community water demand, and grid allocation are not measured Virginia totals or a geographically coherent reservoir. The assumed baseline storage is 28,000 ML (capacity 40,000 ML), inflow 2,600 ML/month and non-data-center demand 1,150 ML/month; these are exploratory parameters. Carbon intensity is a scenario assumption, not calibrated to observed marginal electricity emissions. The water metric calibrated to JLARC refers to total facility water use (including reclaimed sources), not solely freshwater withdrawals. For the water buffer only, the model assumes 65% of facility water comes from freshwater and 35% is reclaimed. This split is NOT measured Virginia supply composition. This distinction is essential: the modeled water buffer is a sensitivity mechanism, not an accurate reconstruction of a local watershed. Avoid claiming that the model predicts actual Virginia reservoir depletion, ecosystem damage, or 2040 emissions with known precision.

The starting installed IT capacity and water-use intensity are fitted estimates, not direct facility observations. All historical simulated output other than source benchmarks is reconstructed, not observed. The fit should not be called an out-of-sample validation.

## Useful source links

- EPRINC electricity estimate: https://eprinc.org/virginia-electricity-demand-growth-the-case-of-data-centers/
- JLARC data-center report: https://jlarc.virginia.gov/landing-2024-data-centers-in-virginia.asp
- EIA state electricity: https://www.eia.gov/electricity/data/state/index.php
- NOAA nClimDiv mirror: https://api.climatedata.dev/v1/us-climate/tavg/us-va.csv

## Tests

```bash
python -m pytest -q
```

## Project scope

This is a calibrated *prototype* suitable for experimenting and explaining feedback, but not yet an independently historically validated hydrological/energy prediction. Before a final scientific claim, use independent facility-level time series or calibrate to more than one year with genuinely separate held-out evidence, and document the physical scope and parameter uncertainty.


## V7 scientific strengthening (2026-11-20)

- Added **Scientific audit** dashboard: monthly water-stock conservation, emissions mass/unit check, grid operating limit, freshwater vs reclaimed balance, climate-data coverage, EIA context ratio.
- Replaced the assumed **historical CO₂ intensity for 2021–2024** with actual EIA Virginia **in-state electricity-generation CO₂ output rates**: 649, 642, 594, 631 lb CO₂/MWh. Converts to kg/kWh with `1 lb / MWh = 0.00045359237 kg/kWh`. (These are not the electricity consumption mix or marginal emissions.)
- For 2015–2020, the model deliberately labels the **2021 emissions rate as a proxy**, not a year-specific observation. For 2025–2040, rates extrapolate from 2024 using the assumption `grid_cleaning_pct`. This is NOT an empirically fitted grid forecast.
- **Geographic limitation:** 2023 DC energy and water benchmarks are Virginia-wide; the 40,000 ML buffer and 8,000 MW allocation represent hypothetical shared-resource infrastructure. Do not describe the water-buffer projections as water levels for a real Virginia locality or claim measured ecological damage.
- 2023 electricity and water values are **calibration targets**, not held-out validation. The EIA statewide electricity series remains a context benchmark, not a DC-only time series.
- Default assumptions are exploratory. The model tests feedback and numerical consistency, not the future state of Virginia water supplies.
- Independent yearly DC electricity and water records and a geo-matched hydrology dataset would be needed for predictive validation.

### Additional source URLs

- EIA 2024 Virginia electricity profile: https://www.eia.gov/electricity/state/virginia/
- EIA 2023: https://www.eia.gov/electricity/state/archive/2023/virginia/
- EIA 2022: https://www.eia.gov/electricity/state/archive/2022/virginia/
- EIA 2021: https://www.eia.gov/electricity/state/archive/2021/virginia/
- EIA state data files: https://www.eia.gov/electricity/data/state/index.php


## V8: historical cross-check and final runnable code (Nov. 20, 2026)

**Why this changed:** Using only the 8% forward growth rate to backcast 2015–2024 overstated early data-center electricity. The state's **2026 Virginia Energy Plan Figure 8** reports an approximate historical data-center segment. We now distinguish:

- `historical_growth_pct=25.0` for 2015–2023, informed by the approximate early-to-2023 trajectory in the state chart (a model-development decision, **not** independently measured annual DC growth).
- `target_growth_pct=8.0` baseline for 2024 onward, an explicitly hypothetical *scenario* rate (not a 2024 observation or utility forecast).
- Actual calendar years 2025 and 2026 have passed/partially passed by this project's date. Simulations after 2024 are **scenario reconstructions/projections**, not observed 2025–2026 data or real-time forecasts.

Historical electricity is still calibrated to **EPRINC's 2023 32 TWh estimate**. The model is not refitted to the held-out **2019, 2021, 2022, and 2024** approximate values from the 2026 Virginia Energy Plan Figure 8. The 2015 chart value is **not** held out because the 25% historical-growth setting was chosen with that endpoint in mind. The external chart values are *visual readings*, not a machine-readable meter dataset; the indicated ±2 TWh interval is only a conservative illustrative graph-reading tolerance, **not a statistical confidence interval**. 2023 itself is not a held-out validation year. The 2025 model value may differ considerably from the approximate 2025 chart and is not fitted; it is a retrospective scenario result.

**UI:** `External historical cross-check` tab plots the historical reconstruction alongside approximate state-published values, shows percent differences and distinguishes model-development vs cross-check years. Use it to explain both successes *and* limitations during Q&A.

**Scientific limitations remain:** Statewide climate input cannot physically determine water availability in an invented local buffer without hydrological calibration. EIA in-state generation rates are not consumed-electricity carbon rates. EPRINC 2023 and JLARC 2023 figures are estimates; the modeled local grid and water infrastructure are stylized. Do not claim exact site-specific water depletion, local ecosystem harm, or verified 2040 projections. Historical cross-checks are approximate and do not prove independent predictive validity.

**Final code-only acceptance test:** Run `python -m pytest -q`, then start `python -m streamlit run app.py`. Confirm 2023 electricity/water targets, historical cross-check tab, drought scenario, sensitivity analysis, and exports. PPT/report and student-facing live-demo rehearsal are separate graded deliverables and are not in this ZIP.
