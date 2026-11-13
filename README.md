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
- Monte Carlo repeats with mean outcomes and central 95% run intervals,
- output tracking and plotting.


## Project Structure

- `app_streamlit.py`: local UI to run scenarios and view KPIs/plot.
- `simulation.py`: script entrypoint for non-UI simulation runs.
- `functions/simulation_runner.py`: reusable run function used by the app and script.
- `parameters.py`: scenario parameter dataclass and defaults.
- `functions/`: simulation event logic modules.
- `tests/`: automated tests.
- `docs/project_reference.rst`: fuller technical reference.
- [Model setup and running flowchart](docs/model_setup_and_running_flowchart.md):
  regional officer areas, household allocation, simulation runs and Monte Carlo summaries.

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
	- mean overall return proportion and response counts,
	- mean active households, call-centre calls and doorstep completions,
	- an overall table with mean, 95% lower and 95% upper columns,
	- a regional results table with mean return rates and 95% intervals,
	- and mean curves with uncertainty bands, overall above named regional panels.


## Option B: Run the Python Script Directly

Run this command in the VS Code terminal:

```bash
python simulation.py
```

What happens:

- The simulation prints progress by repeat and day.
- The overall mean/95% interval table is printed first, followed by regional summaries.
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

### Simulation Weekdays

`census_start_weekday` sets the weekday at simulation time 0 (default `"Monday"`).
Set it in `parameters.py` or use the app's **Census starting weekday (day 0)**
control. Day 1 is the following weekday; fractional times stay within their
whole day, so time 6.9 is Sunday and time 7 is Monday with the default start.

Use `params.weekday_at(env.now)` inside simulation processes, or
`result.params.weekday_at(day)` after a run, to look up any simulation time.
Single-run unit, regional, aggregate and call-centre histories include a
`weekday` list aligned with `time`. Monte Carlo aggregate, regional and
call-centre histories retain these weekday labels. Progress messages also show
the weekday. Field visits use this calendar to select weekday or weekend
working slots. Other response and intervention processes retain their timing.

### Monte Carlo Repeats

`monte_carlo_repeats` is a positive integer controlling how many independent
runs the app or script performs (default 1). Set it in `parameters.py` or use
the app's **Monte Carlo repeats** control. Each repeat starts a fresh model,
including household states, clock, call centre and shared paper stock.
Distinct seeds are derived reproducibly from the scenario's starting `seed`.
Unit random generators use the run seed plus their unit ID. The call centre
uses the run seed plus the maximum unit ID plus one, avoiding unit-seed
collisions even with more than 10,000 units. Repeat seed spacing keeps these
integer seed ranges separate across runs. This replaces the previous fixed
call-centre offset of 10,000, so exact seeded call outcomes can change.
Regional demographic shuffling uses a separate labelled seed,
`f"{run_seed}:{region_name}:group_shuffle"`, rather than reusing the first
unit's seed. It remains reproducible without reserving another numeric offset.
This changes seeded group placement and can change subsequent outcomes,
but preserves each region's group totals.
Repeats run sequentially; regions within each repeat share one clock.

The overall table reports the mean and the 2.5th/97.5th percentiles of each
final outcome across runs. This is a central empirical **95% run interval**,
not a confidence interval for the mean. Means and percentile limits for counts
can be fractional. With one repeat, both limits equal that run's result and
cannot estimate variation. Small repeat counts give unstable tail estimates;
use more repeats (for example 100 or more) for more reliable percentiles.
Runtime grows approximately with the number of repeats.

Plots retain the existing daily timestamps and intervention markers. Lines
show mean return rates; shaded bands show pointwise 95% run intervals, not a
simultaneous interval for the whole curve. Each run's overall rate is weighted
by active households before rates are averaged across runs.

For direct API use, `run_simulation()` remains a single-run building block.
Use `run_monte_carlo()` for repeated runs:

```python
import dataclasses as dc
from parameters import baseline_parameters
from functions.simulation_runner import run_monte_carlo

params = dc.replace(baseline_parameters, monte_carlo_repeats=100)
result = run_monte_carlo(params, generate_plot=False)
print(result.overall_summary["proportion_returned"])
```

The repeated-run result exposes `overall_summary`, `region_summaries`,
mean `aggregate_history`, named mean `region_histories`, mean
`call_centre_history` and `run_seeds`. Household objects are not retained for
every repeat, keeping memory use lower.

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
than averaging regional percentages. Single-run results expose `result.regions`
and each region's `name`, `households` and `return_history`; `result.units`
remains an internal lower-level view. Monte Carlo results instead expose
`region_summaries` and `region_histories` keyed by region name.

### Field Visit Slots

#### Simple and detailed field modes

`field_visit_mode` selects `"simple"` (the default) or `"detailed"`.
Use the **Field visit mode** selector in Streamlit or change the parameter for
script/API runs. Results retain the mode in `result.params`; app and script
report it alongside results. Both modes use the same queues, officer hours,
time slots, visit records and revisit delays. Refusing households are excluded
from field visits in **both** modes.

Simple mode uses one mutually exclusive draw per knock:

| Outcome | Parameter | Default |
|---------|-----------|---------|
| Doorstep completion | `field_doorstep_completion_probability` | 0.5 |
| Refusal | `refusal_probability` | 0.01 |
| Vacancy | `field_vacancy_probability` | 0.05 |
| Ordinary success | `field_success_probability_by_slot` | 0.3 in every slot |
| No outcome | Remaining probability | 0.14 |

These are unconditional probabilities, not sequential conditional draws.
The four configured probabilities must sum to at most 1 **in every slot**.
Increasing doorstep completion therefore requires leaving sufficient probability
for the other outcomes. Doorstep completion always returns the household,
including paper-first households and those already awaiting paper.
While awaiting paper, all non-doorstep draws become no outcome: no refusal,
vacancy, success or duplicate paper order is possible.

Refusal sets `refusal=True` and prevents future field visits. Vacancy removes
the household from the active population and intervention lists.
An ordinary success immediately returns a non-paper-first household.
For a paper-first household it instead orders a questionnaire through the shared
paper service, consuming stock and using postal plus any out-of-stock printing
delay. On delivery it immediately returns the household, provided it is still
active, has not refused and has not already responded. Only paper ordered via
simple-mode field success gains this immediate response-on-delivery behaviour;
contact-centre and detailed-mode paper orders retain their existing behaviour.
Unsuccessful visits and paper orders use `field_days_until_next_visit`.

`simple_field_successes` counts ordinary successes resulting in a response,
including completed paper deliveries, **not** pending orders or doorstep
completions. Each household stores its count; overall and regional Monte Carlo
summaries report the mean and run interval separately from `doorstep_completions`.

Detailed mode retains the original door-answer decision tree, including
conditional doorstep completion, paper orders, vacancy on no answer and
one-off response attempts. Its door-answer and response-after-answer slot
probabilities, and `field_visit_response_probability_if_no_answer` and
`field_vacancy_probability_if_no_answer`, do not control simple-mode outcomes.
Conversely, simple refusal, vacancy and success probabilities do not control
detailed outcomes. Switching to detailed does not enforce the simple-mode
probability-sum constraint.

#### Shared slot scheduling

`field_officer_working_hours_by_slot` sets hours **per officer per day**:

| Slot | Days used | Default hours |
|------|-----------|---------------|
| `morning` | Monday-Friday | 3 |
| `afternoon` | Monday-Friday | 3 |
| `evening` | Monday-Friday | 2 |
| `weekend` | Saturday and Sunday | 8 on each day |

Each slot's capacity is `floor(hours * field_officer_visits_per_hour)`.
The shared visit rate defaults to 3.75 per hour. Fractional visits are discarded
separately per slot, not pooled: defaults allow 11 morning, 11 afternoon and
7 evening visits (29 per weekday), or 30 per weekend day. Zero hours disables
a slot; all-zero hours disables visits. The visit rate must be finite and positive.
Hours must be finite and non-negative, and all four slot keys are required.

In **detailed mode**, two independent probability dictionaries also require all four slot keys:

- `field_answer_door_probability_by_slot`: chance the door is answered.
- `field_visit_response_probability_if_answer_by_slot`: chance of an immediate
  response after answering, when there is no doorstep completion or paper order.

Both default to **0.3 in every slot** and accept values from 0 to 1.
The response-after-answer default was previously 0.5. Doorstep completion and
the no-answer response chance remain separate parameters in detailed mode.
Edit hours and both probabilities for each slot in the Streamlit sidebar.

All slots still happen at the same simulated timestamp on each day from
`field_first_day` through `field_last_day`, inclusive. Eligible households are
assigned in list order to morning, then afternoon, then evening on weekdays;
only the weekend slot is used on Saturday/Sunday. Each household is selected
at most once per day, even with a zero revisit delay. Fewer visits occur when
fewer households are eligible. There is no elapsed visit duration, unused
capacity carry-over or spillover into later days; revisit waiting periods apply.

Single-run results expose each officer unit's `field_visit_history`, containing
`time`, `household_id` and `slot` for every visit actually performed.
For example, `result.units[0].field_visit_history` shows the first officer's
visits. `result.params.weekday_at(visit["time"])` gives a visit's weekday.
Monte Carlo overall and regional summaries include `field_visits_morning`,
`field_visits_afternoon`, `field_visits_evening` and `field_visits_weekend`.
The overall results table also reports those slot totals.

These settings replace `field_officer_working_hours_per_day`,
`daily_field_visits`, `field_answer_door_probability` and
`field_visit_response_probability_if_answer`; configure the slot dictionaries
instead of passing those old arguments to `SimulationParameters`.

### Reminder Letters

`reminder_letter_days`, under fixed parameters, lists the days on which letters
are posted (default `[10, 20, 30]`). An empty list disables reminders. Days must
be unique non-negative integers; they are processed chronologically.
The Streamlit sidebar provides sending-day and response-probability controls.
Overall and regional graphs mark each configured sending day with a purple
dashed line labelled **Reminder letters sent**. Markers use sending days,
not delivery days, and do not include the postal delay.

On each sending day at `day + 0.85` (the same daily offset as SMS), every active,
non-responded household is sent one reminder, including paper-first and refusing
households. Delivery occurs after `pQ_postal_delay`, with **no printing delay**
and no use of paper questionnaire stock. Integer postal delays preserve the
0.85 daily delivery offset. Sending does not block or defer field visits, SMS,
other letters or paper questionnaire orders, so a household can be visited and
receive a reminder on the same day.

At delivery, an active household that has not responded and is neither
paper-first nor refusing gets one response attempt with
`reminder_letter_response_probability` (default 0.4). Success marks it responded
and removes it from open-household and intervention lists. Eligibility is checked
again at delivery; letters already posted remain counted if a household responds
or is marked vacant in transit. Failed attempts do not change baseline response
probabilities. Each subsequent letter can make another attempt.

Single-run units expose `reminder_letter_history`: mailing `time`, aligned
`letters_sent` counts, `total_letters_sent`, `letters_delivered` (to active
households), and successful `responses`. Counts cover events before the run
horizon; a posted letter can still be in transit at the end of the run.
Monte Carlo overall and regional summaries expose `total_letters_sent`,
`letters_delivered` and `reminder_letter_responses`, also shown in the overall
results table in both the app and script.

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
household on each configured sending day with probability
`sms_response_probability` (default 0.3). Set `sms_days`, for example
`[10, 20, 30]`, just like `reminder_letter_days`. The default is `[20]`;
an empty list disables SMS. Days must be unique non-negative integers and are
scheduled chronologically at `day + 0.85`. The app supports multiple selections
and plots mark every sending day. Eligible non-respondents can receive SMS on
later scheduled days; successful respondents are removed immediately. Eligible
field visits make one response attempt with probability
`field_visit_response_probability_if_answer_by_slot` (default 0.3 per slot) when there is no
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


Contact-centre calls are restricted to active, outstanding, non-refusing
households that require paper and are not already awaiting a questionnaire.
Refusal prevents future calls; paper ordered before refusal can still arrive.

## Running Tests

With the virtual environment activated, run:

```powershell
python -m pytest
```

Tests use Matplotlib's non-interactive `Agg` backend to save and check plots
without opening GUI windows or requiring Tk. This test-only configuration does
not change interactive plotting when running the simulation script.


## Troubleshooting

- If `python` is not recognized, install Python and reopen VS Code.
- If package install fails, confirm the virtual environment is activated.
- If Streamlit does not open automatically, copy the localhost URL from the
	terminal into your browser.


## Documentation

For a day-by-day guide without pseudocode, see the
[plain-English household journey](docs/household_journey_plain_english.md).

For SMS selection, contact and list removal, see the
[SMS intervention flowchart](docs/sms_intervention_flowchart.md).

For questionnaire requests, paper-first households, deliveries and reminder
letters, see the [paper products flowchart](docs/paper_products_flowchart.md).

SMS uses one central national list and one intervention process per run.
All response routes remove respondents from this shared list immediately.
Officer units retain references to it for removal, not separate SMS queues.
Regional reporting is unchanged. A dedicated reproducible SMS random stream
means individual outcomes can differ from earlier per-unit SMS runs with the
same starting seed. Each Monte Carlo repeat starts a fresh national SMS list.

For a fuller reference, see `docs/project_reference.rst`.
