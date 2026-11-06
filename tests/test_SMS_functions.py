from types import SimpleNamespace
import dataclasses as dc

import pytest
import simpy

from functions.functions_sms import sms_day_n_responses
from functions.functions_sms import populate_sms_list
from functions.functions_households import daily_response_updates
from functions.simulation_runner import run_simulation, run_monte_carlo
import functions.functions_sms as sms
from parameters import RegionParameters, baseline_parameters


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
	assert sms_list == [households[1]]
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


def test_daily_response_on_day_nine_removes_household_before_day_ten_sms():
	env = simpy.Environment()
	household = SimpleNamespace(
		demographic_group="A", responded=False, is_active=True,
		refusal=False, paper_first=False, sms_available=True,
	)
	open_households = [household]
	sms_list = []
	env.process(populate_sms_list(env, open_households, sms_list))
	env.process(daily_response_updates(
		env, [household], SequenceRandom([0.5] * 9),
		{"A": [0.0] * 8 + [1.0] + [0.0] * 41},
		open_households, sms_list=sms_list,
	))
	env.process(sms_day_n_responses(env, sms_list, 10, 1.0, SequenceRandom([])))

	env.run(until=9.7)
	assert sms_list == [household]
	assert not household.responded
	env.run(until=9.9)
	assert household.responded
	assert sms_list == []
	assert open_households == []
	env.run(until=11)


def test_simulation_wires_immediate_sms_removal_for_daily_responses():
	params = dc.replace(
		baseline_parameters,
		regions={"First": RegionParameters(20, 2), "Second": RegionParameters(20, 0)},
		field_first_day=20, field_last_day=20,
		daily_response_probabilities_by_group={
			group: [0.0] * 8 + [1.0] + [0.0] * 41 for group in ("A", "B", "C")
		},
		paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
		sms_timing=10, reminder_letter_days=[],
	)
	run = run_simulation(params, run_until=9.9, generate_plot=False)
	assert any(household.sms_available for household in run.units[0].households)
	assert all(household.responded for unit in run.units for household in unit.households)
	assert run.sms_list == []
	assert all(unit.intervention_lists.sms_list is run.sms_list for unit in run.units)


def test_sms_immediate_removal_does_not_skip_the_next_household():
	env = simpy.Environment()
	households = [
		SimpleNamespace(responded=False, is_active=True, refusal=False, paper_first=False)
		for _ in range(3)
	]
	sms_list = list(households)
	env.process(sms_day_n_responses(
		env, sms_list, 0, 1.0, SequenceRandom([0.0] * 3),
	))
	env.run(until=0.9)
	assert all(household.responded for household in households)
	assert sms_list == []


def test_sms_process_finishes_at_send_time_without_delayed_cleanup():
	env = simpy.Environment()
	household = SimpleNamespace(
		responded=False, is_active=True, refusal=False, paper_first=False,
	)
	sms_list = [household]
	process = env.process(sms_day_n_responses(
		env, sms_list, 0, 0.0, SequenceRandom([0.5]),
	))

	env.run(until=0.9)

	assert not process.is_alive
	assert env.peek() == float("inf")
	assert sms_list == [household]
	assert not household.responded


def test_national_sms_selection_and_sending_cover_all_regions_once(capsys):
	params = dc.replace(
		baseline_parameters,
		regions={"First": RegionParameters(20, 2), "Second": RegionParameters(20, 0)},
		daily_response_probabilities_by_group=dict.fromkeys(("A", "B", "C"), [0.0] * 50),
		paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
		field_first_day=20, field_last_day=20,
		sms_timing=1, sms_response_probability=1.0, reminder_letter_days=[],
	)
	before = run_simulation(params, run_until=0.2, generate_plot=False)
	expected = [house for unit in before.units for house in unit.households if house.sms_available]
	assert before.sms_list == expected
	assert all(unit.intervention_lists.sms_list is before.sms_list for unit in before.units)
	assert all(any(house.sms_available for house in region.households) for region in before.regions)

	after = run_simulation(params, run_until=1.95, generate_plot=False)
	assert after.sms_list is not before.sms_list
	assert after.sms_list == []
	for unit in after.units:
		assert all(house.responded == house.sms_available for house in unit.households)
		assert all(not house.responded for house in unit.open_households)
	for region in after.regions:
		assert region.return_history["responded_count"][-1] == sum(
			house.sms_available for house in region.households
		)
	assert capsys.readouterr().out.count("SMS sent to houses on sms_list") == 1


def test_monte_carlo_registers_one_fresh_national_sms_list_per_repeat(monkeypatch):
	lists = []
	populate = sms.populate_sms_list

	def capture_population(env, households, sms_list):
		lists.append(sms_list)
		return populate(env, households, sms_list)

	monkeypatch.setattr(sms, "populate_sms_list", capture_population)
	params = dc.replace(
		baseline_parameters,
		regions={"First": RegionParameters(10, 2), "Second": RegionParameters(10, 0)},
		monte_carlo_repeats=2, sms_timing=10, reminder_letter_days=[],
	)
	run_monte_carlo(params, run_until=1, generate_plot=False)
	assert len(lists) == 2
	assert lists[0] is not lists[1]
