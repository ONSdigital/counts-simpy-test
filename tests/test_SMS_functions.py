from types import SimpleNamespace

import pytest
import simpy

from functions.functions_sms import sms_day_n_increase_baseline


def test_sms_day_n_increase_baseline_increases_each_household_probability_after_the_delay():
	env = simpy.Environment()
	households = [
		SimpleNamespace(response_probability=0.05),
		SimpleNamespace(response_probability=0.2),
	]

	env.process(sms_day_n_increase_baseline(env, households, 3))

	env.run(until=2)

	assert [household.response_probability for household in households] == [0.05, 0.2]

	env.run(until=4)

	assert households[0].response_probability == pytest.approx(0.15)
	assert households[1].response_probability == pytest.approx(0.3)

