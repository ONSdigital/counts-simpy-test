import simpy


def remove_household_from_all_intervention_lists(household, intervention_lists):
    """Remove a household from every intervention list if present."""

    for intervention_list in (
        intervention_lists.sms_list,
        intervention_lists.field_officer_list,
        intervention_lists.reminder_card_list,
    ):
        while household in intervention_list:
            intervention_list.remove(household)


def remove_vacant_household(household, open_households, intervention_lists):
    """Remove a vacant household from the model population and interventions."""

    remove_household_from_all_intervention_lists(household, intervention_lists)
    household.is_active = False
    household.waiting_for_pq = False
    if household in open_households:
        open_households.remove(household)

def create_field_officer(env: simpy.Environment):
    """Create the SimPy resource representing field-officer capacity.

    Args:
        env: SimPy environment.

    Returns:
        A SimPy resource with capacity for one field officer.
    """

    return simpy.Resource(env, capacity=1)

def populate_field_officer_list(env: simpy.Environment, households, field_officer_list):
    """Populate the field-officer list with eligible households.

    Args:
        env: SimPy environment.
        households: Iterable of household objects in the simulation.
        field_officer_list: Mutable list that receives eligible households.

    Yields:
        SimPy timeout events that refresh the list once per day.
    """

    yield env.timeout(1.85)
    while True:
        for household in households:
            if (
                household.field_knocks <= household.hard_to_count
                and not household.responded
                and not household.refusal
                and household not in field_officer_list
            ):
                field_officer_list.append(household)
        yield env.timeout(1)

def queue_field_officer_visits(
    env,
    field_officer,
    open_households,
    intervention_lists,
    field_officer_list,
    first_day,
    last_day,
    response_probability_if_no_answer,
    scenario_params,
    random_source,
    doorstep_completion_probability,
    vacancy_probability_if_no_answer,
    days_until_next_visit,
    paper_questionnaire_service,
    field_enabled=True,
    visit_history=None,
):
    """Complete a limited batch of visits at the same time each field day.

    Args:
        env: SimPy environment.
        field_officer: SimPy resource representing officer capacity.
        open_households: Mutable list of active, non-responded households.
        intervention_lists: Object containing all intervention lists.
        field_officer_list: Mutable list of households eligible for visits.
        first_day: First simulation day on which visits are launched.
        last_day: Last simulation day on which visits are launched.
        response_probability_if_no_answer: One-off response probability when
            there is no answer and the household is not marked vacant.
        scenario_params: Weekday calendar, slot hours, visit rate and slot probabilities.
        random_source: Random number generator used by visit processes.
        doorstep_completion_probability: Probability of completing at the door
            when the household answers.
        vacancy_probability_if_no_answer: Probability a no-answer household is
            vacant.
        days_until_next_visit: Days until next visit when no answer and not
            vacant.
        paper_questionnaire_service: Shared paper questionnaire service used
            for ordering and dispatch delays.
        field_enabled: Whether this officer unit performs visits.
        visit_history: Optional list receiving completed visit times, slots and household IDs.

    Yields:
        SimPy timeout events that advance between daily batches.
    """

    if not field_enabled:
        return
    yield env.timeout(first_day)
    for target_day in range(first_day, last_day + 1):
        daily_queue = [
            household
            for household in field_officer_list
            if not household.responded
            and not household.refusal
            and household.is_active
            and household.next_field_visit_day <= target_day
        ]

        offset = 0
        for slot, capacity in scenario_params.field_visit_capacities_at(target_day).items():
            slot_queue = daily_queue[offset:offset + capacity]
            offset += len(slot_queue)
            for household in slot_queue:
                env.process(
                    field_officer_visit(
                        env,
                        field_officer,
                        open_households,
                        intervention_lists,
                        field_officer_list,
                        household,
                        random_source,
                        scenario_params.field_answer_door_probability_by_slot[slot],
                        doorstep_completion_probability,
                        vacancy_probability_if_no_answer,
                        days_until_next_visit,
                        scenario_params.field_visit_response_probability_if_answer_by_slot[slot],
                        response_probability_if_no_answer,
                        paper_questionnaire_service,
                        visit_slot=slot,
                        visit_history=visit_history,
                        visit_mode=scenario_params.field_visit_mode,
                        refusal_probability=scenario_params.refusal_probability,
                        vacancy_probability=scenario_params.field_vacancy_probability,
                        success_probability=scenario_params.field_success_probability_by_slot[slot],
                    )
                )
        yield env.timeout(1)

def field_officer_visit(
    env: simpy.Environment,
    field_officer: simpy.Resource,
    open_households,
    intervention_lists,
    field_officer_list,
    household,
    random_source,
    answer_door_probability,
    doorstep_completion_probability,
    vacancy_probability_if_no_answer,
    days_until_next_visit,
    response_probability_if_answer,
    response_probability_if_no_answer,
    paper_questionnaire_service,
    visit_slot=None,
    visit_history=None,
    visit_mode="detailed",
    refusal_probability=0.01,
    vacancy_probability=0.05,
    success_probability=0.3,
):
    """Complete a field-officer visit without advancing simulation time.

    Args:
        env: SimPy environment.
        field_officer: SimPy resource representing officer capacity.
        open_households: Mutable list of active, non-responded households.
        intervention_lists: Object containing all intervention lists.
        field_officer_list: Mutable list of households eligible for visits.
        household: Household being visited.
        random_source: Random number generator used to determine the outcome.
        answer_door_probability: Probability household answers the door.
        doorstep_completion_probability: Probability of completing at the door
            when the household answers.
        vacancy_probability_if_no_answer: Probability a no-answer household is
            vacant.
        days_until_next_visit: Days until next visit when no answer and not
            vacant.
        response_probability_if_answer: One-off response probability when
            answered-door contact does not lead to doorstep completion or a pQ order.
        response_probability_if_no_answer: One-off response probability when
            there is no answer and the household is not marked vacant.
        paper_questionnaire_service: Shared paper questionnaire service used
            for ordering and dispatch delays.
        visit_slot: Assigned morning, afternoon, evening or weekend label.
        visit_history: Optional list receiving records for visits actually performed.
        visit_mode: Outcome implementation, simple or detailed.
        refusal_probability: Simple per-knock refusal chance.
        vacancy_probability: Simple per-knock vacancy chance.
        success_probability: Simple per-knock ordinary success chance for this slot.

    Yields:
        SimPy resource acquisition at the current simulation time.
    """


  
    with field_officer.request() as request:
        yield request
        if household.responded or household.refusal or not household.is_active:
            return

        household.field_knocks += 1
        if visit_history is not None:
            visit_history.append(
                {"time": env.now, "household_id": household.id, "slot": visit_slot}
            )

        if visit_mode == "simple":
            simple_field_visit_outcome(
                env, household, random_source, doorstep_completion_probability,
                refusal_probability, vacancy_probability, success_probability,
                days_until_next_visit, paper_questionnaire_service,
                open_households, intervention_lists,
            )
        elif visit_mode == "detailed":
            detailed_field_visit_outcome(
                env, household, random_source, answer_door_probability,
                doorstep_completion_probability, vacancy_probability_if_no_answer,
                days_until_next_visit, response_probability_if_answer,
                response_probability_if_no_answer, paper_questionnaire_service,
                open_households, intervention_lists, field_officer_list,
            )
        else:
            raise ValueError(f"Unknown field visit mode: {visit_mode}")

        if household.responded:
            remove_household_from_all_intervention_lists(household, intervention_lists)
            if household in open_households:
                open_households.remove(household)


def simple_field_visit_outcome(
    env, household, rng, doorstep_probability, refusal_probability,
    vacancy_probability, success_probability, revisit_delay, paper_service,
    open_households, intervention_lists,
):
    """Apply one mutually exclusive outcome; awaiting paper permits only doorstep completion."""
    household.next_field_visit_day = int(env.now) + revisit_delay
    draw = rng.random()
    if draw < doorstep_probability:
        household.doorstep_completions += 1
        household.responded = True
    elif household.waiting_for_pq:
        return
    elif draw < doorstep_probability + refusal_probability:
        household.refusal = True
        if household in intervention_lists.field_officer_list:
            intervention_lists.field_officer_list.remove(household)
    elif draw < doorstep_probability + refusal_probability + vacancy_probability:
        remove_vacant_household(household, open_households, intervention_lists)
    elif draw < doorstep_probability + refusal_probability + vacancy_probability + success_probability:
        def complete_success():
            if not household.is_active or household.responded or household.refusal:
                return
            household.responded = True
            household.simple_field_successes += 1
            remove_household_from_all_intervention_lists(household, intervention_lists)
            if household in open_households:
                open_households.remove(household)

        if household.paper_first:
            paper_service.order_paper_questionnaire(env, household, on_delivery=complete_success)
        else:
            complete_success()


def detailed_field_visit_outcome(
    env, household, random_source, answer_door_probability,
    doorstep_completion_probability, vacancy_probability_if_no_answer,
    days_until_next_visit, response_probability_if_answer,
    response_probability_if_no_answer, paper_questionnaire_service,
    open_households, intervention_lists, field_officer_list,
):
    """Apply the original answered-door decision tree."""
    if random_source.random() < answer_door_probability:
        if household.waiting_for_pq:
            household.next_field_visit_day += days_until_next_visit
        else:
            if random_source.random() < doorstep_completion_probability:
                if household in field_officer_list:
                    field_officer_list.remove(household)
                    household.doorstep_completions += 1
                    household.responded = True
            else:
                if household.paper_first and not household.waiting_for_pq:
                    paper_questionnaire_service.order_paper_questionnaire(env, household)
                elif not household.refusal:
                    if random_source.random() < response_probability_if_answer:
                        household.responded = True
                household.next_field_visit_day = int(env.now) + days_until_next_visit
    else:
        if random_source.random() < vacancy_probability_if_no_answer:
            remove_vacant_household(household, open_households, intervention_lists)
        else:
            if not household.paper_first and not household.refusal:
                if random_source.random() < response_probability_if_no_answer:
                    household.responded = True
            household.next_field_visit_day = int(env.now) + days_until_next_visit
                

def end_of_day_remove_responded_houses(env, field_officer_list, first_day):
    """Remove responded households from the field-officer list each day.

    Args:
        env: SimPy environment.
        field_officer_list: Mutable list of households eligible for visits.
        first_day: First simulation day on which field visits begin.

    Yields:
        SimPy timeout events that run the cleanup once per day.
    """

    yield env.timeout(first_day + 0.55)
    while True:
        yield env.timeout(1)
        field_officer_list[:] = [household for household in field_officer_list if not household.responded]
    
    
