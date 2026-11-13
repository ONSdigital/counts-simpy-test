from types import SimpleNamespace
from unittest.mock import Mock
import random

import pytest
import simpy

from functions.functions_contact_centre import PaperQuestionnaireService
from functions.functions_contact_centre import deliver_paper_questionnaire
from functions.functions_contact_centre import process_call_centre_calls


def test_deliver_paper_questionnaire_sets_paper_first_false_for_active_household():
    # This test checks that a delivered paper questionnaire clears waiting state and switches the household away from paper-first.
    env = simpy.Environment()
    household = SimpleNamespace(
        paper_first=True, waiting_for_pq=True, is_active=True, responded=False,
    )

    env.process(deliver_paper_questionnaire(env, household, total_delay=2))
    env.run(until=2.1)

    assert household.waiting_for_pq is False
    assert household.paper_first is False
    assert household.responded is False


@pytest.mark.parametrize("active", [True, False])
def test_paper_delivery_calls_completion_only_for_active_recipients_after_arrival(active):
    env = simpy.Environment()
    household = SimpleNamespace(
        paper_first=True, waiting_for_pq=True, is_active=active,
    )
    states_at_completion = []
    env.process(
        deliver_paper_questionnaire(
            env, household, total_delay=2,
            on_delivery=lambda: states_at_completion.append(
                (env.now, household.paper_first, household.waiting_for_pq)
            ),
        )
    )

    env.run(until=1.9)
    assert states_at_completion == []
    assert household.waiting_for_pq is True
    env.run(until=2.1)

    assert household.waiting_for_pq is False
    assert states_at_completion == ([(2, False, False)] if active else [])


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
        SimpleNamespace(paper_first=True, responded=False, refusal=False, waiting_for_pq=False, is_active=True),
        SimpleNamespace(paper_first=True, responded=False, refusal=False, waiting_for_pq=False, is_active=True),
        SimpleNamespace(paper_first=False, responded=False, refusal=False, waiting_for_pq=False, is_active=True),
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
    assert households[0].responded is False
    assert households[1].responded is False


def test_call_centre_ignores_responded_households_even_if_paper_first():
    # This test checks that already responded households are excluded from call-centre calling even when paper-first is true.
    env = simpy.Environment()
    households = [
        SimpleNamespace(paper_first=True, responded=True, refusal=False, waiting_for_pq=False, is_active=True),
        SimpleNamespace(paper_first=True, responded=False, refusal=False, waiting_for_pq=False, is_active=True),
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
    household = SimpleNamespace(paper_first=True, responded=False, refusal=False, waiting_for_pq=False, is_active=True)
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
    household = SimpleNamespace(paper_first=True, responded=False, refusal=False, waiting_for_pq=False, is_active=True)
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


@pytest.mark.parametrize("nested", [False, True])
def test_call_centre_excludes_refusing_households_without_using_paper_stock(nested):
    env = simpy.Environment()
    refusing = SimpleNamespace(
        paper_first=True, responded=False, refusal=True,
        waiting_for_pq=False, is_active=True,
    )
    eligible = SimpleNamespace(
        paper_first=True, responded=False, refusal=False,
        waiting_for_pq=False, is_active=True,
    )
    households = [[refusing], [eligible]] if nested else [refusing, eligible]
    history = {"time": [], "daily_calls": []}
    service = PaperQuestionnaireService(
        initial_paper_batch=2, postal_delay=10, printing_delay=4,
    )
    env.process(
        process_call_centre_calls(
            env, households, call_probability=1.0, rng=random.Random(5),
            call_centre_history=history, paper_questionnaire_service=service,
        )
    )

    env.run(until=3.9)

    assert refusing.waiting_for_pq is False
    assert refusing.paper_first is True
    assert eligible.waiting_for_pq is True
    assert service.paper_stock_remaining == 1
    assert history["daily_calls"] == [1, 0, 0]


def test_call_centre_rechecks_refusal_before_each_daily_call_opportunity():
    env = simpy.Environment()
    household = SimpleNamespace(
        paper_first=True, responded=False, refusal=False,
        waiting_for_pq=False, is_active=True,
    )
    history = {"time": [], "daily_calls": []}
    service = PaperQuestionnaireService(
        initial_paper_batch=2, postal_delay=10, printing_delay=4,
    )
    rng = Mock()
    rng.random.side_effect = [1.0, 0.0]
    env.process(
        process_call_centre_calls(
            env, [household], call_probability=0.5, rng=rng,
            call_centre_history=history, paper_questionnaire_service=service,
        )
    )
    env.run(until=1.9)
    household.refusal = True
    env.run(until=2.9)

    assert household.waiting_for_pq is False
    assert service.paper_stock_remaining == 2
    assert history["daily_calls"] == [0, 0]
    assert rng.random.call_count == 1


def test_one_call_centre_and_paper_stock_serve_all_regions():
    import dataclasses as dc

    from functions.simulation_runner import run_simulation
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={
            "North East": RegionParameters(4, 0),
            "Wales": RegionParameters(6, 0),
        },
        daily_response_probabilities_by_group={group: [0.0] * 50 for group in ("A", "B", "C")},
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 1.0),
        call_centre_call_probability=1.0,
        initial_paper_batch=3,
        pQ_postal_delay=1,
        printing_delay=5,
    )

    result = run_simulation(params, run_until=3, generate_plot=False)
    households = [household for region in result.regions for household in region.households]

    assert result.call_centre_history["time"] == pytest.approx([1.85, 2.85])
    assert result.call_centre_history["daily_calls"] == [10, 0]
    assert sum(not household.paper_first for household in households) == 3
    assert sum(household.waiting_for_pq for household in households) == 7


def test_monte_carlo_repeats_reset_shared_call_centre_and_paper_stock():
    import dataclasses as dc

    from functions.simulation_runner import run_monte_carlo
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={"North East": RegionParameters(4, 0), "Wales": RegionParameters(6, 0)},
        monte_carlo_repeats=3,
        daily_response_probabilities_by_group={group: [1.0] * 50 for group in ("A", "B", "C")},
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 1.0),
        call_centre_call_probability=1.0,
        initial_paper_batch=3,
        pQ_postal_delay=1,
        printing_delay=5,
    )

    result = run_monte_carlo(params, run_until=4, generate_plot=False)

    assert result.overall_summary["total_calls"] == {"mean": 10, "lower_95": 10, "upper_95": 10}
    assert result.overall_summary["responded_count"] == {"mean": 3, "lower_95": 3, "upper_95": 3}
    assert result.call_centre_history["daily_calls"] == [10, 0, 0]


def test_call_centre_seed_follows_unit_seeds_across_repeats(monkeypatch):
    import dataclasses as dc

    from functions.simulation_runner import run_monte_carlo
    from parameters import RegionParameters, baseline_parameters

    states = []

    def capture_calls(env, open_lists, probability, rng, history, paper_service):
        states.append(rng.getstate())
        yield env.timeout(1)

    monkeypatch.setattr("functions.functions_contact_centre.process_call_centre_calls", capture_calls)
    params = dc.replace(
        baseline_parameters,
        regions={"North East": RegionParameters(0, 2), "Wales": RegionParameters(0, 0)},
        monte_carlo_repeats=3,
        seed=7,
    )
    result = run_monte_carlo(params, run_until=1, generate_plot=False)
    unit_count = 3
    assert states == [random.Random(seed + unit_count).getstate() for seed in result.run_seeds]
    assert len(set(states)) == 3
    unit_states = {
        random.Random(seed + unit_id).getstate()
        for seed in result.run_seeds
        for unit_id in range(unit_count)
    }
    assert not unit_states.intersection(states)


def test_call_centre_seed_uses_maximum_unit_id_above_10000(monkeypatch):
    import dataclasses as dc
    from types import SimpleNamespace

    from functions.functions_output import initialise_household_return_history
    from functions.simulation_runner import run_simulation
    from parameters import RegionParameters, baseline_parameters

    states = []

    def build_test_region(env, name, *args):
        units = [
            SimpleNamespace(
                unit_id=unit_id, households=[], open_households=[],
                return_history=initialise_household_return_history([]),
            )
            for unit_id in (10_000, 0)
        ]
        return SimpleNamespace(name=name, units=units, return_history={})

    def capture_calls(env, open_lists, probability, rng, history, paper_service):
        states.append(rng.getstate())
        yield env.timeout(1)

    monkeypatch.setattr("functions.simulation_runner.build_region", build_test_region)
    monkeypatch.setattr("functions.functions_contact_centre.process_call_centre_calls", capture_calls)
    params = dc.replace(baseline_parameters, regions={"Wales": RegionParameters(0, 0)}, seed=7)
    run_simulation(params, run_until=1, generate_plot=False)
    assert states == [random.Random(7 + 10_000 + 1).getstate()]
    assert states[0] != random.Random(7 + 10_000).getstate()
