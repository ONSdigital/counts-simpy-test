import dataclasses as dc
import random

import numpy as np
import simpy

import functions.functions_contact_centre as cc
import functions.functions_output as out
import functions.functions_sms as sms
from functions.function_core import build_region
from parameters import FIELD_VISIT_SLOTS, SimulationParameters
from parameters import baseline_parameters
from functions.simulation_types import RegionState, UnitState


@dc.dataclass
class SimulationRunResult:
    params: SimulationParameters
    units: list[UnitState]
    regions: list[RegionState]
    call_centre_history: dict
    aggregate_history: dict
    sms_list: list


@dc.dataclass
class MonteCarloResult:
    params: SimulationParameters
    run_seeds: list[int]
    overall_summary: dict
    region_summaries: dict
    aggregate_history: dict
    region_histories: dict
    call_centre_history: dict


def run_monte_carlo(
    scenario_params=baseline_parameters,
    run_until=50,
    progress_interval=None,
    progress_callback=None,
    generate_plot=True,
    show_plot=False,
    output_path=None,
):
    """Repeat the regional model with independent seeds and summarise run variation."""
    #generate the correct number of random seeds
    seed_stride = max(
        10_001,
        1 + sum(max(region.num_field_officers, 1) for region in scenario_params.regions.values()),
    )
    run_seeds = [
        scenario_params.seed + repeat * seed_stride
        for repeat in range(scenario_params.monte_carlo_repeats)
    ]
    overall_values = []
    region_values = {name: [] for name in scenario_params.regions}
    histories = []
    region_histories = {name: [] for name in scenario_params.regions}
    call_histories = []

     #function to summarise final metrics for monte carlo run (not at a certain time, but overall)
    def summarise_metrics(run_values):
            return {
                key: out.summarise_monte_carlo_values([values[key] for values in run_values])
                for key in run_values[0]
            }

#function to format final metrics for a single run
    def final_metrics(history, households, units):
        if not history["time"]:
            raise ValueError("run_until must include at least one response snapshot")
        return {
            "total_households": history["total_households"],
            "responded_count": history["responded_count"][-1],
            "active_households": history["active_households"][-1],
            "proportion_returned": history["proportion_returned"][-1],
            "field_visits": sum(household.field_knocks for household in households),
            "simple_field_successes": sum(household.simple_field_successes for household in households),
            "total_letters_sent": sum(
                unit.reminder_letter_history["total_letters_sent"] for unit in units
            ),
            "letters_delivered": sum(
                unit.reminder_letter_history["letters_delivered"] for unit in units
            ),
            "reminder_letter_responses": sum(
                unit.reminder_letter_history["responses"] for unit in units
            ),
            **{
                f"field_visits_{slot}": sum(
                    visit["slot"] == slot
                    for unit in units
                    for visit in unit.field_visit_history
                )
                for slot in FIELD_VISIT_SLOTS
            },
            "doorstep_completions": sum(household.doorstep_completions for household in households),
        }
#for each repeat in a monte carlo, run the simulation, collect metrics and add to the overall values/histories produced above
    for repeat, seed in enumerate(run_seeds):
        if progress_interval:
            print(f"Monte Carlo run {repeat + 1}/{len(run_seeds)} (seed {seed})")
        callback = None
        if progress_callback is not None:
            def report_progress(day, offset=repeat * run_until):
                progress_callback(offset + day)
            callback = report_progress
        run = run_simulation(
            dc.replace(scenario_params, seed=seed, monte_carlo_repeats=1),
            run_until=run_until,
            progress_interval=progress_interval,
            progress_callback=callback,
            generate_plot=False,
        )
        metrics = final_metrics(
            run.aggregate_history,
            [household for region in run.regions for household in region.households],
            run.units,
        )
        metrics["total_calls"] = sum(run.call_centre_history["daily_calls"])
        overall_values.append(metrics)
        histories.append(run.aggregate_history)
        call_histories.append(run.call_centre_history)
        for region in run.regions:
            region_values[region.name].append(
                final_metrics(region.return_history, region.households, region.units)
            )
            region_histories[region.name].append(region.return_history)
   

    #combine the histories from all Monte Carlo runs, maintaining the snapshot structure
    aggregate_history = out.summarise_monte_carlo_histories(histories)
    combined_regions = {
        name: out.summarise_monte_carlo_histories(values)
        for name, values in region_histories.items()
    }
    daily_calls = np.asarray([history["daily_calls"] for history in call_histories], dtype=float)
    call_centre_history = {
        "time": list(call_histories[0]["time"]),
        "daily_calls": np.mean(daily_calls, axis=0).tolist(),
        "daily_calls_lower_95": np.quantile(daily_calls, 0.025, axis=0).tolist(),
        "daily_calls_upper_95": np.quantile(daily_calls, 0.975, axis=0).tolist(),
    }
    #add weekday information to each history based on the scenario parameters
    for history in (aggregate_history, call_centre_history, *combined_regions.values()):
        history["weekday"] = [scenario_params.weekday_at(time) for time in history["time"]]
    
    if generate_plot:
        out.plot_household_return_proportions(
            aggregate_history,
            sms_days=scenario_params.sms_days,
            field_first_day=scenario_params.field_first_day,
            call_centre_history=call_centre_history,
            show_plot=show_plot,
            output_path=output_path,
            region_histories=combined_regions,
            reminder_letter_days=scenario_params.reminder_letter_days,
        )
    return MonteCarloResult(
        params=scenario_params,
        run_seeds=run_seeds,
        overall_summary=summarise_metrics(overall_values),
        region_summaries={name: summarise_metrics(values) for name, values in region_values.items()},
        aggregate_history=aggregate_history,
        region_histories=combined_regions,
        call_centre_history=call_centre_history,
    )

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
        SimulationRunResult containing regional and aggregate outputs.
    """

    env = simpy.Environment()
    paper_questionnaire_service = cc.PaperQuestionnaireService(
        scenario_params.initial_paper_batch,
        scenario_params.pQ_postal_delay,
        scenario_params.printing_delay,
    )

    units = []
    regions = []
    sms_list = []
    next_household_id = 0
    for name, region_params in scenario_params.regions.items():
        region = build_region(
            env,
            name,
            region_params,
            scenario_params,
            len(units),
            next_household_id,
            paper_questionnaire_service,
            sms_list,
        )
        regions.append(region)
        units.extend(region.units)
        next_household_id += region_params.num_households

    all_open_household_lists = [unit.open_households for unit in units]
    all_households = [household for unit in units for household in unit.households]
    env.process(sms.populate_sms_list(env, all_households, sms_list))
    env.process(
        sms.send_sms(
            env, sms_list, scenario_params.sms_days,
            scenario_params.sms_response_probability,
            random.Random(f"{scenario_params.seed}:national_sms"),
            all_open_household_lists,
        )
    )
    call_centre_history = out.initialise_call_centre_history()
    call_centre_rng = random.Random(
        scenario_params.seed + max(unit.unit_id for unit in units) + 1
    )
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
                print(f"Simulation reached day {current_day} ({scenario_params.weekday_at(current_day)})")
            current_day += step_size

        env.run(until=run_until)
        if progress_callback is not None:
            progress_callback(run_until)
        else:
            print(f"Simulation reached day {run_until} ({scenario_params.weekday_at(run_until)})")

    for region in regions:
        region.return_history = out.aggregate_unit_return_histories(
            [unit.return_history for unit in region.units]
        )
    aggregate_history = out.aggregate_unit_return_histories(
        [region.return_history for region in regions]
    )
    for history in (
        aggregate_history,
        call_centre_history,
        *(unit.return_history for unit in units),
        *(region.return_history for region in regions),
    ):
        history["weekday"] = [scenario_params.weekday_at(time) for time in history["time"]]

    if generate_plot:
        out.plot_household_return_proportions(
            aggregate_history,
            sms_days=scenario_params.sms_days,
            field_first_day=scenario_params.field_first_day,
            call_centre_history=call_centre_history,
            show_plot=show_plot,
            output_path=output_path,
            region_histories={region.name: region.return_history for region in regions},
            reminder_letter_days=scenario_params.reminder_letter_days,
        )

    return SimulationRunResult(
        params=scenario_params,
        units=units,
        regions=regions,
        call_centre_history=call_centre_history,
        aggregate_history=aggregate_history,
        sms_list=sms_list,
    )
