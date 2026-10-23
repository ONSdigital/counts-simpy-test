from types import SimpleNamespace
import random

import pytest
import simpy

from functions.functions_contact_centre import PaperQuestionnaireService
from functions.functions_contact_centre import deliver_paper_questionnaire
from functions.functions_contact_centre import process_call_centre_calls


def test_deliver_paper_questionnaire_sets_paper_first_false_for_active_household():
    # This test checks that a delivered paper questionnaire clears waiting state and switches the household away from paper-first.
    env = simpy.Environment()
    household = SimpleNamespace(paper_first=True, waiting_for_pq=True, is_active=True)

    env.process(deliver_paper_questionnaire(env, household, total_delay=2))
    env.run(until=2.1)

    assert household.waiting_for_pq is False
    assert household.paper_first is False


def test_order_paper_questionnaire_uses_stock_and_marks_waiting():
    # This test checks that ordering a paper questionnaire decrements stock and marks the household as waiting for delivery.
    env = simpy.Environment()
    service = PaperQuestionnaireService(initial_paper_batch=1, postal_delay=2, printing_delay=3)
    household = SimpleNamespace(paper_first=True, waiting_for_pq=False, is_active=True)

    service.order_paper_questionnaire(env, household)

    assert household.waiting_for_pq is True
    assert service.paper_stock_remaining == 0


def test_call_centre_calls_switch_paper_first_to_false_and_records_daily_calls():
    # This test checks that call-centre demand triggers questionnaire orders and records the matching daily call count.
    env = simpy.Environment()
    households = [
        SimpleNamespace(paper_first=True, responded=False, waiting_for_pq=False, is_active=True),
        SimpleNamespace(paper_first=True, responded=False, waiting_for_pq=False, is_active=True),
        SimpleNamespace(paper_first=False, responded=False, waiting_for_pq=False, is_active=True),
    ]
    history = {"time": [], "daily_calls": []}
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=10,
        postal_delay=2,
        printing_delay=4,
    )

    env.process(
        process_call_centre_calls(
            env,
            households,
            call_probability=1.0,
            rng=random.Random(1),
            call_centre_history=history,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )

    env.run(until=1.9)

    assert households[0].paper_first is True
    assert households[1].paper_first is True
    assert households[2].paper_first is False
    assert households[0].waiting_for_pq is True
    assert households[1].waiting_for_pq is True
    assert history["time"] == pytest.approx([1.85])
    assert history["daily_calls"] == [2]

    env.run(until=3.9)

    assert households[0].paper_first is False
    assert households[1].paper_first is False
    assert households[0].waiting_for_pq is False
    assert households[1].waiting_for_pq is False


def test_call_centre_ignores_responded_households_even_if_paper_first():
    # This test checks that already responded households are excluded from call-centre calling even when paper-first is true.
    env = simpy.Environment()
    households = [
        SimpleNamespace(paper_first=True, responded=True, waiting_for_pq=False, is_active=True),
        SimpleNamespace(paper_first=True, responded=False, waiting_for_pq=False, is_active=True),
    ]
    history = {"time": [], "daily_calls": []}
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=10,
        postal_delay=2,
        printing_delay=4,
    )

    env.process(
        process_call_centre_calls(
            env,
            households,
            call_probability=1.0,
            rng=random.Random(2),
            call_centre_history=history,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )

    env.run(until=1.9)

    assert households[0].paper_first is True
    assert households[1].paper_first is True
    assert households[1].waiting_for_pq is True
    assert history["daily_calls"] == [1]


def test_households_do_not_call_again_while_waiting_for_postal_delivery():
    # This test checks that households waiting for questionnaire delivery are not counted as repeat calls on subsequent days.
    env = simpy.Environment()
    household = SimpleNamespace(paper_first=True, responded=False, waiting_for_pq=False, is_active=True)
    history = {"time": [], "daily_calls": []}
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=10,
        postal_delay=3,
        printing_delay=4,
    )

    env.process(
        process_call_centre_calls(
            env,
            [household],
            call_probability=1.0,
            rng=random.Random(3),
            call_centre_history=history,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )

    env.run(until=3.1)

    assert household.waiting_for_pq is True
    assert history["daily_calls"] == [1, 0]


def test_out_of_stock_households_use_print_on_demand_delay_before_post():
    # This test checks that out-of-stock orders keep households waiting until printing plus postal delay has elapsed.
    env = simpy.Environment()
    household = SimpleNamespace(paper_first=True, responded=False, waiting_for_pq=False, is_active=True)
    history = {"time": [], "daily_calls": []}
    paper_questionnaire_service = PaperQuestionnaireService(
        initial_paper_batch=0,
        postal_delay=2,
        printing_delay=3,
    )

    env.process(
        process_call_centre_calls(
            env,
            [household],
            call_probability=1.0,
            rng=random.Random(4),
            call_centre_history=history,
            paper_questionnaire_service=paper_questionnaire_service,
        )
    )

    env.run(until=5.1)

    assert household.waiting_for_pq is True
    assert household.paper_first is True

    env.run(until=6.9)

    assert household.waiting_for_pq is False
    assert household.paper_first is False
