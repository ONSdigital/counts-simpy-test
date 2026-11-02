from types import SimpleNamespace

import pytest
import simpy

from functions.functions_sms import sms_day_n_responses
from functions.functions_sms import populate_sms_list


class SequenceRandom:
	def __init__(self, draws):
		self.draws = iter(draws)

	def random(self):
		return next(self.draws)


def test_sms_makes_one_off_attempts_without_changing_baseline():
	env = simpy.Environment()
	households = [
		SimpleNamespace(id=1, response_probability=0.05, responded=False, is_active=True, refusal=False, paper_first=False),
		SimpleNamespace(id=2, response_probability=0.2, responded=False, is_active=True, refusal=False, paper_first=False),
	]
	sms_list = list(households)
	open_households = list(households)

	env.process(sms_day_n_responses(env, sms_list, 3, 0.3, SequenceRandom([0.1, 0.8]), open_households))

	env.run(until=2)

	assert [household.response_probability for household in households] == [0.05, 0.2]
	assert not any(household.responded for household in households)

	env.run(until=4)

	assert [household.responded for household in households] == [True, False]
	assert [household.response_probability for household in households] == [0.05, 0.2]
	assert open_households == [households[1]]
	env.run(until=10)
	assert sms_list == [households[1]]
	assert households[1].responded is False


@pytest.mark.parametrize("state", [{"paper_first": True}, {"refusal": True}, {"is_active": False}, {"responded": True}])
def test_sms_skips_households_ineligible_at_send_time(state):
	env = simpy.Environment()
	household = SimpleNamespace(response_probability=0.05, responded=False, is_active=True, refusal=False, paper_first=False)
	for name, value in state.items():
		setattr(household, name, value)
	env.process(sms_day_n_responses(env, [household], 0, 1.0, SequenceRandom([])))
	env.run(until=2)
	assert household.responded is state.get("responded", False)
	assert household.response_probability == 0.05


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

