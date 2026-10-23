import dataclasses as dc
import random

import simpy

import functions.functions_contact_centre as cc
import functions.functions_output as out
from function_core import build_unit
from parameters import SimulationParameters
from parameters import baseline_parameters
from simulation_types import UnitState


@dc.dataclass
class SimulationRunResult:
    params: SimulationParameters
    units: list[UnitState]
    call_centre_history: dict
    aggregate_history: dict

def run_simulation(
    scenario_params=baseline_parameters,
    run_until=50,
    progress_interval=None,
    progress_callback=None,
    generate_plot=True,
    show_plot=False,
    output_path=None,
):
    """Run the simulation and return structured outputs.

    Args:
        scenario_params: Scenario parameters dataclass.
        run_until: Simulation horizon.
        progress_interval: Optional interval for progress prints.
        progress_callback: Optional callable invoked with each reported day.
        generate_plot: Whether to generate an output plot as part of the run.
        show_plot: Whether to display the output chart.
        output_path: Optional image path for the chart.

    Returns:
        SimulationRunResult containing unit-level and aggregate outputs.
    """

    num_units = scenario_params.num_field_officers
    if num_units <= 0:
        raise ValueError("num_field_officers must be greater than 0")

    env = simpy.Environment()
    paper_questionnaire_service = cc.PaperQuestionnaireService(
        scenario_params.initial_paper_batch,
        scenario_params.pQ_postal_delay,
        scenario_params.printing_delay,
    )

    households_per_unit = scenario_params.num_households // num_units
    household_remainder = scenario_params.num_households % num_units

    units = []
    next_household_id = 0
    for unit_id in range(num_units):
        unit_household_count = households_per_unit + (1 if unit_id < household_remainder else 0)
        units.append(
            build_unit(
                env,
                unit_id,
                scenario_params,
                unit_household_count,
                next_household_id,
                paper_questionnaire_service,
            )
        )
        next_household_id += unit_household_count

    all_open_household_lists = [unit.open_households for unit in units]
    call_centre_history = out.initialise_call_centre_history()
    call_centre_rng = random.Random(scenario_params.seed + 10_000)
    env.process(
        cc.process_call_centre_calls(
            env,
            all_open_household_lists,
            scenario_params.call_centre_call_probability,
            call_centre_rng,
            call_centre_history,
            paper_questionnaire_service,
        )
    )

    step_size = None
    if progress_interval and progress_interval > 0:
        step_size = progress_interval
        print("Starting simulation run...")
    elif progress_callback is not None:
        step_size = 1

    if step_size is None:
        env.run(until=run_until)
    else:
        current_day = step_size
        while current_day < run_until:
            env.run(until=current_day)
            if progress_callback is not None:
                progress_callback(current_day)
            else:
                print(f"Simulation reached day {current_day}")
            current_day += step_size

        env.run(until=run_until)
        if progress_callback is not None:
            progress_callback(run_until)
        else:
            print(f"Simulation reached day {run_until}")

    aggregate_history = out.aggregate_unit_return_histories(
        [unit.return_history for unit in units]
    )

    if generate_plot:
        out.plot_household_return_proportions(
            aggregate_history,
            sms_day=scenario_params.sms_timing,
            field_first_day=scenario_params.field_first_day,
            call_centre_history=call_centre_history,
            show_plot=show_plot,
            output_path=output_path,
            unit_histories=[unit.return_history for unit in units],
        )

    return SimulationRunResult(
        params=scenario_params,
        units=units,
        call_centre_history=call_centre_history,
        aggregate_history=aggregate_history,
    )
