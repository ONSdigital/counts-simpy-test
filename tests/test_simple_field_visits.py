import dataclasses as dc
from types import SimpleNamespace

import pytest
import simpy

from functions.functions_contact_centre import PaperQuestionnaireService
from functions.functions_field import field_officer_visit, queue_field_officer_visits
from functions.simulation_runner import run_monte_carlo
from parameters import FIELD_VISIT_SLOTS, RegionParameters, SimulationParameters


class SequenceRandom:
    def __init__(self, draws):
        self.draws = list(draws)

    def random(self):
        return self.draws.pop(0)


def start_visit(draw, *, paper_first=False, waiting=False, stock=1, mode="simple", refusal=False):
    env = simpy.Environment()
    household = SimpleNamespace(
        id=1, responded=False, refusal=refusal, is_active=True,
        paper_first=paper_first, waiting_for_pq=waiting,
        field_knocks=0, doorstep_completions=0, simple_field_successes=0,
        next_field_visit_day=0,
    )
    open_households = [household]
    lists = SimpleNamespace(
        sms_list=[household], field_officer_list=[household], reminder_card_list=[household],
    )
    service = PaperQuestionnaireService(stock, 2, 3)
    history = []
    rng = SequenceRandom([draw])
    env.process(field_officer_visit(
        env, simpy.Resource(env, capacity=1), open_households, lists, lists.field_officer_list,
        household, rng, answer_door_probability=1.0,
        doorstep_completion_probability=0.2, vacancy_probability_if_no_answer=0.1,
        days_until_next_visit=3, response_probability_if_answer=0.3,
        response_probability_if_no_answer=0.2, paper_questionnaire_service=service,
        visit_slot="morning", visit_history=history, visit_mode=mode,
        refusal_probability=0.1, vacancy_probability=0.1, success_probability=0.3,
    ))
    return env, household, open_households, lists, service, history, rng


@pytest.mark.parametrize(
    "draw,outcome",
    [(0.0, "doorstep"), (0.199, "doorstep"), (0.2, "refusal"),
     (0.299, "refusal"), (0.301, "vacancy"), (0.399, "vacancy"),
     (0.401, "success"), (0.699, "success"), (0.701, "none"), (0.999, "none")],
)
def test_simple_outcomes_use_one_mutually_exclusive_draw(draw, outcome):
    env, house, open_houses, lists, _, history, rng = start_visit(draw)
    env.run()

    assert house.field_knocks == 1
    assert history == [{"time": 0, "household_id": 1, "slot": "morning"}]
    assert rng.draws == []
    assert house.doorstep_completions == (outcome == "doorstep")
    assert house.simple_field_successes == (outcome == "success")
    assert house.responded == (outcome in ("doorstep", "success"))
    assert house.refusal == (outcome == "refusal")
    assert house.is_active == (outcome != "vacancy")
    if outcome in ("doorstep", "success", "vacancy"):
        assert house not in open_houses
        assert all(house not in entries for entries in vars(lists).values())
    elif outcome == "refusal":
        assert house in open_houses
        assert house not in lists.field_officer_list
    else:
        assert house in lists.field_officer_list
        assert house.next_field_visit_day == 3


@pytest.mark.parametrize("stock,delivery_time", [(1, 2), (0, 5)])
def test_paper_success_uses_shared_stock_and_completes_only_at_delivery(stock, delivery_time):
    env, house, open_houses, lists, service, _, _ = start_visit(0.5, paper_first=True, stock=stock)
    env.run(until=delivery_time - 0.01)
    assert not house.responded
    assert house.waiting_for_pq
    assert house.simple_field_successes == 0
    assert service.paper_stock_remaining == 0
    env.run(until=delivery_time + 0.01)
    assert house.responded
    assert house.simple_field_successes == 1
    assert house.doorstep_completions == 0
    assert not house.waiting_for_pq
    assert not house.paper_first
    assert house not in open_houses
    assert all(house not in entries for entries in vars(lists).values())


@pytest.mark.parametrize("draw", [0.25, 0.35, 0.5, 0.9])
def test_awaiting_paper_skips_all_non_doorstep_outcomes(draw):
    env, house, _, _, service, _, _ = start_visit(draw, paper_first=True, waiting=True)
    env.run()
    assert not house.responded and not house.refusal and house.is_active
    assert house.waiting_for_pq
    assert house.next_field_visit_day == 3
    assert service.paper_stock_remaining == 1


def test_awaiting_paper_can_complete_at_doorstep_without_ordering_more_paper():
    env, house, _, _, service, _, _ = start_visit(0.1, paper_first=True, waiting=True)
    env.run()
    assert house.responded
    assert house.doorstep_completions == 1
    assert house.simple_field_successes == 0
    assert service.paper_stock_remaining == 1


@pytest.mark.parametrize("change", ["responded", "refusal", "vacant"])
def test_pending_paper_success_does_not_double_count_or_revive_households(change):
    env, house, _, _, _, _, _ = start_visit(0.5, paper_first=True)
    env.run(until=1)
    if change == "vacant":
        house.is_active = False
    else:
        setattr(house, change, True)
    env.run()
    assert house.simple_field_successes == 0
    if change != "responded":
        assert not house.responded


@pytest.mark.parametrize("mode", ["simple", "detailed"])
def test_refusing_households_do_not_consume_a_visit_or_a_draw(mode):
    env, house, _, _, _, history, rng = start_visit(0.5, mode=mode, refusal=True)
    env.run()
    assert house.field_knocks == 0
    assert history == []
    assert rng.draws == [0.5]


@pytest.mark.parametrize("slot", FIELD_VISIT_SLOTS)
@pytest.mark.parametrize("success", [0.0, 1.0])
def test_simple_scheduler_uses_slot_success_and_not_detailed_probabilities(slot, success):
    params = SimulationParameters(
        census_start_weekday="Saturday" if slot == "weekend" else "Monday",
        field_officer_working_hours_by_slot={
            name: float(name == slot) for name in FIELD_VISIT_SLOTS
        },
        field_officer_visits_per_hour=1.0,
        field_doorstep_completion_probability=0.0,
        refusal_probability=0.0, field_vacancy_probability=0.0,
        field_success_probability_by_slot={
            name: success if name == slot else 1.0 - success for name in FIELD_VISIT_SLOTS
        },
        field_answer_door_probability_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 0.0),
    )
    env, house, open_houses, lists, service, history, _ = start_visit(0.9, refusal=True)
    env.run()
    house.refusal = False
    rng = SequenceRandom([0.5])
    env.process(queue_field_officer_visits(
        env, simpy.Resource(env, capacity=1), open_houses, lists, lists.field_officer_list,
        first_day=0, last_day=0, response_probability_if_no_answer=0.0,
        scenario_params=params, random_source=rng, doorstep_completion_probability=0.0,
        vacancy_probability_if_no_answer=0.0, days_until_next_visit=3,
        paper_questionnaire_service=service, visit_history=history,
    ))
    env.run()
    assert house.responded == bool(success)
    assert house.simple_field_successes == success
    assert history[0]["slot"] == slot


@pytest.mark.parametrize("mode", ["invalid", "", None])
def test_mode_validation(mode):
    with pytest.raises(ValueError, match="field_visit_mode"):
        SimulationParameters(field_visit_mode=mode)


@pytest.mark.parametrize(
    "name",
    ["refusal_probability", "field_vacancy_probability", "field_doorstep_completion_probability"],
)
@pytest.mark.parametrize("value", [-0.1, 1.1, True, None, float("nan"), float("inf")])
def test_simple_scalar_probability_validation(name, value):
    with pytest.raises(ValueError, match=name):
        SimulationParameters(**{name: value})


def test_simple_probability_sum_and_detailed_independence():
    assert SimulationParameters().field_visit_mode == "simple"
    with pytest.raises(ValueError, match="evening.*sum"):
        SimulationParameters(field_success_probability_by_slot={
            "morning": 0.3, "afternoon": 0.3, "evening": 0.9, "weekend": 0.3,
        })
    SimulationParameters(
        field_visit_mode="detailed", field_doorstep_completion_probability=1.0,
        field_success_probability_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 1.0),
    )


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), True, None])
def test_simple_slot_success_validation(value):
    with pytest.raises(ValueError, match="field_success_probability_by_slot"):
        SimulationParameters(field_success_probability_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, value))


def test_simple_success_requires_all_four_slot_keys():
    with pytest.raises(ValueError, match="field_success_probability_by_slot"):
        SimulationParameters(field_success_probability_by_slot={"morning": 0.3})


def test_simple_refusals_are_not_readded_or_revisited_in_later_days():
    from functions.simulation_runner import run_simulation

    params = SimulationParameters(
        regions={"Test": RegionParameters(4, 1)},
        field_first_day=3, field_last_day=10, field_days_until_next_visit=0,
        field_officer_visits_per_hour=4.0,
        refusal_probability=1.0, field_vacancy_probability=0.0,
        field_doorstep_completion_probability=0.0,
        field_success_probability_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 0.0),
        daily_response_probabilities_by_group=dict.fromkeys(("A", "B", "C"), [0.0] * 50),
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
        sms_days=[100], reminder_letter_days=[],
    )
    run = run_simulation(params, run_until=11, generate_plot=False)
    assert all(house.refusal and house.field_knocks == 1 for house in run.units[0].households)
    assert run.units[0].intervention_lists.field_officer_list == []


@pytest.mark.parametrize("paper_probability", [0.0, 1.0])
def test_monte_carlo_tracks_simple_and_doorstep_successes_separately(paper_probability):
    params = SimulationParameters(
        regions={"Test": RegionParameters(4, 1)}, monte_carlo_repeats=2,
        field_first_day=3, field_last_day=3, field_officer_visits_per_hour=4.0,
        field_officer_working_hours_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 1.0),
        refusal_probability=0.0, field_vacancy_probability=0.0,
        field_doorstep_completion_probability=0.0,
        field_success_probability_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 1.0),
        daily_response_probabilities_by_group=dict.fromkeys(("A", "B", "C"), [0.0] * 50),
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), paper_probability),
        call_centre_call_probability=0.0,
        sms_days=[100], reminder_letter_days=[],
    )
    result = run_monte_carlo(params, run_until=7, generate_plot=False)
    assert result.params.field_visit_mode == "simple"
    assert result.overall_summary["simple_field_successes"] == {"mean": 4, "lower_95": 4, "upper_95": 4}
    assert result.region_summaries["Test"]["simple_field_successes"]["mean"] == 4
    assert result.overall_summary["doorstep_completions"]["mean"] == 0
    assert result.overall_summary["responded_count"]["mean"] == 4
    doorstep = run_monte_carlo(
        dc.replace(
            params, field_success_probability_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 0.0),
            field_doorstep_completion_probability=1.0,
        ), run_until=5, generate_plot=False,
    )
    assert doorstep.overall_summary["simple_field_successes"]["mean"] == 0
    assert doorstep.overall_summary["doorstep_completions"]["mean"] == 4
