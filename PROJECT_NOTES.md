# Model implementation notes

## Scope
The model studies interactions between facility growth, electricity capacity, and water availability in a hypothetical Virginia resource system. It does **not** represent a measured county reservoir or power interconnection. The monthly time step was chosen to keep seasonal water availability visible.

## Where the calculations happen
- `model.py`: `Settings` holds the experiment inputs and `simulate` advances the stocks month by month. `annualize` sums flows and retains year-end stocks.
- `calibration.py`: adjusts the initial IT capacity and water intensity to match two published 2023 estimates. The fit is not an independent validation.
- `data_sources.py`, `benchmarks.py`, `emissions_data.py`, `external_evidence.py`: load and identify input evidence.
- `diagnostics.py`, `science_audit.py`: compare modeled behaviors and check internal constraints.
- `app.py`: runs the interface and scenario comparisons; it does not contain a separate simulation model.

## Main feedback mechanisms
1. IT growth raises electricity needs, and remaining grid capacity limits further additions.
2. The facility uses an assumed freshwater share; falling water storage reduces allowed utilization.
3. The facility can cut utilization quickly during shortages but ramps back up gradually.
4. Weather changes cooling overhead, which alters facility electricity and water requirements.

## Evidence limitations
Observed climate and state-total energy data are separate from the hypothetical local water buffer. The 2023 electricity and water figures are published estimates used for calibration. The Virginia Energy Plan chart values provide an approximate historical plausibility check. They should not be called metered site-level observations or a fully independent validation dataset. EIA in-state generation carbon rates are a proxy, not a data-center-specific marginal emissions factor.

## Reproducibility
Create a fresh virtual environment, install `requirements.txt`, run `python -m pytest -q`, then `python -m streamlit run app.py`. The `data/` CSV files are required inputs.
