from types import SimpleNamespace

import simpy

from functions.functions_contact_centre import PaperQuestionnaireService
from functions.functions_field import create_field_officer
from functions.functions_field import end_of_day_remove_responded_houses
from functions.functions_field import field_officer_visit
from functions.functions_field import populate_field_officer_list
from functions.functions_field import queue_field_officer_visits
from functions.functions_field import remove_household_from_all_intervention_lists
from functions.functions_field import remove_vacant_household


class SequenceRandom:
    def __init__(self, draws):
        self._draws = list(draws)

    def random(self):
        return self._draws.pop(0)


def test_remove_household_from_all_intervention_lists_removes_all_occurrences():
    # This test checks that removing a household clears it from every intervention list, including duplicates.
    household = SimpleNamespace(id=10)
    intervention_lists = SimpleNamespace(
        sms_list=[household, household],
        field_officer_list=[household],
        reminder_card_list=[household],
    )

    remove_household_from_all_intervention_lists(household, intervention_lists)

    assert intervention_lists.sms_list == []
    assert intervention_lists.field_officer_list == []
    assert intervention_lists.reminder_card_list == []


def test_remove_vacant_household_marks_inactive_and_removes_from_open_households():
    # This test checks that marking a household vacant sets inactive flags and removes it from open and intervention collections.
    household = SimpleNamespace(id=11, is_active=True, waiting_for_pq=True)
    open_households = [household]
    intervention_lists = SimpleNamespace(
        sms_list=[household],
        field_officer_list=[household],
        reminder_card_list=[household],
    )

    remove_vacant_household(household, open_households, intervention_lists)

    assert household.is_active is False
    assert household.waiting_for_pq is False
    assert open_households == []
    assert intervention_lists.sms_list == []
    assert intervention_lists.field_officer_list == []
    assert intervention_lists.reminder_card_list == []


def test_create_field_officer_returns_single_capacity_resource():
    # This test checks that the field officer helper creates a SimPy resource with capacity one.
    env = simpy.Environment()
    resource = create_field_officer(env)

    assert isinstance(resource, simpy.Resource)
    assert resource.capacity == 1


def test_queue_field_officer_visits_schedules_visit_within_active_window():
    # This test checks that queueing launches a visit for eligible households between first and last active days.
    env = simpy.Environment()
    field_officer = simpy.Resource(env, capacity=1)
    household = SimpleNamespace(
        id=12,
        responded=False,
        paper_first=False,
        waiting_for_pq=False,
        response_probability=0.1,
        next_field_visit_day=0,
        field_knocks=0,
        is_active=True,
        doorstep_completions=0,
    )
    open_households = [household]
    field_officer_list = [household]
    intervention_lists = SimpleNamespace(
        sms_list=[],
        field_officer_list=field_officer_list,
        reminder_card_list=[],
    )
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=1,
        postal_delay=2,
        printing_delay=1,
    )

    env.process(
        queue_field_officer_visits(
            env,
            field_officer,
            open_households,
            intervention_lists,
            field_officer_list,
            first_day=1,
            last_day=1,
            visit_duration=0.1,
            response_probability_increase_if_answer=0.2,
            response_probability_increase_if_no_answer=0.1,
            queue_size=1,
            random_source=SequenceRandom([0.9, 0.9]),
            answer_door_probability=0.5,
            doorstep_completion_probability=0.5,
            vacancy_probability_if_no_answer=0.1,
            days_until_next_visit=3,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )
    env.run(until=2)

    assert household.field_knocks == 1


def test_end_of_day_remove_responded_houses_filters_list_after_first_day():
    # This test checks that the end-of-day cleanup removes responded households from the visit list after field start day.
    env = simpy.Environment()
    responded_household = SimpleNamespace(responded=True)
    open_household = SimpleNamespace(responded=False)
    field_officer_list = [responded_household, open_household]

    env.process(end_of_day_remove_responded_houses(env, field_officer_list, first_day=2))
    env.run(until=3.7)

    assert responded_household not in field_officer_list
    assert open_household in field_officer_list


def test_vacant_household_is_removed_from_population_and_all_lists():
    # This test checks that a no-answer vacancy outcome removes the household from active population and all intervention lists.
    env = simpy.Environment()
    field_officer = simpy.Resource(env, capacity=1)

    household = SimpleNamespace(id=1, responded=False, field_knocks=0, doorstep_completions=0)
    households = [household]
    intervention_lists = SimpleNamespace(
        sms_list=[household],
        field_officer_list=[household],
        reminder_card_list=[household],
    )
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=10,
        postal_delay=2,
        printing_delay=1,
    )

    env.process(
        field_officer_visit(
            env,
            field_officer,
            households,
            intervention_lists,
            intervention_lists.field_officer_list,
            household,
            visit_duration=0.1,
            random_source=SequenceRandom([0.9, 0.05]),
            answer_door_probability=0.5,
            doorstep_completion_probability=0.5,
            vacancy_probability_if_no_answer=0.1,
            days_until_next_visit=4,
            response_probability_increase_if_answer=0.2,
            response_probability_increase_if_no_answer=0.2,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )
    env.run(until=1)

    assert household not in households
    assert household not in intervention_lists.sms_list
    assert household not in intervention_lists.field_officer_list
    assert household not in intervention_lists.reminder_card_list
    assert household.field_knocks == 1


def test_no_answer_non_vacant_household_is_scheduled_for_revisit():
    # This test checks that a no-answer non-vacant visit schedules a future revisit day instead of removing the household.
    env = simpy.Environment()
    field_officer = simpy.Resource(env, capacity=1)

    household = SimpleNamespace(
        id=2,
        responded=False,
        paper_first=True,
        waiting_for_pq=False,
        response_probability=0.05,
        field_knocks=0,
        doorstep_completions=0,
    )
    households = [household]
    intervention_lists = SimpleNamespace(
        sms_list=[],
        field_officer_list=[household],
        reminder_card_list=[],
    )
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=10,
        postal_delay=2,
        printing_delay=1,
    )

    env.process(
        field_officer_visit(
            env,
            field_officer,
            households,
            intervention_lists,
            intervention_lists.field_officer_list,
            household,
            visit_duration=0.1,
            random_source=SequenceRandom([0.9, 0.9, 0.9]),
            answer_door_probability=0.5,
            doorstep_completion_probability=0.5,
            vacancy_probability_if_no_answer=0.1,
            days_until_next_visit=6,
            response_probability_increase_if_answer=0.2,
            response_probability_increase_if_no_answer=0.2,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )
    env.run(until=1)

    assert household in households
    assert household.responded is False
    assert household.next_field_visit_day == 6
    assert household.waiting_for_pq is False


def test_answer_door_keeps_outcome_a_behaviour():
    # This test checks that an answered door followed by doorstep completion marks the household as responded and removes it from field queue.
    env = simpy.Environment()
    field_officer = simpy.Resource(env, capacity=1)

    household = SimpleNamespace(
        id=3,
        responded=False,
        paper_first=False,
        waiting_for_pq=False,
        response_probability=0.05,
        field_knocks=0,
        doorstep_completions=0,
    )
    households = [household]
    intervention_lists = SimpleNamespace(
        sms_list=[],
        field_officer_list=[household],
        reminder_card_list=[],
    )
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=10,
        postal_delay=2,
        printing_delay=1,
    )

    env.process(
        field_officer_visit(
            env,
            field_officer,
            households,
            intervention_lists,
            intervention_lists.field_officer_list,
            household,
            visit_duration=0.1,
            random_source=SequenceRandom([0.1, 0.1]),
            answer_door_probability=0.5,
            doorstep_completion_probability=0.5,
            vacancy_probability_if_no_answer=0.1,
            days_until_next_visit=4,
            response_probability_increase_if_answer=0.2,
            response_probability_increase_if_no_answer=0.2,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )
    env.run(until=1)

    assert household.responded is True
    assert household not in intervention_lists.field_officer_list
    assert household.field_knocks == 1


def test_answer_no_completion_orders_pq_when_paper_first_and_not_waiting():
    # This test checks that answered-door households that are paper-first and not waiting are sent a paper questionnaire when no completion occurs.
    env = simpy.Environment()
    field_officer = simpy.Resource(env, capacity=1)

    household = SimpleNamespace(
        id=4,
        responded=False,
        paper_first=True,
        waiting_for_pq=False,
        response_probability=0.05,
        field_knocks=0,
        doorstep_completions=0,
    )
    households = [household]
    intervention_lists = SimpleNamespace(
        sms_list=[],
        field_officer_list=[household],
        reminder_card_list=[],
    )
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=1,
        postal_delay=2,
        printing_delay=1,
    )

    env.process(
        field_officer_visit(
            env,
            field_officer,
            households,
            intervention_lists,
            intervention_lists.field_officer_list,
            household,
            visit_duration=0.1,
            random_source=SequenceRandom([0.1, 0.9]),
            answer_door_probability=0.5,
            doorstep_completion_probability=0.5,
            vacancy_probability_if_no_answer=0.1,
            days_until_next_visit=5,
            response_probability_increase_if_answer=0.2,
            response_probability_increase_if_no_answer=0.2,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )

    env.run(until=1)

    assert household.waiting_for_pq is True
    assert household.next_field_visit_day == 5
    assert household.field_knocks == 1


def test_answer_no_completion_increases_response_probability_when_no_pq_order():
    # This test checks that answered-door households not requiring paper orders receive the configured response-probability boost.
    env = simpy.Environment()
    field_officer = simpy.Resource(env, capacity=1)

    household = SimpleNamespace(
        id=5,
        responded=False,
        paper_first=False,
        waiting_for_pq=False,
        response_probability=0.05,
        field_knocks=0,
        doorstep_completions=0,
    )
    households = [household]
    intervention_lists = SimpleNamespace(
        sms_list=[],
        field_officer_list=[household],
        reminder_card_list=[],
    )
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=1,
        postal_delay=2,
        printing_delay=1,
    )

    env.process(
        field_officer_visit(
            env,
            field_officer,
            households,
            intervention_lists,
            intervention_lists.field_officer_list,
            household,
            visit_duration=0.1,
            random_source=SequenceRandom([0.1, 0.9]),
            answer_door_probability=0.5,
            doorstep_completion_probability=0.5,
            vacancy_probability_if_no_answer=0.1,
            days_until_next_visit=5,
            response_probability_increase_if_answer=0.2,
            response_probability_increase_if_no_answer=0.2,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )
    env.run(until=1)

    assert household.response_probability == 0.25
    assert household.next_field_visit_day == 5
    assert household.field_knocks == 1


def test_answering_door_while_waiting_for_pq_increments_next_visit_day():
    # This test checks that households already waiting for paper are deferred to a later visit day when the door is answered.
    env = simpy.Environment()
    field_officer = simpy.Resource(env, capacity=1)

    household = SimpleNamespace(
        id=6,
        responded=False,
        paper_first=True,
        waiting_for_pq=True,
        response_probability=0.05,
        next_field_visit_day=7,
        field_knocks=0,
        doorstep_completions=0,
    )
    households = [household]
    intervention_lists = SimpleNamespace(
        sms_list=[],
        field_officer_list=[household],
        reminder_card_list=[],
    )
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=1,
        postal_delay=2,
        printing_delay=1,
    )

    env.process(
        field_officer_visit(
            env,
            field_officer,
            households,
            intervention_lists,
            intervention_lists.field_officer_list,
            household,
            visit_duration=0.1,
            random_source=SequenceRandom([0.1]),
            answer_door_probability=0.5,
            doorstep_completion_probability=0.5,
            vacancy_probability_if_no_answer=0.1,
            days_until_next_visit=5,
            response_probability_increase_if_answer=0.2,
            response_probability_increase_if_no_answer=0.2,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )
    env.run(until=1)

    assert household.responded is False
    assert household.waiting_for_pq is True
    assert household.response_probability == 0.05
    assert household.next_field_visit_day == 12
    assert household in intervention_lists.field_officer_list
    assert household.field_knocks == 1


def test_populate_field_officer_list_only_adds_households_when_knocks_are_at_or_below_threshold():
    # This test checks that field list population includes only non-responded households with knocks at or below hard-to-count threshold.
    env = simpy.Environment()
    field_officer_list = []
    households = [
        SimpleNamespace(hard_to_count=2, field_knocks=3, responded=False),
        SimpleNamespace(hard_to_count=2, field_knocks=2, responded=False),
        SimpleNamespace(hard_to_count=2, field_knocks=1, responded=False),
        SimpleNamespace(hard_to_count=1, field_knocks=4, responded=True),
    ]

    env.process(populate_field_officer_list(env, households, field_officer_list))
    env.run(until=1.9)

    assert len(field_officer_list) == 2
    assert households[1] in field_officer_list
    assert households[2] in field_officer_list
