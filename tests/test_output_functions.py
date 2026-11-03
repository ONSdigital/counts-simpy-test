from types import SimpleNamespace
from pathlib import Path

import pytest
import simpy

from functions.functions_output import aggregate_unit_return_histories
from functions.functions_output import daily_response_totals
from functions.functions_output import initialise_call_centre_history
from functions.functions_output import initialise_household_return_history
from functions.functions_output import plot_household_return_proportions
from functions.functions_output import print_call_centre_daily_calls
from functions.functions_output import record_household_return_proportions


def test_initialise_call_centre_history_returns_empty_series():
    # This test checks that call-centre history storage starts with empty time and daily call lists.
    history = initialise_call_centre_history()

    assert history == {"time": [], "daily_calls": []}


def test_print_call_centre_daily_calls_prints_one_line_per_day(capsys):
    # This test checks that call-centre history printing produces a human-readable day-by-day summary.
    history = {"time": [1.85, 2.85], "daily_calls": [3, 1]}

    print_call_centre_daily_calls(history)

    output = capsys.readouterr().out
    assert "Call centre daily calls:" in output
    assert "Day 1: 3 calls" in output
    assert "Day 2: 1 calls" in output


def test_initialise_household_return_history_groups_households_by_demographic():
    # This test checks that household return history initialisation builds group sizes and empty proportion series.
    households = [
        SimpleNamespace(demographic_group="A"),
        SimpleNamespace(demographic_group="A"),
        SimpleNamespace(demographic_group="B"),
    ]

    history = initialise_household_return_history(households)

    assert history["total_households"] == 3
    assert history["group_sizes"] == {"A": 2, "B": 1}
    assert history["group_proportion_returned"] == {"A": [], "B": []}


def test_aggregate_unit_return_histories_combines_counts_and_weighted_group_proportions():
    # This test checks that aggregation sums counts and computes weighted group proportions across units.
    unit_one = {
        "time": [0.0, 1.0],
        "responded_count": [1, 2],
        "proportion_returned": [0.5, 1.0],
        "total_households": 2,
        "active_households": [2, 2],
        "group_sizes": {"A": 2},
        "group_proportion_returned": {"A": [0.5, 1.0]},
    }
    unit_two = {
        "time": [0.0, 1.0],
        "responded_count": [1, 1],
        "proportion_returned": [0.5, 0.5],
        "total_households": 2,
        "active_households": [2, 2],
        "group_sizes": {"A": 1, "B": 1},
        "group_proportion_returned": {"A": [1.0, 1.0], "B": [0.0, 0.0]},
    }

    aggregated = aggregate_unit_return_histories([unit_one, unit_two])

    assert aggregated["responded_count"] == [2, 3]
    assert aggregated["proportion_returned"] == pytest.approx([0.5, 0.75])
    assert aggregated["group_sizes"] == {"A": 3, "B": 1}
    assert aggregated["group_proportion_returned"]["A"] == pytest.approx([2 / 3, 1.0])
    assert aggregated["group_proportion_returned"]["B"] == [0.0, 0.0]


def test_daily_response_totals_prints_running_last_three_days(capsys):
    # This test checks that daily response total logging reports the rolling three-day summary once per day.
    env = simpy.Environment()
    households = [
        SimpleNamespace(responded=True),
        SimpleNamespace(responded=False),
    ]

    env.process(daily_response_totals(env, households))
    env.run(until=3.1)

    output = capsys.readouterr().out
    assert "on day 1" in output
    assert "on day 2" in output
    assert "on day 3" in output


def test_record_household_return_proportions_tracks_time_overall_and_group_values():
    # This test checks that return-proportion recording captures initial and daily samples for active households and each group.
    env = simpy.Environment()
    households = [
        SimpleNamespace(demographic_group="A", responded=True, is_active=True),
        SimpleNamespace(demographic_group="B", responded=False, is_active=True),
        SimpleNamespace(demographic_group="B", responded=False, is_active=False),
    ]
    history = initialise_household_return_history(households)

    env.process(record_household_return_proportions(env, households, history))
    env.run(until=2.95)

    assert history["time"] == pytest.approx([0.0, 1.0, 2.0])
    assert history["active_households"] == [2, 2, 2]
    assert history["responded_count"] == [1, 1, 1]
    assert history["proportion_returned"] == pytest.approx([0.5, 0.5, 0.5])
    assert history["group_proportion_returned"]["A"] == [1.0, 1.0, 1.0]
    assert history["group_proportion_returned"]["B"] == [0.0, 0.0, 0.0]


def test_plot_household_return_proportions_saves_png_file(tmp_path):
    # This test checks that plotting creates an image file when an output path is provided without showing an interactive window.
    output_file = tmp_path / "returns_plot.png"
    history = {
        "time": [0.0, 1.0, 2.0],
        "responded_count": [0, 1, 2],
        "proportion_returned": [0.0, 0.5, 1.0],
        "total_households": 2,
        "active_households": [2, 2, 2],
        "group_sizes": {"A": 1, "B": 1},
        "group_proportion_returned": {"A": [0.0, 1.0, 1.0], "B": [0.0, 0.0, 1.0]},
    }
    call_history = {"time": [1.0, 2.0], "daily_calls": [3, 1]}

    plot_household_return_proportions(
        history,
        sms_day=1,
        field_first_day=2,
        call_centre_history=call_history,
        show_plot=False,
        output_path=str(output_file),
    )

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_plot_household_return_proportions_saves_png_with_named_region_grid(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt

    figures = []
    original_close = plt.close

    def capture_figure(figure):
        figures.append(figure)
        original_close(figure)

    monkeypatch.setattr(plt, "close", capture_figure)
    output_file = tmp_path / "returns_with_regions.png"
    history = {
        "time": [0.0, 1.0, 2.0],
        "responded_count": [0, 1, 2],
        "proportion_returned": [0.0, 0.5, 1.0],
        "total_households": 2,
        "active_households": [2, 2, 2],
        "group_sizes": {"A": 1, "B": 1},
        "group_proportion_returned": {"A": [0.0, 1.0, 1.0], "B": [0.0, 0.0, 1.0]},
    }
    region_histories = {"North East": history, "Wales": history}

    plot_household_return_proportions(
        history,
        sms_day=1,
        field_first_day=2,
        show_plot=False,
        output_path=str(output_file),
        region_histories=region_histories,
    )

    assert output_file.exists()
    assert output_file.stat().st_size > 0
    assert [axis.get_title() for axis in figures[-1].axes] == [
        "Overall: England and Wales", "North East", "Wales",
    ]
    assert figures[-1].axes[0].lines[0].get_label() == "Overall"


def test_aggregation_weights_group_rates_by_active_households_after_vacancies():
    histories = [
        {
            "time": [0], "responded_count": [1], "proportion_returned": [1.0],
            "total_households": 2, "active_households": [1], "group_sizes": {"A": 2},
            "group_active_households": {"A": [1]}, "group_proportion_returned": {"A": [1.0]},
        },
        {
            "time": [0], "responded_count": [0], "proportion_returned": [0.0],
            "total_households": 2, "active_households": [2], "group_sizes": {"A": 2},
            "group_active_households": {"A": [2]}, "group_proportion_returned": {"A": [0.0]},
        },
    ]

    combined = aggregate_unit_return_histories(histories)

    assert combined["group_proportion_returned"]["A"] == pytest.approx([1 / 3])
    assert combined["group_active_households"] == {"A": [3]}
    assert combined["proportion_returned"] == pytest.approx([1 / 3])


def test_streamlit_region_edits_reach_simulation_and_named_reporting(monkeypatch):
    import dataclasses as dc
    from unittest.mock import Mock

    from streamlit.testing.v1 import AppTest
    from functions.simulation_runner import run_simulation
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={"North East": RegionParameters(12, 2), "Wales": RegionParameters(8, 1)},
    )
    runner = Mock(wraps=run_simulation)
    plot = Mock()
    monkeypatch.setattr("parameters.baseline_parameters", params)
    monkeypatch.setattr("functions.simulation_runner.run_simulation", runner)
    monkeypatch.setattr("functions.functions_output.plot_household_return_proportions", plot)
    monkeypatch.setattr("streamlit.image", Mock())
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app_streamlit.py")).run(timeout=30)
    assert not app.exception
    app.session_state["regional_parameters"] = {
        "edited_rows": {1: {"Households": 9, "Officers": 0, "A": 0.5, "B": 0.5, "C": 0.0}},
        "added_rows": [], "deleted_rows": [],
    }
    app.button[0].click()
    app.run(timeout=30)

    assert not app.exception
    wales = runner.call_args.kwargs["scenario_params"].regions["Wales"]
    assert wales.num_households == 9
    assert wales.num_field_officers == 0
    assert wales.household_type_proportions == {"A": 0.5, "B": 0.5, "C": 0.0}
    assert list(plot.call_args.kwargs["region_histories"]) == ["North East", "Wales"]
    headings = [heading.value for heading in app.subheader]
    assert headings.index("Overall: England and Wales") < headings.index("Regional results")
    result_tables = [table.value for table in app.dataframe if "Returned" in table.value.columns]
    assert len(result_tables) == 1
    assert list(result_tables[0]["Region"]) == ["North East", "Wales"]


def test_streamlit_invalid_region_shares_prevent_run_and_identify_region(monkeypatch):
    import dataclasses as dc
    from unittest.mock import Mock

    from streamlit.testing.v1 import AppTest
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(baseline_parameters, regions={"Wales": RegionParameters(8, 1)})
    runner = Mock()
    monkeypatch.setattr("parameters.baseline_parameters", params)
    monkeypatch.setattr("functions.simulation_runner.run_simulation", runner)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app_streamlit.py")).run(timeout=30)
    app.session_state["regional_parameters"] = {
        "edited_rows": {0: {"A": 0.5, "B": 0.5, "C": 0.5}},
        "added_rows": [], "deleted_rows": [],
    }
    app.button[0].click()
    app.run(timeout=30)

    assert not app.exception
    assert any("Wales" in error.value and "sum to 1" in error.value for error in app.error)
    runner.assert_not_called()


def test_script_displays_and_saves_regional_graph_and_reports_overall_first(monkeypatch, capsys, tmp_path):
    import dataclasses as dc
    from unittest.mock import Mock

    import matplotlib.pyplot as plt

    import simulation
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={"North East": RegionParameters(4, 1), "Wales": RegionParameters(6, 1)},
    )
    show = Mock()
    monkeypatch.setattr(simulation, "baseline_parameters", params)
    monkeypatch.setattr(plt, "show", show)
    monkeypatch.chdir(tmp_path)
    simulation.main()
    output = capsys.readouterr().out

    assert output.index("Overall: England and Wales") < output.index("\nNorth East:") < output.index("\nWales:")
    assert "Unit " not in output
    assert (tmp_path / "household_returns.png").stat().st_size > 0
    show.assert_called_once()
    figure = plt.gcf()
    assert [axis.get_title() for axis in figure.axes] == [
        "Overall: England and Wales", "North East", "Wales",
    ]
    plt.close(figure)
