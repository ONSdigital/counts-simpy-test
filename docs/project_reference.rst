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
   * SMS list population and one-off SMS response attempts,
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

* Console output with progress updates and per-unit final return proportions.
* A matplotlib chart saved to ``household_returns.png`` showing:

  * overall household return proportion over time,
  * one line per demographic group,
  * response-count labels on every 10th sampled point,
   * intervention timing markers for SMS and field operation start day.


Configuration
-------------

Simulation settings are defined in ``parameters.py``. The main script currently
imports ``baseline_parameters`` as ``params``. The Streamlit app also uses
``baseline_parameters`` as its default baseline.

``new_scenario_parameters`` is kept in ``parameters.py`` as an example of creating
a modified scenario with ``dataclasses.replace``.

To change the scenario, either:

* edit the values in ``baseline_parameters`` (by changing defaults in
   ``SimulationParameters``), or
* define another ``SimulationParameters`` instance and update the import in
  ``simulation.py``.

Important parameters include:

``num_households``
   Number of households generated for the run.

``daily_response_probabilities_by_group``
   A dictionary containing 50 daily baseline probabilities for each of A, B
   and C. Index 0 is day 1 and index 49 is day 50. Longer runs retain the last
   value. There is no automatic decay; interventions make separate one-off
   response attempts without changing the table. Defaults are 0.05 for all groups and days.
   Each group's first value also sets its time-zero response probability.

``sms_timing``
   Simulation day on which the one-off SMS response attempts occur.

``sms_response_probability``
   One-off probability of responding to SMS (default 0.3).

``field_visit_response_probability_if_answer``
   One-off probability of responding after an answered visit with no doorstep
   completion or paper order (default 0.5).

``field_visit_response_probability_if_no_answer``
   One-off probability of responding after an unanswered, non-vacant visit
   (default 0.2). Paper-first and refusing households cannot use this route.

``field_first_day``
   Simulation day on which field operations begin.

``field_last_day``
   Final simulation day on which field operations are active.

``daily_field_visits``
   Maximum visits completed per officer each day (default 30). Each day's
   visits complete at the same simulated time, with no visit duration or
   spillover. Fewer visits occur when fewer households are eligible. Zero
   disables visits.

``field_doorstep_completion_probability``
   Probability that a household completes at the doorstep when the door is
   answered during a field visit.


Module And API Reference
------------------------

``parameters`` module
~~~~~~~~~~~~~~~~~~~~~

.. py:class:: SimulationParameters

   Frozen dataclass that groups together the parameters required for a simulation
   run. It provides a simple way to create scenario variants without changing the
   rest of the simulation wiring.

   Attributes include response probabilities, intervention timings, daily visit limits,
   and the random seed.

``baseline_parameters``
   Default parameter set.

``new_scenario_parameters``
   Example scenario derived from ``baseline_parameters`` using
   ``dataclasses.replace``.


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

.. py:function:: daily_response_updates(env, households, rng)

   SimPy process that starts after the first day and then checks once per day
   whether each non-responding household responds according to its current
   ``response_probability``.


``functions.functions_sms`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: sms_day_n_responses(env, sms_list, n, sms_response_probability, rng, open_households=None)

   SimPy process that waits until time ``n + 0.85`` and makes a single response
   draw for each active, outstanding, non-refusing, non-paper-first household
   in ``sms_list``. Success records an immediate return and removes the household
   from the open list. Failure has no lasting effect on daily probabilities.
   After a short delay, responded households are removed from ``sms_list``.

.. py:function:: populate_sms_list(env, households, sms_list)

   SimPy process that runs shortly after first-day responses and fills
   ``sms_list`` with households that have an SMS contact route and have not yet
   responded.


``functions.functions_field`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:function:: create_field_officer(env)

   Creates the SimPy ``Resource`` used to represent field-officer capacity.

.. py:function:: populate_field_officer_list(env, households, field_officer_list)

   SimPy process that runs shortly after first-day responses and adds eligible,
   non-responding households to the field-officer candidate list.

.. py:function:: queue_field_officer_visits(env, field_officer, open_households, intervention_lists, field_officer_list, first_day, last_day, response_probability_if_answer, response_probability_if_no_answer, daily_field_visits, random_source, answer_door_probability, doorstep_completion_probability, vacancy_probability_if_no_answer, days_until_next_visit, paper_questionnaire_service)

   SimPy process that runs on each integer day from ``first_day`` through
   ``last_day``, inclusive. It selects up to ``daily_field_visits`` eligible
   households per officer and completes all selected visits at that timestamp.

   The queue currently filters to households that have not responded and are not
   waiting for a later revisit day.

.. py:function:: field_officer_visit(env, field_officer, open_households, intervention_lists, field_officer_list, household, random_source, answer_door_probability, doorstep_completion_probability, vacancy_probability_if_no_answer, days_until_next_visit, response_probability_if_answer, response_probability_if_no_answer, paper_questionnaire_service)

   SimPy process for a single field visit. It requests field-officer capacity,
   then handles the visit without advancing simulation time. Configured
   probabilities determine door answering, doorstep completion, vacancy and
   one-off returns; other outcomes include paper orders and future revisits.

.. py:function:: end_of_day_remove_responded_houses(env, field_officer_list, start_date)

   SimPy process that runs after daily updates once field visits are active and
   removes households that have already responded from the field-officer list.


``functions.intervention_lists`` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. py:class:: intervention_lists

   Lightweight container class holding mutable lists used by intervention
   processes. The current attributes are ``sms_list``, ``field_officer_list``,
   and ``reminder_card_list``.


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

   * the current simulation time,
   * the total number of households responded,
   * the overall response proportion,
   * one response-proportion series per demographic group.

   The process then repeats once per simulated day.

.. py:function:: plot_household_return_proportions(history, sms_day=None, field_visit_day=None)

   Creates the matplotlib chart for household returns over time. The chart plots
   one line per demographic group, a dashed overall line, labels every 10th
   sampled overall point with the total responded count, and optionally draws
   vertical timing markers for SMS and field-visit start days.


``simulation`` module
~~~~~~~~~~~~~~~~~~~~~

This module is currently written as a script rather than as reusable functions.
Its responsibilities are:

* import a scenario from ``parameters.py``,
* instantiate the SimPy environment,
* create households and intervention containers,
* register all event processes,
* run the environment until day 50,
* plot the resulting return history.


Testing
-------

The repository currently contains a limited automated test suite.

To run the existing tests:

.. code-block:: powershell

   pytest

At the time of writing, the visible test coverage focuses on SMS-related logic.
