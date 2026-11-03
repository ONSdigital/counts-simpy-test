# COUNTS SimPy Prototype

This repository contains a SimPy-based prototype for modelling household
responses to census collection activity over time.

You can use the project in two ways:

1. A local Streamlit app (`app_streamlit.py`) with interactive controls.
2. A direct Python script run (`simulation.py`) for terminal-based execution.


## What This Model Simulates

The model currently includes:

- first-day household responses,
- day-by-day response behaviour,
- SMS intervention effects,
- field officer visit effects,
- call-centre activity,
- concurrent regional populations on one shared simulation clock,
- output tracking and plotting.


## Project Structure

- `app_streamlit.py`: local UI to run scenarios and view KPIs/plot.
- `simulation.py`: script entrypoint for non-UI simulation runs.
- `functions/simulation_runner.py`: reusable run function used by the app and script.
- `parameters.py`: scenario parameter dataclass and defaults.
- `functions/`: simulation event logic modules.
- `tests/`: automated tests.
- `docs/project_reference.rst`: fuller technical reference.

Default run behavior:

- `simulation.py` and `app_streamlit.py` use `baseline_parameters` by default.
- `PoC_parameters` in `parameters.py` is kept as an example of how to
	create a modified scenario.


## First-Time Setup (VS Code)

These steps assume you already have VS Code and this repository open.

### 1. Open a terminal in VS Code

- Use Terminal -> New Terminal.

### 2. Create a virtual environment

PowerShell:

```powershell
python -m venv .venv
```

Command Prompt (cmd):

```cmd
python -m venv .venv
```

### 3. Activate the virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt (cmd):

```cmd
.venv\Scripts\activate.bat
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```


## Option A: Run the Streamlit App

Run this command in the VS Code terminal:

```bash
python -m streamlit run app_streamlit.py
```

What happens:

- Streamlit starts a local web app and shows a local URL (usually
	`http://localhost:8501`).
- Open that URL in your browser.
- Edit regional populations, officer counts and A/B/C shares in the regional table.
- Use the sidebar for the shared intervention and response settings.
- Click **Run simulation**.
- The app displays:
	- final overall return proportion,
	- final responded count,
	- final active households,
	- total call-centre calls,
	- doorstep completions,
	- a regional results table,
	- and an overall chart above named regional panels.


## Option B: Run the Python Script Directly

Run this command in the VS Code terminal:

```bash
python simulation.py
```

What happens:

- The simulation runs in the terminal and prints progress by day.
- The overall result is printed first, followed by named regional results.
- The overall-and-regions plot is displayed and also saved as `household_returns.png`.


## Local Map Data

The `LA_maps/` and `LSOA_maps/` folders contain local map datasets and are
excluded from Git. Cloning this repository does not download these datasets.
Supply them separately in those folders if you need the map visualisation,
keeping each shapefile and its companion files together.


## Changing Scenario Settings

- Default scenario values are in `parameters.py`.
- `simulation.py` and `app_streamlit.py` both use
	`baseline_parameters` as the run baseline.
- `PoC_parameters` is an example scenario object only.
- For script-based runs, edit values in `parameters.py` before running.
- For app-based runs, use the regional table and sidebar controls at runtime.

### Regions

`SimulationParameters.regions` maps region names to `RegionParameters` objects.
Each region sets its own `num_households`, `num_field_officers` and
`household_type_proportions` for A, B and C. Shares must be between 0 and 1 and
sum to 1. Household counts are allocated to whole numbers using the largest
fractional remainders, preserving the region's exact total.

The defaults include the nine English regions (North East, North West,
Yorkshire and the Humber, East Midlands, West Midlands, East of England,
London, South East and South West) plus Wales. Each starts with 10,000
households, 10 officers and equal A/B/C shares: these are illustrative values,
not real regional population estimates. Replace them with your scenario data.
For example, a small two-region scenario can be defined as:

```python
import dataclasses as dc
from parameters import RegionParameters, baseline_parameters

scenario = dc.replace(
	baseline_parameters,
	regions={
		"North East": RegionParameters(
			num_households=10000,
			num_field_officers=10,
			household_type_proportions={"A": 0.5, "B": 0.3, "C": 0.2},
		),
		"Wales": RegionParameters(
			num_households=6000,
			num_field_officers=6,
			household_type_proportions={"A": 0.2, "B": 0.3, "C": 0.5},
		),
	},
)
```

All regions run together on one SimPy clock. Each region retains internal
officer units and their daily visit limits. Zero officers disables field
visits in that region without stopping baseline responses, SMS or calls.
Empty regions are also supported. The call centre and paper questionnaire
stock are shared across every region; `initial_paper_batch` is a single total,
not a per-region allocation. Other intervention settings remain shared.

Reports show the overall result first, then each named region, not individual
officer units. Overall rates are weighted by active household counts, rather
than averaging regional percentages. In code, use `result.regions` and each
region's `name`, `households` and `return_history`. `result.units` remains an
internal lower-level view.

### Daily Field Visits

`daily_field_visits` sets the maximum visits completed per officer each day
(default 30). All visits happen at the same simulated time on each day from
`field_first_day` through `field_last_day`, inclusive. There is no visit duration
or spillover into later days. Fewer visits occur when fewer households are
eligible; revisit waiting periods still apply. Set the value to 0 to disable
visits. This replaces `field_visit_duration` and `field_daily_queue_size`.

### Daily Response Probabilities

`daily_response_probabilities_by_group` supplies exactly 50 baseline
probabilities for each of `A`, `B` and `C`. Values must be between 0 and 1.
Index 0 is day 1, index 49 is day 50. For example:

```python
daily_response_probabilities_by_group={
	"A": [0.05, 0.04] + [0.03] * 48,
	"B": [0.08, 0.06] + [0.04] * 48,
	"C": [0.03, 0.02] + [0.01] * 48,
}
```

The defaults are a flat 0.05 for every group and day. There is no automatic
daily decay. Interventions never modify the baseline table or add to daily
response probabilities. Instead, SMS makes one response attempt per eligible
household with probability `sms_response_probability` (default 0.3). Eligible
field visits make one response attempt with probability
`field_visit_response_probability_if_answer` (default 0.5) when there is no
doorstep completion or paper order, or
`field_visit_response_probability_if_no_answer` (default 0.2) when there is no
answer and the household is not vacant. Each attempt either records an
immediate return or has no lasting effect; a later visit can make a new attempt.
Already-responded or refusing households cannot respond through these attempts.
Paper-first households cannot respond through SMS, these field attempts, or
ordinary daily returns until paper arrives. Doorstep completion and paper
ordering remain separate field outcomes. The time-zero response uses the
first value in the household's group table, with no separate first-day setting.
The timing and indexing of subsequent daily draws are unchanged. Runs beyond day 50
retain the day-50 baseline. In the app, edit the 50-row table in the sidebar.


## Troubleshooting

- If `python` is not recognized, install Python and reopen VS Code.
- If package install fails, confirm the virtual environment is activated.
- If Streamlit does not open automatically, copy the localhost URL from the
	terminal into your browser.


## Documentation

For a fuller reference, see `docs/project_reference.rst`.
