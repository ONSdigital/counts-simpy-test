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
        first_day_probability=0.3,
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
        first_day_probability=0.3,
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
            first_day_probability=0.6,
            is_active=True,
        ),
        SimpleNamespace(
            id=2,
            responded=False,
            refusal=False,
            paper_first=True,
            first_day_probability=0.9,
            is_active=True,
        ),
        SimpleNamespace(
            id=3,
            responded=False,
            refusal=False,
            paper_first=False,
            first_day_probability=0.1,
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


def test_daily_response_probability_wanes_by_percentage_each_day():
    # This test checks that daily response probability is multiplied by the configured waning factor once per day.
    env = simpy.Environment()
    households = [
        SimpleNamespace(
            responded=False,
            refusal=False,
            paper_first=False,
            is_active=True,
            response_probability=0.2,
        )
    ]

    env.process(
        daily_response_updates(
            env,
            households,
            ConstantRandom(),
            daily_percentage_response_decrease=0.15,
        )
    )

    env.run(until=1.7)
    assert households[0].response_probability == pytest.approx(0.2)

    env.run(until=2.7)
    assert households[0].response_probability == pytest.approx(0.17)

    env.run(until=3.7)
    assert households[0].response_probability == pytest.approx(0.1445)


def test_first_daily_update_happens_on_day_one_using_pre_wane_probability():
    # This test checks that the first daily response draw happens before any waning is applied for that day.
    env = simpy.Environment()
    households = [
        SimpleNamespace(
            responded=False,
            refusal=False,
            paper_first=False,
            is_active=True,
            response_probability=0.2,
        )
    ]

    env.process(
        daily_response_updates(
            env,
            households,
            SequenceRandom([0.15]),
            daily_percentage_response_decrease=0.15,
        )
    )

    env.run(until=1.7)
    assert households[0].responded is False

    env.run(until=1.9)
    assert households[0].responded is True
    assert households[0].response_probability == pytest.approx(0.2)
