#import packages
import random

import simpy

import functions.functions_contact_centre as cc
import functions.functions_output as out
from functions.function_core import build_unit


#import scenario parameters
from parameters import baseline_parameters as params

num_of_households = params.num_households
num_field_officers = params.num_field_officers
sms_response_probability = params.sms_response_probability
SEED = params.seed
sms_timing = params.sms_timing
intervention_costs = params.intervention_costs
baseline_response_probability = params.baseline_response_probability
first_day_probability = params.first_day_probability
daily_percentage_response_decrease = params.daily_percentage_response_decrease
field_first_day = params.field_first_day
field_last_day = params.field_last_day
field_visit_duration = params.field_visit_duration
field_visit_response_boost_if_answer = params.field_visit_response_boost_if_answer
field_visit_response_boost_if_no_answer = params.field_visit_response_boost_if_no_answer
field_daily_queue_size = params.field_daily_queue_size
field_answer_door_probability = params.field_answer_door_probability
field_doorstep_completion_probability = params.field_doorstep_completion_probability
field_vacancy_probability_if_no_answer = params.field_vacancy_probability_if_no_answer
field_days_until_next_visit = params.field_days_until_next_visit
call_centre_call_probability = params.call_centre_call_probability
initial_paper_batch = params.initial_paper_batch
pQ_postal_delay = params.pQ_postal_delay
printing_delay = params.printing_delay
num_units = num_field_officers


#setup environment
env = simpy.Environment()


households_per_unit = num_of_households // num_units
household_remainder = num_of_households % num_units

paper_questionnaire_service = cc.PaperQuestionnaireService(
    initial_paper_batch,
    pQ_postal_delay,
    printing_delay,
)

#build and run units
units = []
next_household_id = 0
for unit_id in range(num_units):
    unit_household_count = households_per_unit + (1 if unit_id < household_remainder else 0)
    units.append(
        build_unit(
            env,
            unit_id,
            params,
            unit_household_count,
            next_household_id,
            paper_questionnaire_service,
        )
    )
    next_household_id += unit_household_count

#single global call centre across all units
all_open_household_lists = [unit.open_households for unit in units]
call_centre_history = out.initialise_call_centre_history()
call_centre_rng = random.Random(params.seed + 10_000)
env.process(
    cc.process_call_centre_calls(
        env,
        all_open_household_lists,
        call_centre_call_probability,
        call_centre_rng,
        call_centre_history,
        paper_questionnaire_service,
    )
)

print("Starting simulation run...")
for day in range(5, 51, 5):
    env.run(until=day)
    print(f"Simulation reached day {day}")

#report per-unit outcomes
for unit in units:
    final_proportion = unit.return_history["proportion_returned"][-1]
    print(f"Unit {unit.unit_id} final return proportion: {final_proportion:.3f}")

#aggregate and plot across all units
aggregate_history = out.aggregate_unit_return_histories(
    [unit.return_history for unit in units]
)
out.plot_household_return_proportions(
    aggregate_history,
    sms_day=sms_timing,
    field_first_day=field_first_day,
    call_centre_history=call_centre_history,
    show_plot=True,
    output_path="household_returns.png",
    unit_histories=[unit.return_history for unit in units],
)

