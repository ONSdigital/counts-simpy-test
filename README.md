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
- output tracking and plotting.


## Project Structure

- `app_streamlit.py`: local UI to run scenarios and view KPIs/plot.
- `simulation.py`: script entrypoint for non-UI simulation runs.
- `simulation_runner.py`: reusable run function used by the app.
- `parameters.py`: scenario parameter dataclass and defaults.
- `functions/`: simulation event logic modules.
- `tests/`: automated tests.
- `docs/project_reference.rst`: fuller technical reference.

Default run behavior:

- `simulation.py` and `app_streamlit.py` use `baseline_parameters` by default.
- `new_scenario_parameters` in `parameters.py` is kept as an example of how to
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
- Use the sidebar to adjust parameters.
- Click **Run simulation**.
- The app displays:
	- final overall return proportion,
	- final responded count,
	- final active households,
	- total call-centre calls,
	- doorstep completions,
	- and a generated plot image.


## Option B: Run the Python Script Directly

Run this command in the VS Code terminal:

```bash
python simulation.py
```

What happens:

- The simulation runs in the terminal and prints progress by day.
- Final per-unit return proportions are printed.
- A plot is generated and saved as `household_returns.png`.


## Local Map Data

The `LA_maps/` and `LSOA_maps/` folders contain local map datasets and are
excluded from Git. Cloning this repository does not download these datasets.
Supply them separately in those folders if you need the map visualisation,
keeping each shapefile and its companion files together.


## Changing Scenario Settings

- Default scenario values are in `parameters.py`.
- `simulation.py` and `app_streamlit.py` both use
	`baseline_parameters` as the run baseline.
- `new_scenario_parameters` is an example scenario object only.
- For script-based runs, edit values in `parameters.py` before running.
- For app-based runs, use the sidebar controls at runtime.


## Troubleshooting

- If `python` is not recognized, install Python and reopen VS Code.
- If package install fails, confirm the virtual environment is activated.
- If Streamlit does not open automatically, copy the localhost URL from the
	terminal into your browser.


## Documentation

For a fuller reference, see `docs/project_reference.rst`.
