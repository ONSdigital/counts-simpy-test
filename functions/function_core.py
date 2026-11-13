import random

import functions.functions_field as field
import functions.functions_households as hh
import functions.functions_output as out
import functions.functions_reminder_letters as reminders
import functions.intervention_lists as il
from functions.simulation_types import RegionState, UnitState


def build_region(
    env,
    name,
    region_params,
    scenario_params,
    unit_id_start,
    household_id_start,
    paper_questionnaire_service,
    sms_list,
):
    """Allocate regional household groups and build internal officer units."""

    expected_counts = {
        group: region_params.num_households * share
        for group, share in region_params.household_type_proportions.items()
    }
    group_counts = {group: int(count) for group, count in expected_counts.items()}
    remainder = region_params.num_households - sum(group_counts.values())
    ordered_groups = sorted(
        group_counts,
        key=lambda group: (-(expected_counts[group] - group_counts[group]), group),
    )
    for group in ordered_groups[:remainder]:
        group_counts[group] += 1
    groups = [group for group, count in group_counts.items() for _ in range(count)]
    random.Random(f"{scenario_params.seed}:{name}:group_shuffle").shuffle(groups)

    unit_count = max(region_params.num_field_officers, 1)
    households_per_unit, household_remainder = divmod(region_params.num_households, unit_count)
    units = []
    offset = 0
    for unit_index in range(unit_count):
        household_count = households_per_unit + (unit_index < household_remainder)
        units.append(
            build_unit(
                env,
                unit_id_start + unit_index,
                scenario_params,
                household_count,
                household_id_start + offset,
                paper_questionnaire_service,
                sms_list,
                demographic_groups=groups[offset:offset + household_count],
                field_enabled=region_params.num_field_officers > 0,
            )
        )
        offset += household_count
    return RegionState(name=name, units=units, return_history={})


def build_unit(
    env,
    unit_id,
    scenario_params,
    household_count,
    household_id_start,
    paper_questionnaire_service,
    sms_list,
    demographic_groups=None,
    field_enabled=True,
):
    """Build one officer unit sharing the national SMS list and register local processes."""

    unit_rng = random.Random(scenario_params.seed + unit_id)
    households = [
        hh.Household(
            id=household_id_start + i,
            rng=unit_rng,
            baseline_response_probability=0.0,
            paper_first_probability_by_group=scenario_params.paper_first_probability_by_group,
            demographic_group=demographic_groups[i] if demographic_groups is not None else None,
        )
        for i in range(household_count)
    ]
    for household in households:
        initial_probability = scenario_params.daily_response_probabilities_by_group[household.demographic_group][0]
        household.baseline_response_probability = initial_probability
        household.response_probability = initial_probability

    unit_intervention_lists = il.intervention_lists(sms_list=sms_list)
    unit_field_officer = field.create_field_officer(env)
    unit_return_history = out.initialise_household_return_history(households)
    open_households = []
    field_visit_history = []
    unit = UnitState(
        unit_id=unit_id,
        households=households,
        open_households=open_households,
        intervention_lists=unit_intervention_lists,
        field_officer=unit_field_officer,
        return_history=unit_return_history,
        field_visit_history=field_visit_history,
    )

    env.process(hh.first_day_responses(env, households, unit_rng, open_households))
    env.process(out.record_household_return_proportions(env, households, unit_return_history))
    env.process(
        hh.daily_response_updates(
            env,
            households,
            unit_rng,
            scenario_params.daily_response_probabilities_by_group,
            open_households,
            sms_list=unit_intervention_lists.sms_list,
        )
    )
    env.process(
        reminders.send_reminder_letters(
            env, households, scenario_params.reminder_letter_days,
            scenario_params.pQ_postal_delay,
            scenario_params.reminder_letter_response_probability,
            random.Random(f"{scenario_params.seed}:{unit_id}:reminder_letters"),
            open_households, unit_intervention_lists, unit.reminder_letter_history,
        )
    )
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
            response_probability_if_no_answer=scenario_params.field_visit_response_probability_if_no_answer,
            scenario_params=scenario_params,
            field_enabled=field_enabled,
            visit_history=field_visit_history,
            random_source=unit_rng,
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

    return unit
