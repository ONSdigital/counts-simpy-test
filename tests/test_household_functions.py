from types import SimpleNamespace

import pytest
import simpy

from functions.functions_households import Household
from functions.functions_households import first_day_responses
from functions.functions_households import daily_response_updates


class ConstantRandom:
    def random(self):
        return 1.0


class SequenceRandom:
    def __init__(self, draws):
        self._draws = list(draws)

    def random(self):
        return self._draws.pop(0)


class HouseholdInitRandom:
    def __init__(self):
        self._choice_values = [4, True, "A"]

    def choice(self, _options):
        return self._choice_values.pop(0)

    def random(self):
        return 0.2


def test_household_initialiser_sets_expected_state_fields():
    # This test checks that creating a household populates core default state and deterministic sampled attributes.
    household = Household(
        id=101,
        rng=HouseholdInitRandom(),
        baseline_response_probability=0.05,
        paper_first_probability_by_group={"A": 0.9, "B": 0.1, "C": 0.5},
    )

    assert household.id == 101
    assert household.hard_to_count == 4
    assert household.sms_available is True
    assert household.demographic_group == "A"
    assert household.paper_first is True
    assert household.responded is False
    assert household.waiting_for_pq is False
    assert household.is_active is True
    assert household.field_knocks == 0
    assert household.doorstep_completions == 0


def test_household_repr_contains_key_debug_fields():
    # This test checks that the household repr includes identifying and debugging attributes in plain text.
    household = Household(
        id=55,
        rng=HouseholdInitRandom(),
        baseline_response_probability=0.05,
        paper_first_probability_by_group={"A": 0.9, "B": 0.1, "C": 0.5},
    )

    text = repr(household)

    assert "Household(id=55" in text
    assert "paper_first=True" in text
    assert "hard_to_count=4" in text


def test_first_day_responses_marks_eligible_households_and_refreshes_open_list():
    # This test checks that first-day responses only affect eligible households and that open households are refreshed afterwards.
    env = simpy.Environment()
    households = [
        SimpleNamespace(
            id=1,
            responded=False,
            refusal=False,
            paper_first=False,
            response_probability=0.6,
            is_active=True,
        ),
        SimpleNamespace(
            id=2,
            responded=False,
            refusal=False,
            paper_first=True,
            response_probability=0.9,
            is_active=True,
        ),
        SimpleNamespace(
            id=3,
            responded=False,
            refusal=False,
            paper_first=False,
            response_probability=0.1,
            is_active=False,
        ),
    ]
    open_households = []

    env.process(first_day_responses(env, households, SequenceRandom([0.4, 0.9]), open_households))
    env.run(until=0.1)

    assert households[0].responded is True
    assert households[1].responded is False
    assert households[2].responded is False
    assert open_households == [households[1]]


def test_daily_response_probability_uses_group_table_without_intervention_carryover():
    env = simpy.Environment()
    households = [
        SimpleNamespace(
            responded=False,
            refusal=False,
            paper_first=False,
            is_active=True,
            demographic_group=group,
            baseline_response_probability=0.2,
            response_probability=0.2,
        )
        for group in ("A", "B", "C")
    ]
    probabilities = {
        "A": [0.2, 0.1] + [0.05] * 48,
        "B": [0.3, 0.4] + [0.1] * 48,
        "C": [0.4, 0.2] + [0.15] * 48,
    }

    env.process(
        daily_response_updates(
            env,
            households,
            ConstantRandom(),
            daily_response_probabilities_by_group=probabilities,
        )
    )

    env.run(until=1.7)
    assert [household.response_probability for household in households] == [0.2] * 3

    env.run(until=2.7)
    assert [household.response_probability for household in households] == pytest.approx([0.2, 0.3, 0.4])
    households[0].response_probability += 0.3

    env.run(until=3.7)
    assert [household.response_probability for household in households] == pytest.approx([0.1, 0.4, 0.2])
    assert probabilities["A"] == [0.2, 0.1] + [0.05] * 48


def test_first_daily_update_happens_on_day_one_using_group_probability():
    env = simpy.Environment()
    households = [
        SimpleNamespace(
            responded=False,
            refusal=False,
            paper_first=False,
            is_active=True,
            demographic_group="B",
            baseline_response_probability=0.05,
            response_probability=0.05,
        )
    ]

    env.process(
        daily_response_updates(
            env,
            households,
            SequenceRandom([0.15]),
            daily_response_probabilities_by_group={"B": [0.2] * 50},
        )
    )

    env.run(until=1.7)
    assert households[0].responded is False

    env.run(until=1.9)
    assert households[0].responded is True
    assert households[0].response_probability == pytest.approx(0.2)


def test_paper_first_household_tracks_table_and_uses_day_50_after_horizon():
    env = simpy.Environment()
    household = SimpleNamespace(
        responded=False,
        refusal=False,
        paper_first=True,
        is_active=True,
        demographic_group="A",
        baseline_response_probability=0.05,
        response_probability=0.35,
    )
    env.process(
        daily_response_updates(
            env,
            [household],
            SequenceRandom([0.3]),
            {"A": [0.1] * 49 + [0.4]},
        )
    )

    env.run(until=2)
    assert household.responded is False
    assert household.response_probability == pytest.approx(0.1)

    env.run(until=51)
    assert household.response_probability == pytest.approx(0.4)
    household.paper_first = False
    env.run(until=52)
    assert household.responded is True


@pytest.mark.parametrize(
    "table",
    [
        {"A": [0.05] * 50},
        {group: [0.05] * 49 for group in ("A", "B", "C")},
        {group: [1.1] * 50 for group in ("A", "B", "C")},
        {group: [float("nan")] * 50 for group in ("A", "B", "C")},
    ],
)
def test_parameters_reject_invalid_daily_probability_tables(table):
    from parameters import SimulationParameters

    with pytest.raises(ValueError):
        SimulationParameters(daily_response_probabilities_by_group=table)


@pytest.mark.parametrize("intervention", ["sms", "answered_visit", "unanswered_visit"])
def test_interventions_return_households_without_changing_baseline_tables(intervention):
    import copy
    import dataclasses as dc

    from functions.simulation_runner import run_simulation
    from parameters import baseline_parameters

    probabilities = {group: [0.0] * 50 for group in ("A", "B", "C")}
    original_probabilities = copy.deepcopy(probabilities)
    params = dc.replace(
        baseline_parameters,
        num_households=60,
        num_field_officers=1,
        daily_response_probabilities_by_group=probabilities,
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
        sms_timing=0 if intervention == "sms" else 100,
        sms_response_probability=1.0,
        field_first_day=100 if intervention == "sms" else 3,
        field_last_day=3,
        daily_field_visits=60,
        field_answer_door_probability=1.0 if intervention == "answered_visit" else 0.0,
        field_doorstep_completion_probability=0.0,
        field_vacancy_probability_if_no_answer=0.0,
        field_visit_response_probability_if_answer=1.0,
        field_visit_response_probability_if_no_answer=1.0,
    )
    result = run_simulation(params, run_until=5, generate_plot=False)
    households = result.units[0].households
    if intervention == "sms":
        households = [household for household in households if household.sms_available]

    assert households
    assert all(household.responded for household in households)
    assert all(household.response_probability == 0.0 for household in result.units[0].households)
    assert all(household.doorstep_completions == 0 for household in households)
    assert params.daily_response_probabilities_by_group == original_probabilities


def test_time_zero_responses_use_first_table_value_for_each_group():
    import dataclasses as dc

    from functions.simulation_runner import run_simulation
    from parameters import baseline_parameters

    first_probabilities = {"A": 1.0, "B": 0.0, "C": 1.0}
    params = dc.replace(
        baseline_parameters,
        num_households=100,
        num_field_officers=1,
        daily_response_probabilities_by_group={
            group: [probability] + [1 - probability] * 49
            for group, probability in first_probabilities.items()
        },
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
    )

    result = run_simulation(params, run_until=1, generate_plot=False)
    households = result.units[0].households

    assert {household.demographic_group for household in households} == {"A", "B", "C"}
    assert all(
        household.responded == bool(first_probabilities[household.demographic_group])
        for household in households
    )
    assert not hasattr(params, "first_day_probability")
