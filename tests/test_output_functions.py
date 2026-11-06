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
    from functions.simulation_runner import run_monte_carlo
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(
        baseline_parameters,
        regions={"North East": RegionParameters(12, 2), "Wales": RegionParameters(8, 1)},
    )
    runner = Mock(wraps=run_monte_carlo)
    plot = Mock()
    monkeypatch.setattr("parameters.baseline_parameters", params)
    monkeypatch.setattr("functions.simulation_runner.run_monte_carlo", runner)
    monkeypatch.setattr("functions.functions_output.plot_household_return_proportions", plot)
    monkeypatch.setattr("streamlit.image", Mock())
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app_streamlit.py")).run(timeout=30)
    assert not app.exception
    app.session_state["regional_parameters"] = {
        "edited_rows": {1: {"Households": 9, "Officers": 0, "A": 0.5, "B": 0.5, "C": 0.0}},
        "added_rows": [], "deleted_rows": [],
    }
    next(control for control in app.number_input if control.label == "Monte Carlo repeats").set_value(3)
    next(control for control in app.selectbox if control.label == "Field visit mode").set_value("detailed")
    next(control for control in app.multiselect if control.label == "Reminder letter sending days").set_value([2, 4])
    next(control for control in app.slider if control.label == "Reminder letter response probability").set_value(0.7)
    next(control for control in app.number_input if control.label == "Morning working hours per day").set_value(4.0)
    next(control for control in app.number_input if control.label == "Weekend working hours per day").set_value(0.0)
    next(control for control in app.slider if control.label == "Evening door-answer probability").set_value(0.8)
    next(
        control for control in app.slider
        if control.label == "Afternoon response probability after answering"
    ).set_value(0.6)
    app.button[0].click()
    app.run(timeout=30)

    assert not app.exception
    wales = runner.call_args.kwargs["scenario_params"].regions["Wales"]
    assert wales.num_households == 9
    assert wales.num_field_officers == 0
    assert wales.household_type_proportions == {"A": 0.5, "B": 0.5, "C": 0.0}
    assert runner.call_args.kwargs["scenario_params"].monte_carlo_repeats == 3
    configured = runner.call_args.kwargs["scenario_params"]
    assert configured.field_visit_mode == "detailed"
    assert configured.reminder_letter_days == [2, 4]
    assert configured.reminder_letter_response_probability == 0.7
    assert configured.field_officer_working_hours_by_slot == {
        "morning": 4.0, "afternoon": 3.0, "evening": 2.0, "weekend": 0.0,
    }
    assert configured.field_answer_door_probability_by_slot["evening"] == 0.8
    assert configured.field_visit_response_probability_if_answer_by_slot["afternoon"] == 0.6
    assert list(plot.call_args.kwargs["region_histories"]) == ["North East", "Wales"]
    assert plot.call_args.kwargs["reminder_letter_days"] == [2, 4]
    headings = [heading.value for heading in app.subheader]
    assert headings.index("Overall: England and Wales") < headings.index("Regional results")
    result_tables = [table.value for table in app.dataframe if "Returned" in table.value.columns]
    assert len(result_tables) == 1
    assert list(result_tables[0]["Region"]) == ["North East", "Wales"]
    overall_tables = [table.value for table in app.dataframe if "Measure" in table.value.columns]
    assert len(overall_tables) == 1
    assert list(overall_tables[0].columns) == ["Measure", "Mean", "95% lower", "95% upper"]
    assert "Call-centre calls" in list(overall_tables[0]["Measure"])
    assert "Weekend visits" in list(overall_tables[0]["Measure"])
    assert "Reminder letters sent" in list(overall_tables[0]["Measure"])
    assert "Simple field successes" in list(overall_tables[0]["Measure"])


def test_streamlit_simple_mode_probability_controls_and_invalid_totals(monkeypatch):
    import dataclasses as dc
    from unittest.mock import Mock
    from streamlit.testing.v1 import AppTest
    from functions.simulation_runner import run_monte_carlo
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(
        baseline_parameters, regions={"Test": RegionParameters(4, 1)},
    )
    runner = Mock(wraps=run_monte_carlo)
    monkeypatch.setattr("parameters.baseline_parameters", params)
    monkeypatch.setattr("functions.simulation_runner.run_monte_carlo", runner)
    monkeypatch.setattr("functions.functions_output.plot_household_return_proportions", Mock())
    monkeypatch.setattr("streamlit.image", Mock())
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app_streamlit.py")).run(timeout=30)
    assert not app.exception
    assert next(control for control in app.selectbox if control.label == "Field visit mode").value == "simple"
    success = next(control for control in app.slider if control.label == "Morning simple success probability")
    success.set_value(0.9)
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert any("must sum to at most 1" in error.value for error in app.error)
    runner.assert_not_called()
    next(control for control in app.slider if control.label == "Morning simple success probability").set_value(0.2)
    next(control for control in app.slider if control.label == "Simple per-knock refusal probability").set_value(0.02)
    next(control for control in app.slider if control.label == "Simple per-knock vacancy probability").set_value(0.03)
    app.button[0].click().run(timeout=30)
    assert not app.exception
    configured = runner.call_args.kwargs["scenario_params"]
    assert configured.field_visit_mode == "simple"
    assert configured.field_success_probability_by_slot["morning"] == 0.2
    assert configured.refusal_probability == 0.02
    assert configured.field_vacancy_probability == 0.03


def test_streamlit_invalid_region_shares_prevent_run_and_identify_region(monkeypatch):
    import dataclasses as dc
    from unittest.mock import Mock

    from streamlit.testing.v1 import AppTest
    from parameters import RegionParameters, baseline_parameters

    params = dc.replace(baseline_parameters, regions={"Wales": RegionParameters(8, 1)})
    runner = Mock()
    monkeypatch.setattr("parameters.baseline_parameters", params)
    monkeypatch.setattr("functions.simulation_runner.run_monte_carlo", runner)
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
        monte_carlo_repeats=2,
    )
    show = Mock()
    monkeypatch.setattr(simulation, "baseline_parameters", params)
    monkeypatch.setattr(plt, "show", show)
    monkeypatch.chdir(tmp_path)
    simulation.main()
    output = capsys.readouterr().out

    assert output.index("Overall: England and Wales") < output.index("\nNorth East:") < output.index("\nWales:")
    assert "Unit " not in output
    assert "95% lower" in output and "95% upper" in output
    assert "2 Monte Carlo runs" in output
    assert (tmp_path / "household_returns.png").stat().st_size > 0
    show.assert_called_once()
    figure = plt.gcf()
    assert [axis.get_title() for axis in figure.axes] == [
        "Overall: England and Wales", "North East", "Wales",
    ]
    assert figure.axes[0].lines[0].get_label() == "Mean overall"
    assert figure.axes[0].collections
    plt.close(figure)


@pytest.mark.parametrize(
    "values, expected",
    [
        ([0, 10, 20, 30], {"mean": 15.0, "lower_95": 0.75, "upper_95": 29.25}),
        ([12], {"mean": 12.0, "lower_95": 12.0, "upper_95": 12.0}),
    ],
)
def test_monte_carlo_summary_uses_mean_and_central_percentile_interval(values, expected):
    from functions.functions_output import summarise_monte_carlo_values

    assert summarise_monte_carlo_values(values) == pytest.approx(expected)


@pytest.mark.parametrize("sending_days", [None, [], [0, 1, 2], [2, 1, 1]])
@pytest.mark.parametrize("regional", [False, True])
def test_plot_marks_reminder_sending_days_on_every_panel(sending_days, regional, monkeypatch):
    import matplotlib.pyplot as plt
    from unittest.mock import Mock

    history = {
        "time": [0, 1, 2, 3],
        "proportion_returned": [0.0, 0.1, 0.2, 0.3],
        "group_proportion_returned": {},
    }
    monkeypatch.setattr(plt, "show", Mock())
    plot_household_return_proportions(
        history,
        sms_day=1,
        field_first_day=2,
        reminder_letter_days=sending_days,
        region_histories={"North East": history, "Wales": history} if regional else None,
        show_plot=True,
    )
    figure = plt.gcf()
    try:
        expected = sorted(set(sending_days or []))
        for axis in figure.axes:
            markers = [line for line in axis.lines if line.get_color() == "tab:purple"]
            assert [list(line.get_xdata()) for line in markers] == [[day, day] for day in expected]
            assert all(line.get_linestyle() == "--" for line in markers)
            assert any(line.get_color() == "tab:orange" for line in axis.lines)
            assert any(line.get_color() == "tab:red" for line in axis.lines)
        labels = [text.get_text() for legend in figure.legends for text in legend.get_texts()]
        assert labels.count("Reminder letters sent") == (1 if expected else 0)
    finally:
        plt.close(figure)


@pytest.mark.parametrize("repeated", [False, True])
def test_runners_pass_reminder_sending_days_to_plot(repeated, monkeypatch):
    from unittest.mock import Mock
    from functions.simulation_runner import run_monte_carlo, run_simulation
    from parameters import RegionParameters, SimulationParameters

    params = SimulationParameters(
        regions={"Test": RegionParameters(2, 0)},
        reminder_letter_days=[1, 3],
        pQ_postal_delay=5,
    )
    plot = Mock()
    monkeypatch.setattr("functions.functions_output.plot_household_return_proportions", plot)
    runner = run_monte_carlo if repeated else run_simulation
    runner(params, run_until=4)

    plot.assert_called_once()
    assert plot.call_args.kwargs["reminder_letter_days"] == [1, 3]
