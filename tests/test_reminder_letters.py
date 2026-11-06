import dataclasses as dc
from types import SimpleNamespace

import pytest
import simpy

from functions.functions_reminder_letters import send_reminder_letters
from functions.simulation_runner import run_monte_carlo, run_simulation
from parameters import FIELD_VISIT_SLOTS, RegionParameters, SimulationParameters


class SequenceRandom:
    def __init__(self, draws):
        self.draws = iter(draws)

    def random(self):
        return next(self.draws)


def household(identifier, **kwargs):
    values = dict(
        id=identifier, is_active=True, responded=False, paper_first=False, refusal=False,
    )
    values.update(kwargs)
    return SimpleNamespace(**values)


def start_letters(households, days, delay=3, probability=0.4, draws=()):
    env = simpy.Environment()
    open_households = [house for house in households if house.is_active and not house.responded]
    lists = SimpleNamespace(
        sms_list=list(open_households), field_officer_list=list(open_households),
        reminder_card_list=list(open_households),
    )
    history = {
        "time": [], "letters_sent": [], "total_letters_sent": 0,
        "letters_delivered": 0, "responses": 0,
    }
    env.process(
        send_reminder_letters(
            env, households, days, delay, probability, SequenceRandom(draws),
            open_households, lists, history,
        )
    )
    return env, open_households, lists, history


def test_letters_posted_on_each_day_and_responses_wait_for_postal_delay():
    houses = [household(0), household(1)]
    env, open_houses, lists, history = start_letters(
        houses, [5, 1], draws=[0.1, 0.9, 0.1],
    )
    env.run(until=4.84)
    assert history["time"] == [1.85]
    assert history["letters_sent"] == [2]
    assert not any(house.responded for house in houses)
    env.run(until=4.86)
    assert [house.responded for house in houses] == [True, False]
    assert houses[0] not in open_houses
    assert houses[0] not in lists.field_officer_list
    assert houses[0] not in lists.sms_list
    assert houses[0] not in lists.reminder_card_list
    env.run(until=8.86)
    assert history == {
        "time": [1.85, 5.85], "letters_sent": [2, 1], "total_letters_sent": 3,
        "letters_delivered": 3, "responses": 2,
    }


def test_all_nonrespondents_receive_letters_but_paper_first_and_refusals_cannot_respond():
    houses = [
        household(0), household(1, paper_first=True), household(2, refusal=True),
        household(3, responded=True), household(4, is_active=False),
    ]
    env, _, _, history = start_letters(houses, [0], delay=0, probability=1.0, draws=[0.0])
    env.run()
    assert history["total_letters_sent"] == history["letters_delivered"] == 3
    assert history["responses"] == 1
    assert [house.responded for house in houses] == [True, False, False, True, False]


def test_delivery_rechecks_vacancy_and_response_and_keeps_sent_count():
    houses = [household(0), household(1), household(2, paper_first=True)]
    env, _, _, history = start_letters(houses, [1], probability=1.0, draws=[0.0])
    env.run(until=2)
    houses[0].is_active = False
    houses[1].responded = True
    houses[2].paper_first = False
    env.run()
    assert history["total_letters_sent"] == 3
    assert history["letters_delivered"] == 2
    assert history["responses"] == 1
    assert not houses[0].responded
    assert houses[2].responded


def test_empty_sending_days_disable_letters():
    env, _, _, history = start_letters([household(0)], [])
    env.run()
    assert history["total_letters_sent"] == 0
    assert history["time"] == []


def test_overlapping_mailings_and_failed_draws_each_make_one_delivery_attempt():
    houses = [household(0)]
    env, _, _, history = start_letters(houses, [0, 1], probability=0.4, draws=[0.4, 0.1])
    env.run()
    assert history["total_letters_sent"] == history["letters_delivered"] == 2
    assert history["responses"] == 1
    assert houses[0].responded


@pytest.mark.parametrize("days", [[-1], [True], [1.5], [1, 1], None, [float("nan")]])
def test_parameters_reject_invalid_letter_days(days):
    with pytest.raises(ValueError, match="reminder_letter_days"):
        SimulationParameters(reminder_letter_days=days)


@pytest.mark.parametrize("value", [-0.1, 1.1, True, float("nan"), float("inf"), None])
def test_parameters_reject_invalid_letter_response_probabilities(value):
    with pytest.raises(ValueError, match="reminder_letter_response_probability"):
        SimulationParameters(reminder_letter_response_probability=value)


@pytest.mark.parametrize("value", [-1, True, float("nan"), float("inf"), None])
def test_parameters_reject_invalid_postal_delays(value):
    with pytest.raises(ValueError, match="pQ_postal_delay"):
        SimulationParameters(pQ_postal_delay=value)


def reminder_scenario(**kwargs):
    values = dict(
        regions={"Test": RegionParameters(4, 1)},
        field_visit_mode="detailed",
        monte_carlo_repeats=2,
        daily_response_probabilities_by_group=dict.fromkeys(("A", "B", "C"), [0.0] * 50),
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
        reminder_letter_days=[3], reminder_letter_response_probability=1.0,
        pQ_postal_delay=2, printing_delay=100, initial_paper_batch=0,
        field_first_day=100, sms_timing=100,
    )
    values.update(kwargs)
    return SimulationParameters(**values)


def test_runner_uses_postal_delay_not_printing_delay_and_tracks_sent_before_delivery():
    params = reminder_scenario()
    before_delivery = run_simulation(params, run_until=4, generate_plot=False)
    assert before_delivery.units[0].reminder_letter_history["total_letters_sent"] == 4
    assert before_delivery.units[0].reminder_letter_history["letters_delivered"] == 0
    assert not any(house.responded for house in before_delivery.units[0].households)
    delivered = run_simulation(params, run_until=5.9, generate_plot=False)
    assert all(house.responded for house in delivered.units[0].households)
    assert delivered.units[0].reminder_letter_history["responses"] == 4


def test_field_visit_and_reminder_delivery_can_happen_on_same_day():
    params = reminder_scenario(
        field_first_day=5, field_last_day=5,
        field_officer_working_hours_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 4.0),
        field_officer_visits_per_hour=1.0,
        field_answer_door_probability_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 0.0),
        field_vacancy_probability_if_no_answer=0.0,
        field_visit_response_probability_if_no_answer=0.0,
    )
    run = run_simulation(params, run_until=5.9, generate_plot=False)
    unit = run.units[0]
    assert len(unit.field_visit_history) == 4
    assert {visit["time"] for visit in unit.field_visit_history} == {5}
    assert unit.reminder_letter_history["responses"] == 4
    assert all(house.responded for house in unit.households)


def test_monte_carlo_reports_overall_and_regional_letter_totals_reproducibly():
    params = reminder_scenario(regions={"One": RegionParameters(4, 0), "Two": RegionParameters(2, 0)})
    result = run_monte_carlo(params, run_until=6, generate_plot=False)
    repeated = run_monte_carlo(params, run_until=6, generate_plot=False)
    for key in ("total_letters_sent", "letters_delivered", "reminder_letter_responses"):
        assert result.overall_summary[key] == {"mean": 6, "lower_95": 6, "upper_95": 6}
        assert result.region_summaries["One"][key]["mean"] == 4
        assert result.region_summaries["Two"][key]["mean"] == 2
    assert result.overall_summary == repeated.overall_summary
    disabled = run_simulation(dc.replace(params, reminder_letter_days=[]), run_until=6, generate_plot=False)
    assert all(not house.responded for unit in disabled.units for house in unit.households)


def test_sms_and_reminder_delivery_can_share_a_timestamp_without_double_response():
    params = reminder_scenario(sms_timing=5, sms_response_probability=0.0)
    run = run_simulation(params, run_until=5.9, generate_plot=False)

    assert run.units[0].reminder_letter_history["responses"] == 4
    assert all(house.responded for house in run.units[0].households)
    assert run.units[0].open_households == []


def test_zero_probability_delivers_letters_without_returning_households():
    houses = [household(0)]
    env, _, _, history = start_letters(houses, [0], delay=0, probability=0.0, draws=[0.0])
    env.run()
    assert history["letters_delivered"] == 1
    assert history["responses"] == 0
    assert not houses[0].responded
