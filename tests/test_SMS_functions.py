from types import SimpleNamespace

import pytest
import simpy

from functions.functions_sms import sms_day_n_increase_baseline
from functions.functions_sms import populate_sms_list


def test_sms_day_n_increase_baseline_increases_each_household_probability_after_the_delay():
	# This test checks that SMS uplift is applied only after the configured delay and increases each listed household probability.
	env = simpy.Environment()
	households = [
		SimpleNamespace(response_probability=0.05, responded=False),
		SimpleNamespace(response_probability=0.2, responded=False),
	]

	env.process(sms_day_n_increase_baseline(env, households, 3, 0.07))

	env.run(until=2)

	assert [household.response_probability for household in households] == [0.05, 0.2]

	env.run(until=4)

	assert households[0].response_probability == pytest.approx(0.12)
	assert households[1].response_probability == pytest.approx(0.27)


def test_populate_sms_list_only_adds_households_with_sms_available_true():
	# This test checks that only non-responded households with SMS availability are added to the SMS list.
	env = simpy.Environment()
	sms_list = []
	households = [
		SimpleNamespace(sms_available=True, responded=False),
		SimpleNamespace(sms_available=False, responded=False),
		SimpleNamespace(sms_available=True, responded=True),
	]

	env.process(populate_sms_list(env, households, sms_list))
	env.run(until=0.2)

	assert len(sms_list) == 1
	assert sms_list[0] is households[0]


def test_populate_sms_list_only_adds_sms_available_households():
	# This test checks that households without SMS availability are excluded from the populated list.
	env = simpy.Environment()
	sms_list = []
	households = [
		SimpleNamespace(sms_available=False, responded=False),
		SimpleNamespace(sms_available=True, responded=False),
	]

	env.process(populate_sms_list(env, households, sms_list))
	env.run(until=0.2)

	assert len(sms_list) == 1
	assert sms_list[0] is households[1]

