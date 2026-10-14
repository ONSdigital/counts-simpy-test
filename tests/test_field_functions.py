from types import SimpleNamespace

import pytest
import simpy

from functions.functions_field import create_field_officer, queue_field_officer_visits


class FixedRandom:
    def __init__(self, values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0)


def test_field_officer_visits_build_a_daily_queue_without_depopulating_the_master_list():
    env = simpy.Environment()
    field_officer = create_field_officer(env)
    households = [
        SimpleNamespace(id=1, responded=False, response_probability=0.05),
        SimpleNamespace(id=2, responded=False, response_probability=0.2),
        SimpleNamespace(id=3, responded=False, response_probability=0.3),
        SimpleNamespace(id=4, responded=False, response_probability=0.4),
    ]
    field_officer_list = households.copy()

    env.process(
        queue_field_officer_visits(
            env,
            field_officer,
            field_officer_list,
            start_day=3,
            visit_duration=0.15,
            response_probability_increase=0.1,
            queue_size=3,
            random_source=FixedRandom([0.8, 0.8, 0.8, 0.8]),
        )
    )

    env.run(until=4.5)

    assert households[0].response_probability == pytest.approx(0.05)
    assert households[1].response_probability == pytest.approx(0.2)
    assert households[2].response_probability == pytest.approx(0.3)
    assert households[3].response_probability == pytest.approx(0.4)
    assert field_officer_list == households
    assert households[0].next_field_visit_day == 7
    assert households[3].next_field_visit_day == 8


def test_field_officer_option_a_removes_household_from_master_list():
    env = simpy.Environment()
    field_officer = create_field_officer(env)
    households = [
        SimpleNamespace(id=1, responded=False, response_probability=0.05),
        SimpleNamespace(id=2, responded=False, response_probability=0.2),
    ]
    field_officer_list = households.copy()

    env.process(
        queue_field_officer_visits(
            env,
            field_officer,
            field_officer_list,
            start_day=3,
            visit_duration=0.2,
            response_probability_increase=0.1,
            queue_size=2,
            random_source=FixedRandom([0.2, 0.8]),
        )
    )

    env.run(until=4)

    assert households[0] not in field_officer_list
    assert households[1] in field_officer_list
    assert households[0].responded is True