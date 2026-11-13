Project Reference
=================

Overview
--------

``counts-simpy-test`` is a small SimPy-based prototype for modelling how households
respond to census collection activity over time. The model combines:

* a household population with response-related attributes,
* background day-by-day response behaviour,
* intervention channels such as SMS and field visits, and
* output helpers for tracking and plotting returns.

The current repository is structured as a lightweight simulation entrypoint plus a
set of modules under ``functions/`` that hold the event logic.


Repository Layout
-----------------

::

   counts-simpy-test/
   ├── Archive/
   │   └── Census structure idea.ipynb
   ├── docs/
   │   └── project_reference.rst
   ├── app_streamlit.py
   ├── function_core.py
   ├── functions/
   │   ├── functions_contact_centre.py
   │   ├── functions_field.py
   │   ├── functions_households.py
   │   ├── functions_output.py
   │   ├── functions_sms.py
   │   └── intervention_lists.py
   ├── simulation_runner.py
   ├── simulation_types.py
   ├── tests/
   │   ├── test_SMS_functions.py
   │   ├── test_call_centre_functions.py
   │   ├── test_field_functions.py
   │   └── test_household_functions.py
   ├── parameters.py
   ├── README.md
   ├── requirements.txt
   └── simulation.py


Key Files
---------

``simulation.py``
   Main entrypoint. Builds the environment, constructs households, wires up the
   event processes, runs the simulation, and triggers plotting.

``app_streamlit.py``
   Local Streamlit interface for running scenarios with interactive controls and
   displaying KPI outputs plus a generated plot image.

``simulation_runner.py``
   Reusable API-style runner used by the Streamlit app to execute the simulation
   and return structured results.

``parameters.py``
   Holds the ``SimulationParameters`` dataclass and example parameter sets used by
   the simulation.

``functions/``
   Contains the simulation rules grouped by concern: household behaviour, SMS,
   field operations, output collection, and intervention list containers.

``tests/``
   Contains automated tests. At present the test suite is limited and focuses on
   SMS behaviour.

``Archive/``
   Holds exploratory notebook material and is not part of the runtime path.


How The Simulation Works
------------------------

The model runs on a SimPy environment. A typical run follows this high-level flow:

1. A reproducible random number generator is created from the configured seed.
2. ``Household`` objects are created and assigned initial attributes.
3. Intervention lists and field-officer resources are created.
4. Processes are scheduled for:

   * first-day responses,
   * daily household response updates,
   * SMS list population and per-sending-day SMS response attempts,
   * field-officer list population and visit scheduling,
   * response-history collection for plotting.

5. The environment runs until the configured stop time.
6. A return-rate plot is produced after the simulation finishes.


Running The Simulation
----------------------

Prerequisites
~~~~~~~~~~~~~

* Python 3.12 or another version compatible with the dependencies in
   ``requirements.txt``.
* VS Code with this repository opened.
* Access to a package index that provides the required libraries.

Setup
~~~~~

In a VS Code terminal, create and activate a virtual environment.

On Windows PowerShell:

.. code-block:: powershell

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt

On Windows Command Prompt (cmd):

.. code-block:: cmd

   python -m venv .venv
   .venv\Scripts\activate.bat
   python -m pip install -r requirements.txt


Run via Streamlit app
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: powershell

   python -m streamlit run app_streamlit.py

What to expect:

* Streamlit starts locally and prints a localhost URL (typically
  ``http://localhost:8501``).
* In the browser app, set scenario inputs in the sidebar and click
  **Run simulation**.
* The app shows KPI metrics (including doorstep completions) and a generated
  returns plot image.


Run via simulation script
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: powershell

   python simulation.py

What to expect
~~~~~~~~~~~~~~

* Console output with progress updates, the overall result, then named regional results.
* A matplotlib chart saved to ``household_returns.png`` showing:

  * overall household return proportion over time,
  * one line per demographic group,
   * named regional panels below the overall chart,
   * intervention timing markers for SMS, field operation start day and
     reminder-letter sending days (not delivery days).


Configuration
-------------

Simulation settings are defined in ``parameters.py``. Both the main script
and Streamlit app use ``baseline_parameters`` and the same simulation runner.

``PoC_parameters`` is kept in ``parameters.py`` as an example of creating
a modified scenario with ``dataclasses.replace``.

To change the scenario, either:

* edit the values in ``baseline_parameters`` (by changing defaults in
   ``SimulationParameters``), or
* define another ``SimulationParameters`` instance and update the import in
  ``simulation.py``.

Important parameters include:

``field_visit_mode``
   ``"simple"`` by default; ``"detailed"`` restores the original door-answer
   decision tree. Both share visit queues, slot capacity, history and revisit
   delays. Refusing households are excluded from visits in both modes.
   The mode is retained in result parameters and shown in app/script reporting.

``field_success_probability_by_slot``
   Simple-mode ordinary success probabilities for morning, afternoon, evening
   and weekend (default 0.3 each). One draw selects doorstep completion,
   refusal, vacancy, ordinary success, or no outcome. Together with
   ``field_doorstep_completion_probability``, ``refusal_probability`` (0.01)
   and ``field_vacancy_probability`` (0.05), each slot's total must be at most 1.
   All probabilities must be finite and in [0, 1].

   Doorstep completion always responds, including for paper-first households
   awaiting paper. While awaiting paper, every other draw gives no outcome.
   Ordinary success responds immediately unless the household is paper-first;
   in that case it orders shared-stock paper with normal postal/printing delays
   and responds immediately on delivery, if still active, non-refusing and
   non-responded. This delivery behaviour is exclusive to simple-mode field
   success orders; other paper orders are unchanged.

   Refusal sets the permanent household refusal flag and removes it from the
   field list. Vacancy uses the existing population/list removal.
   No outcome and paper orders defer visits by ``field_days_until_next_visit``.
   Household ``simple_field_successes`` counts ordinary immediate or delivered
   responses, separately from ``doorstep_completions`` and not pending orders.
   Overall and regional Monte Carlo summaries include means and run intervals
   for this count.

``census_start_weekday``
   Weekday name at simulation time 0, from ``"Monday"`` to ``"Sunday"``
   (default ``"Monday"``). Day 1 is the following weekday. Weekdays advance at
   integer day boundaries and repeat every seven days; fractional times use
   their containing day. The Streamlit sidebar exposes this setting.
   ``params.weekday_at(env.now)`` provides the weekday during a process, and
   ``result.params.weekday_at(day)`` provides it after a run.
   Returned unit, regional, aggregate and call-centre histories include a
   ``weekday`` list aligned with ``time``. Repeated-run histories retain these
   labels, and progress messages include weekdays. The calendar selects
   weekday or weekend field slots; other processes retain their timing.

``monte_carlo_repeats``
   Positive integer number of independent runs (default 1). The app and script
   report means and central 95% intervals using the 2.5th/97.5th percentiles
   across runs. This measures run-to-run variation, not confidence in the mean.
   One repeat gives a zero-width interval; small counts give unstable tails.
   Each repeat gets a distinct reproducible seed and fresh model/service state.
   Unit generators use the run seed plus unit ID; the call centre uses the run
   seed plus the maximum unit ID plus one. Repeat seed spacing keeps these
   integer ranges separate across runs. The call-centre offset is no longer
   fixed at 10,000, so exact seeded call outcomes can differ from earlier runs.
   Regional group shuffling uses ``f"{run_seed}:{region_name}:group_shuffle"``,
   separate from the first unit's seed and without another numeric offset.
   This changes seeded group placement and potentially later outcomes, while
   preserving regional group totals and reproducibility.

``regions``
   Region-name mapping to ``RegionParameters``. Each region specifies its own
   ``num_households``, ``num_field_officers`` and A/B/C
   ``household_type_proportions``. Population shares must sum to 1; counts are
   rounded using largest fractional remainders while preserving regional totals.
   Defaults cover nine English regions plus Wales using illustrative populations.
   All regions share one clock, call centre and paper questionnaire stock.
   Zero officers disables regional field visits; zero households is allowed.

``daily_response_probabilities_by_group``
   A dictionary containing 50 daily baseline probabilities for each of A, B
   and C. Index 0 is day 1 and index 49 is day 50. Longer runs retain the last
   value. There is no automatic decay; interventions make separate one-off
   response attempts without changing the table. Defaults are 0.05 for all groups and days.
   Each group's first value also sets its time-zero response probability.

``sms_days``
   List of unique non-negative integer sending days (default ``[20]``).
   An empty list disables SMS. Days are sorted for scheduling at ``day + 0.85``,
   matching reminder-letter sending. Eligible non-respondents can receive
   another SMS on each later configured day.

``sms_response_probability``
   Probability of responding to each SMS (default 0.3).

``reminder_letter_days``
   List of unique non-negative integer sending days, under fixed parameters
   (default ``[10, 20, 30]``). An empty list disables reminders. Days are sorted
   for scheduling. Each mailing is posted at ``day + 0.85``, matching the SMS
   daily offset, to every active non-respondent, including paper-first and
   refusing households. Each letter arrives after ``pQ_postal_delay``, without
   printing delay or consuming questionnaire stock. Letters do not block visits,
   SMS or other mailings. Field visits and delivery can occur on the same day.

``reminder_letter_response_probability``
   One-off response probability on reminder delivery (default 0.4).
   Must be finite and between 0 and 1. Only active, non-responded households
   that are neither paper-first nor refusing can respond. Eligibility is
   rechecked at arrival. Successful households are removed from open-household
   and intervention lists; failed attempts leave baseline probabilities unchanged.
   The shared ``pQ_postal_delay`` must be finite and non-negative.

   Each unit's ``reminder_letter_history`` stores mailing ``time``, aligned
   ``letters_sent``, ``total_letters_sent``, ``letters_delivered`` (to active
   households) and successful ``responses``. Sent counts include letters still
   in transit or whose recipients responded or became vacant after posting.
   Monte Carlo overall and regional summaries include ``total_letters_sent``,
   ``letters_delivered`` and ``reminder_letter_responses``. These are also
   reported in the overall app/script table.

``field_visit_response_probability_if_answer_by_slot``
   One-off probability of responding after an answered visit with no doorstep
   completion or paper order. Requires keys ``morning``, ``afternoon``,
   ``evening`` and ``weekend``, each a finite probability in [0, 1].
   All default to 0.3, replacing the former scalar default of 0.5.

``field_answer_door_probability_by_slot``
   Probability of answering the door in each of the same four slots.
   Each probability is finite and in [0, 1]; all default to 0.3.

``field_visit_response_probability_if_no_answer``
   One-off probability of responding after an unanswered, non-vacant visit
   (default 0.2). Paper-first and refusing households cannot use this route.

``field_first_day``
   Simulation day on which field operations begin.

``field_last_day``
   Final simulation day on which field operations are active.

``field_officer_working_hours_by_slot``
   Finite non-negative hours per officer per day, requiring exactly the same
   four slot keys. Defaults: morning 3, afternoon 3, evening 2, weekend 8.
   Monday-Friday use morning, afternoon and evening. Saturday and Sunday
   each use only the weekend slot. Zero hours disables a slot.

``field_officer_visits_per_hour``
   Shared finite positive visit rate, default 3.75. Capacity is rounded down
   separately for each active slot: ``floor(slot_hours * visits_per_hour)``.
   Defaults give 11 morning, 11 afternoon and 7 evening visits (29 per weekday),
   or 30 visits per weekend day. Fractional capacity is not pooled or carried
   forward. These settings replace the scalar working-hours setting and
   ``daily_field_visits``.

   All slots execute at the same simulated time, without elapsed visit duration
   or spillover. Households are assigned in list order to active slots in
   morning/afternoon/evening order, or weekend only. A household is selected at
   most once per day. Existing eligibility and revisit delays still apply.
   Each single-run unit exposes ``field_visit_history`` records containing
   ``time``, ``household_id`` and ``slot``. Monte Carlo overall and regional
   summaries report ``field_visits_morning``, ``field_visits_afternoon``,
   ``field_visits_evening`` and ``field_visits_weekend``.

``field_doorstep_completion_probability``
   Simple: unconditional per-knock automatic success probability, including
   while awaiting paper. Detailed: conditional probability of completion after
   answering when not awaiting paper. Default 0.5 in both modes.


Module And API Reference
------------------------

``parameters`` module
~~~~~~~~~~~~~~~~~~~~~

.. py:class:: RegionParameters

   Frozen regional configuration holding household count, officer count and
   A/B/C population shares. The national total is the sum of regional counts.

.. py:class:: SimulationParameters

   Frozen dataclass that groups together the parameters required for a simulation
   run. It provides a simple way to create scenario variants without changing the
   rest of the simulation wiring.

   Attributes include response probabilities, intervention timings, daily visit limits,
   and the random seed.

``baseline_parameters``
   Default parameter set.

``PoC_parameters``
   Example scenario derived from ``baseline_parameters`` using
   ``dataclasses.replace``.

``functions.simulation_runner`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: run_monte_carlo(scenario_params=baseline_parameters, run_until=50, ...)

   Repeats the single-run model ``monte_carlo_repeats`` times. Returns
   ``overall_summary`` and ``region_summaries`` with ``mean``, ``lower_95`` and
   ``upper_95`` for final outcomes. ``aggregate_history`` and ``region_histories``
   contain mean curves and pointwise percentile intervals. ``run_seeds`` records
   reproducible seeds; ``call_centre_history`` contains mean daily call demand.
   Household objects are not retained across repeats. Regions share a clock
   and services within each run; repeats start fresh and execute sequentially.
   Per-run histories and final metrics are held temporarily for summarisation,
   but are not returned or saved separately. Only combined results and run
   seeds remain available after the call. Scenario settings stay identical
   across repeats except for the seed and the internal repeat count of one.
   Each run seed is the starting seed plus the repeat index times
   ``max(10_001, number_of_units + 1)``. Zero-officer regions still have one
   internal unit and count towards this spacing.

.. py:function:: run_simulation(scenario_params=baseline_parameters, run_until=50, ...)

   Builds every region in one SimPy environment and registers a single global
   call-centre process for one run. Returns overall history and named regional histories
   in ``result.regions``. Officer units remain internal implementation details.
   Plots place the overall chart above named regional panels, with consistent
   group colours. Rates are weighted by active household counts, including
   after vacancies remove households.


``functions.functions_households`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:class:: Household(id, rng, baseline_response_probability, paper_first_probability_by_group)

   Represents a single household in the simulation.

   The current implementation assigns several attributes randomly at creation
   time, including ``paper_first``, ``hard_to_count``, ``sms_available``, and
   ``demographic_group``. It also stores response-state fields such as
   ``response_probability`` and ``responded``.

.. py:method:: Household.__repr__()

   Returns a concise text representation of the household for debugging.

.. py:function:: first_day_responses(env, households, rng)

   SimPy process that applies one-off first-day responses at simulation time
   ``t = 0``. Each household is marked as responded if a random draw falls below
   its initial ``response_probability``, set from the first value in its group table.

.. py:function:: daily_response_updates(env, households, rng, daily_response_probabilities_by_group, open_households=None, sms_list=None)

   SimPy process that starts after the first day and then checks once per day
   whether each non-responding household responds according to its current
   ``response_probability``. Respondents are removed immediately from the
   supplied outstanding and SMS lists. The simulation supplies both lists.


``functions.functions_sms`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each run registers one national selection process and one SMS scheduling process.
All officer units reference the same central SMS list so daily responses,
field outcomes and reminder responses remove contacts immediately.
SMS uses a dedicated reproducible random stream. Each Monte Carlo repeat
starts with a fresh national list; regional response reporting is preserved.

.. py:function:: send_sms(env, sms_list, sending_days, sms_response_probability, rng, open_households=None)

   SimPy process that loops over sorted sending days, waits until
   ``day + 0.85`` and makes one response
   draw for each active, outstanding, non-refusing, non-paper-first household
   in ``sms_list``. Success records an immediate return and removes the household
   from the open and SMS lists immediately. Failure has no lasting effect on
   daily probabilities. Eligibility is rechecked on every sending day.
   The process finishes after the final send; there is no delayed housekeeping check.

.. py:function:: populate_sms_list(env, households, sms_list)

   SimPy process that runs shortly after first-day responses and fills
   ``sms_list`` with households that have an SMS contact route and have not yet
   responded.


``functions.functions_reminder_letters`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``send_reminder_letters``
   Schedules each mailing and records its recipient count. Independently
   schedules delivery for each recipient; no shared paper stock is used.

``deliver_reminder_letter``
   Waits for the postal delay, rechecks recipient eligibility and makes one
   response draw. Uses a separate reproducible random stream per officer unit
   so disabled reminders do not alter other intervention random draws.


``functions.functions_field`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: create_field_officer(env)

   Creates the SimPy ``Resource`` used to represent field-officer capacity.

.. py:function:: populate_field_officer_list(env, households, field_officer_list)

   SimPy process that runs shortly after first-day responses and adds eligible,
   non-responding households to the field-officer candidate list.

.. py:function:: queue_field_officer_visits(env, field_officer, open_households, intervention_lists, field_officer_list, first_day, last_day, response_probability_if_no_answer, scenario_params, random_source, doorstep_completion_probability, vacancy_probability_if_no_answer, days_until_next_visit, paper_questionnaire_service, field_enabled=True, visit_history=None)

   SimPy process that runs on each integer day from ``first_day`` through
   ``last_day``, inclusive. It uses ``scenario_params.field_visit_capacities_at(day)``
   to assign eligible households to slots and passes the slot-specific answer
   and response probabilities to each visit. All visits share that timestamp.
   ``field_enabled=False`` disables the process for units without an officer.

   The queue filters to active, non-responded, non-refusing households that are
   not waiting for a later revisit day. Awaiting paper does not exclude a visit.

.. py:function:: field_officer_visit(env, field_officer, open_households, intervention_lists, field_officer_list, household, random_source, answer_door_probability, doorstep_completion_probability, vacancy_probability_if_no_answer, days_until_next_visit, response_probability_if_answer, response_probability_if_no_answer, paper_questionnaire_service, visit_slot=None, visit_history=None, visit_mode="detailed", refusal_probability=0.01, vacancy_probability=0.05, success_probability=0.3)

   SimPy process for a single field visit. It requests field-officer capacity,
   then handles the visit without advancing simulation time. Configured
   probabilities determine door answering, doorstep completion, vacancy and
   one-off returns; other outcomes include paper orders and future revisits.
   Common visit accounting dispatches to ``simple_field_visit_outcome`` or
   ``detailed_field_visit_outcome``. Direct calls default to detailed for
   compatibility; the scheduler explicitly passes the scenario's mode.
   The scheduler supplies ``visit_slot`` and a shared per-unit ``visit_history``
   list. Only visits actually performed are recorded.

.. py:function:: end_of_day_remove_responded_houses(env, field_officer_list, start_date)

   SimPy process that runs after daily updates once field visits are active and
   removes households that have already responded from the field-officer list.


``functions.intervention_lists`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:class:: intervention_lists

   Lightweight container class holding mutable lists used by intervention
   processes. The current attributes are ``sms_list``, ``field_officer_list``,
   and ``reminder_card_list``.
   During a simulation run, ``sms_list`` references the same national list
   in every unit. The field-officer and reminder-card lists remain local.
   The run result exposes the central list as ``sms_list``.


``functions.functions_output`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: initialise_household_return_history(households)

   Builds the dictionary used to store output series for plotting. The structure
   includes overall response counts, overall response proportions, and a separate
   proportion series for each demographic group present in the supplied
   households.

.. py:function:: daily_response_totals(env, households)

   Debugging helper that records daily response totals and prints the most recent
   three values. This process is currently not enabled in ``simulation.py``.

.. py:function:: record_household_return_proportions(env, households, history)

   SimPy process that records output snapshots for plotting. After allowing
   first-day responses to happen at ``t = 0``, it stores:

   * the day label (snapshot time minus 0.9, rounded to ten decimal places),
   * the active population and active households responded,
   * the overall response proportion,
   * one response-proportion series per demographic group.

   Snapshots occur at ``t = 0.9, 1.9, 2.9, ...``, labelled days 0, 1, 2,
   and include group-level active counts. Initial population counts remain
   fixed. A run stopping at 50 has snapshots labelled 0 through 49.

.. py:function:: plot_household_return_proportions(history, sms_days=None, field_first_day=None, call_centre_history=None, show_plot=False, output_path=None, region_histories=None, reminder_letter_days=None)

   ``reminder_letter_days`` adds purple dashed sending-day markers to every
   overall and regional panel, with one shared legend entry. Postal delay is
   not added. Omitted or empty sending days produce no reminder markers.

   Plots overall and group return curves with named regional panels below.
   For Monte Carlo histories, curves are means and shaded bands are pointwise
   central 95% run intervals for the overall curve in each panel. Group curves
   show means without shaded group intervals. Call-centre history is accepted
   but not plotted. Daily labels and straight-line interpolation are unchanged,
   as are SMS and field-start markers.


``simulation`` module
~~~~~~~~~~~~~~~~~~~~~

The ``main()`` entrypoint:

* import a scenario from ``parameters.py``,
* calls ``run_monte_carlo()`` to repeat regional runs until day 50,
* displays and saves the mean overall-and-regions chart,
* prints an overall mean/95% interval table, followed by regional summaries.


Testing
-------

The repository currently contains a limited automated test suite.

To run the existing tests:

.. code-block:: powershell

   pytest

At the time of writing, the visible test coverage focuses on SMS-related logic.
