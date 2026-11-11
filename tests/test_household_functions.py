from types import SimpleNamespace

import pytest
import simpy

from parameters import FIELD_VISIT_SLOTS, RegionParameters
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
        regions={"Test region": RegionParameters(num_households=60, num_field_officers=1)},
        field_visit_mode="detailed",
        daily_response_probabilities_by_group=probabilities,
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
        sms_days=[0] if intervention == "sms" else [100],
        sms_response_probability=1.0,
        field_first_day=100 if intervention == "sms" else 3,
        field_last_day=3,
        field_officer_working_hours_by_slot={
            "morning": 8.0, "afternoon": 0.0, "evening": 0.0, "weekend": 8.0,
        },
        field_officer_visits_per_hour=7.5,
        field_answer_door_probability_by_slot=dict.fromkeys(
            FIELD_VISIT_SLOTS, 1.0 if intervention == "answered_visit" else 0.0
        ),
        field_doorstep_completion_probability=0.0,
        field_vacancy_probability_if_no_answer=0.0,
        field_visit_response_probability_if_answer_by_slot=dict.fromkeys(FIELD_VISIT_SLOTS, 1.0),
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
        regions={"Test region": RegionParameters(num_households=100, num_field_officers=1)},
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


def test_regions_share_clock_and_use_their_own_population_and_group_splits():
    import dataclasses as dc

    from functions.simulation_runner import run_simulation
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={
            "North East": RegionParameters(10, 2, {"A": 1.0, "B": 0.0, "C": 0.0}),
            "Wales": RegionParameters(6, 1, {"A": 0.0, "B": 1.0, "C": 0.0}),
        },
        daily_response_probabilities_by_group={"A": [1.0] * 50, "B": [0.0] * 50, "C": [0.0] * 50},
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
        field_first_day=100,
        sms_days=[100],
    )

    result = run_simulation(params, run_until=3, generate_plot=False)

    assert [region.name for region in result.regions] == ["North East", "Wales"]
    assert [len(region.households) for region in result.regions] == [10, 6]
    assert [len(region.units) for region in result.regions] == [2, 1]
    assert {household.demographic_group for household in result.regions[0].households} == {"A"}
    assert {household.demographic_group for household in result.regions[1].households} == {"B"}
    assert all(region.return_history["time"] == [0, 1, 2] for region in result.regions)
    assert result.aggregate_history["total_households"] == 16
    assert result.aggregate_history["responded_count"][-1] == 10
    assert result.aggregate_history["proportion_returned"][-1] == pytest.approx(10 / 16)
    assert len({household.id for region in result.regions for household in region.households}) == 16


def test_region_splits_round_to_population_and_zero_officers_disable_visits():
    import dataclasses as dc
    from collections import Counter

    from functions.simulation_runner import run_simulation
    from parameters import baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={"Wales": RegionParameters(5, 0, {"A": 0.5, "B": 0.3, "C": 0.2})},
        daily_response_probabilities_by_group={group: [0.0] * 50 for group in ("A", "B", "C")},
        field_first_day=3,
    )
    result = run_simulation(params, run_until=5, generate_plot=False)
    repeated = run_simulation(params, run_until=5, generate_plot=False)
    households = result.regions[0].households

    assert Counter(household.demographic_group for household in households) == {"A": 3, "B": 1, "C": 1}
    assert all(household.field_knocks == 0 for household in households)
    assert [vars(household) for household in households] == [
        vars(household) for household in repeated.regions[0].households
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"num_households": -1},
        {"num_field_officers": 1.5},
        {"household_type_proportions": {"A": 0.5, "B": 0.5}},
        {"household_type_proportions": {"A": 0.2, "B": 0.2, "C": 0.2}},
        {"household_type_proportions": {"A": -0.1, "B": 0.5, "C": 0.6}},
        {"household_type_proportions": {"A": float("nan"), "B": 0.5, "C": 0.5}},
    ],
)
def test_region_parameters_validate_counts_and_population_shares(kwargs):
    with pytest.raises(ValueError):
        RegionParameters(**kwargs)


def test_default_regions_include_nine_english_regions_and_wales():
    from parameters import baseline_parameters

    assert set(baseline_parameters.regions) == {
        "North East", "North West", "Yorkshire and the Humber", "East Midlands",
        "West Midlands", "East of England", "London", "South East", "South West", "Wales",
    }


def test_monte_carlo_repeats_use_distinct_reproducible_seeds_and_summarise_actual_runs():
    import dataclasses as dc
    import numpy as np

    from functions.simulation_runner import run_monte_carlo, run_simulation
    from parameters import baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={"North East": RegionParameters(12, 1), "Wales": RegionParameters(8, 1)},
        monte_carlo_repeats=4,
        seed=7,
        daily_response_probabilities_by_group={group: [0.2] * 50 for group in ("A", "B", "C")},
        paper_first_probability_by_group=dict.fromkeys(("A", "B", "C"), 0.0),
        field_first_day=100,
        sms_days=[100],
    )
    result = run_monte_carlo(params, run_until=3, generate_plot=False)
    repeated = run_monte_carlo(params, run_until=3, generate_plot=False)
    individual_runs = [
        run_simulation(dc.replace(params, seed=seed), run_until=3, generate_plot=False)
        for seed in result.run_seeds
    ]
    counts = [run.aggregate_history["responded_count"][-1] for run in individual_runs]

    assert len(result.run_seeds) == 4
    assert len(set(result.run_seeds)) == 4
    assert result.run_seeds[0] == params.seed
    assert result.overall_summary == repeated.overall_summary
    assert result.region_summaries == repeated.region_summaries
    assert result.overall_summary["responded_count"] == pytest.approx({
        "mean": np.mean(counts), "lower_95": np.quantile(counts, 0.025),
        "upper_95": np.quantile(counts, 0.975),
    })
    assert result.aggregate_history["proportion_returned"] == pytest.approx(
        np.mean([run.aggregate_history["proportion_returned"] for run in individual_runs], axis=0)
    )
    assert list(result.region_histories) == ["North East", "Wales"]
    assert result.overall_summary["total_households"]["mean"] == 20


@pytest.mark.parametrize("repeats", [0, -1, 1.5, True])
def test_monte_carlo_repeat_count_must_be_a_positive_integer(repeats):
    from parameters import SimulationParameters

    with pytest.raises(ValueError, match="monte_carlo_repeats"):
        SimulationParameters(monte_carlo_repeats=repeats)


def test_monte_carlo_progress_covers_all_repeats_and_only_plots_once(monkeypatch):
    import dataclasses as dc
    from unittest.mock import Mock

    from functions.simulation_runner import run_monte_carlo
    from parameters import baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={"Wales": RegionParameters(10, 1)},
        monte_carlo_repeats=3,
    )
    progress = []
    plot = Mock()
    monkeypatch.setattr("functions.functions_output.plot_household_return_proportions", plot)
    result = run_monte_carlo(params, run_until=2, progress_callback=progress.append)

    assert progress == [1, 2, 3, 4, 5, 6]
    plot.assert_called_once()
    assert plot.call_args.kwargs["region_histories"] == result.region_histories
    assert "proportion_returned_lower_95" in plot.call_args.args[0]


def test_one_monte_carlo_repeat_matches_single_run_and_has_zero_width_interval():
    import dataclasses as dc

    from functions.simulation_runner import run_monte_carlo, run_simulation
    from parameters import baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={"Wales": RegionParameters(10, 1)},
        monte_carlo_repeats=1,
    )
    result = run_monte_carlo(params, run_until=1, generate_plot=False)
    single = run_simulation(params, run_until=1, generate_plot=False)
    count = single.aggregate_history["responded_count"][-1]

    assert result.overall_summary["responded_count"] == {
        "mean": count, "lower_95": count, "upper_95": count,
    }
    assert result.aggregate_history["proportion_returned"] == single.aggregate_history["proportion_returned"]
    assert result.call_centre_history["daily_calls"] == []
