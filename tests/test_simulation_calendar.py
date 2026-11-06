import dataclasses as dc

import pytest
import simpy

from functions.simulation_runner import run_monte_carlo, run_simulation
from parameters import WEEKDAYS, RegionParameters, SimulationParameters


@pytest.mark.parametrize("start_weekday", WEEKDAYS)
def test_weekday_at_tracks_whole_days_and_wraps_each_week(start_weekday):
    params = SimulationParameters(census_start_weekday=start_weekday)
    start_index = WEEKDAYS.index(start_weekday)

    for day in range(22):
        expected = WEEKDAYS[(start_index + day) % 7]
        assert params.weekday_at(day) == expected
        assert params.weekday_at(day + 0.99) == expected


def test_weekday_at_defaults_to_monday_at_time_zero():
    params = SimulationParameters()

    assert params.weekday_at(0) == "Monday"
    assert params.weekday_at(6.99) == "Sunday"
    assert params.weekday_at(7) == "Monday"


@pytest.mark.parametrize("value", ["monday", "Funday", "", None, 0, True, []])
def test_parameters_reject_invalid_start_weekdays(value):
    with pytest.raises(ValueError, match="census_start_weekday"):
        SimulationParameters(census_start_weekday=value)


@pytest.mark.parametrize(
    "value", [-1, -0.1, float("nan"), float("inf"), float("-inf"), True, "1", None]
)
def test_weekday_at_rejects_invalid_simulation_times(value):
    with pytest.raises(ValueError, match="Simulation time"):
        SimulationParameters().weekday_at(value)


def test_weekday_is_available_to_processes_at_the_current_simulation_time():
    env = simpy.Environment()
    params = SimulationParameters(census_start_weekday="Sunday")
    observed = []

    def observe_weekdays():
        observed.append(params.weekday_at(env.now))
        yield env.timeout(0.9)
        observed.append(params.weekday_at(env.now))
        yield env.timeout(0.1)
        observed.append(params.weekday_at(env.now))

    env.process(observe_weekdays())
    env.run()

    assert observed == ["Sunday", "Sunday", "Monday"]


@pytest.mark.parametrize("runner", [run_simulation, run_monte_carlo])
def test_run_histories_include_weekdays_without_changing_model_outcomes(runner):
    params = SimulationParameters(
        regions={"Test": RegionParameters(num_households=6, num_field_officers=1)},
        monte_carlo_repeats=2,
        census_start_weekday="Sunday",
        field_first_day=100,
    )
    result = runner(params, run_until=9, generate_plot=False)
    shifted = runner(
        dc.replace(params, census_start_weekday="Wednesday"),
        run_until=9,
        generate_plot=False,
    )
    histories = [result.aggregate_history, result.call_centre_history]
    shifted_histories = [shifted.aggregate_history, shifted.call_centre_history]
    if runner is run_simulation:
        histories.extend(unit.return_history for unit in result.units)
        histories.extend(region.return_history for region in result.regions)
        shifted_histories.extend(unit.return_history for unit in shifted.units)
        shifted_histories.extend(region.return_history for region in shifted.regions)
    else:
        histories.extend(result.region_histories.values())
        shifted_histories.extend(shifted.region_histories.values())

    for history, shifted_history in zip(histories, shifted_histories):
        assert history["time"]
        assert history["weekday"] == [
            WEEKDAYS[(6 + int(time)) % 7] for time in history["time"]
        ]
        assert shifted_history["weekday"] == [
            WEEKDAYS[(2 + int(time)) % 7] for time in shifted_history["time"]
        ]
        assert {key: value for key, value in history.items() if key != "weekday"} == {
            key: value for key, value in shifted_history.items() if key != "weekday"
        }
