"""Cross-check a reconstructed trajectory against published *approximate* chart values.

These are visual readings of Virginia Energy Plan 2026 Fig. 8; not raw utility
meter observations and not an independent high-precision validation dataset.
The 2015 estimate informed the 25% historical-growth setting and is excluded
from any held-out summaries. EPRINC 2023 remains the electricity fit target.
"""
from pathlib import Path
import pandas as pd
from model import annualize

PATH = Path(__file__).resolve().parent/'data'/'virginia_energy_plan_dc_electricity_approx.csv'

def load_external():
    return pd.read_csv(PATH)

def crosscheck(monthly):
    annual = annualize(monthly)[['year','electricity_gwh']]
    external = load_external()
    result = external.merge(annual, on='year', how='left',validate='one_to_one')
    result['difference_gwh'] = result['electricity_gwh'] - result['dc_electricity_gwh_approx']
    result['difference_pct'] = 100 * result['difference_gwh'] / result['dc_electricity_gwh_approx']
    result['within_illustrative_chart_band'] = result['difference_gwh'].abs() <= result['uncertainty_gwh']
    return result
