import random

import functions.functions_field as field
import functions.functions_households as hh
import functions.functions_output as out
import functions.functions_sms as sms
import functions.intervention_lists as il
from simulation_types import UnitState


def build_unit(
    env,
    unit_id,
    scenario_params,
    household_count,
    household_id_start,
    paper_questionnaire_service,
):
    """Build one independent simulation unit and register its processes."""

    unit_rng = random.Random(scenario_params.seed + unit_id)
    households = [
        hh.Household(
            id=household_id_start + i,
            rng=unit_rng,
            baseline_response_probability=scenario_params.baseline_response_probability,
            first_day_probability=scenario_params.first_day_probability,
            paper_first_probability_by_group=scenario_params.paper_first_probability_by_group,
        )
        for i in range(household_count)
    ]

    unit_intervention_lists = il.intervention_lists()
    unit_field_officer = field.create_field_officer(env)
    unit_return_history = out.initialise_household_return_history(households)
    open_households = []

    env.process(hh.first_day_responses(env, households, unit_rng, open_households))
    env.process(out.record_household_return_proportions(env, households, unit_return_history))
    env.process(
        hh.daily_response_updates(
            env,
            households,
            unit_rng,
            scenario_params.daily_percentage_response_decrease,
            open_households,
        )
    )
    env.process(
        sms.sms_day_n_increase_baseline(
            env,
            unit_intervention_lists.sms_list,
            scenario_params.sms_timing,
            scenario_params.sms_response_probability,
        )
    )
    env.process(sms.populate_sms_list(env, open_households, unit_intervention_lists.sms_list))
    env.process(
        field.populate_field_officer_list(
            env,
            open_households,
            unit_intervention_lists.field_officer_list,
        )
    )
    env.process(
        field.queue_field_officer_visits(
            env,
            unit_field_officer,
            open_households,
            unit_intervention_lists,
            unit_intervention_lists.field_officer_list,
            first_day=scenario_params.field_first_day,
            last_day=scenario_params.field_last_day,
            visit_duration=scenario_params.field_visit_duration,
            response_probability_increase_if_answer=scenario_params.field_visit_response_boost_if_answer,
            response_probability_increase_if_no_answer=scenario_params.field_visit_response_boost_if_no_answer,
            queue_size=scenario_params.field_daily_queue_size,
            random_source=unit_rng,
            answer_door_probability=scenario_params.field_answer_door_probability,
            doorstep_completion_probability=scenario_params.field_doorstep_completion_probability,
            vacancy_probability_if_no_answer=scenario_params.field_vacancy_probability_if_no_answer,
            days_until_next_visit=scenario_params.field_days_until_next_visit,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )
    env.process(
        field.end_of_day_remove_responded_houses(
            env,
            unit_intervention_lists.field_officer_list,
            scenario_params.field_first_day,
        )
    )

    return UnitState(
        unit_id=unit_id,
        households=households,
        open_households=open_households,
        intervention_lists=unit_intervention_lists,
        field_officer=unit_field_officer,
        return_history=unit_return_history,
    )
