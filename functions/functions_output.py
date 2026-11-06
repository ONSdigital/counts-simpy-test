import math
import textwrap

import matplotlib.pyplot as plt
import numpy as np


def summarise_monte_carlo_values(values):
    """Return the mean and central 95% percentile interval across runs."""

    return {
        "mean": float(np.mean(values)),
        "lower_95": float(np.quantile(values, 0.025)),
        "upper_95": float(np.quantile(values, 0.975)),
    }


def summarise_monte_carlo_histories(histories):
    """Combine aligned run histories using means and pointwise run intervals."""

    first = histories[0]
    if any(history["time"] != first["time"] for history in histories):
        raise ValueError("Monte Carlo history timestamps must match")
    combined = {
        "time": list(first["time"]),
        "total_households": first["total_households"],
        "group_sizes": dict(first["group_sizes"]),
    }
    for key in ("responded_count", "active_households", "proportion_returned"):
        values = np.asarray([history[key] for history in histories], dtype=float)
        combined[key] = np.mean(values, axis=0).tolist()
        combined[f"{key}_lower_95"] = np.quantile(values, 0.025, axis=0).tolist()
        combined[f"{key}_upper_95"] = np.quantile(values, 0.975, axis=0).tolist()
    for key in ("group_active_households", "group_proportion_returned"):
        combined[key] = {}
        combined[f"{key}_lower_95"] = {}
        combined[f"{key}_upper_95"] = {}
        for group in first[key]:
            values = np.asarray([history[key][group] for history in histories], dtype=float)
            combined[key][group] = np.mean(values, axis=0).tolist()
            combined[f"{key}_lower_95"][group] = np.quantile(values, 0.025, axis=0).tolist()
            combined[f"{key}_upper_95"][group] = np.quantile(values, 0.975, axis=0).tolist()
    return combined


def monte_carlo_summary_rows(summary):
    """Prepare overall summary rows with return proportions expressed as percentages."""

    measures = (
        ("total_households", "Initial households", 1),
        ("responded_count", "Returned", 1),
        ("active_households", "Active households", 1),
        ("proportion_returned", "Returned (%)", 100),
        ("total_calls", "Call-centre calls", 1),
        ("total_letters_sent", "Reminder letters sent", 1),
        ("letters_delivered", "Reminder letters delivered", 1),
        ("reminder_letter_responses", "Reminder letter responses", 1),
        ("field_visits", "Field visits", 1),
        ("simple_field_successes", "Simple field successes", 1),
        ("field_visits_morning", "Morning visits", 1),
        ("field_visits_afternoon", "Afternoon visits", 1),
        ("field_visits_evening", "Evening visits", 1),
        ("field_visits_weekend", "Weekend visits", 1),
        ("doorstep_completions", "Doorstep completions", 1),
    )
    return [
        {
            "Measure": label,
            "Mean": scale * summary[key]["mean"],
            "95% lower": scale * summary[key]["lower_95"],
            "95% upper": scale * summary[key]["upper_95"],
        }
        for key, label, scale in measures
        if key in summary
    ]


def initialise_call_centre_history():
    """Create storage for daily call-centre demand outputs."""

    return {
        "time": [],
        "daily_calls": [],
    }


def print_call_centre_daily_calls(history):
    """Print the call-centre daily call totals.

    Args:
        history: Call-centre output dictionary with ``time`` and ``daily_calls``.
    """

    print("Call centre daily calls:")
    for day, daily_calls in zip(history["time"], history["daily_calls"]):
        print(f"Day {int(day)}: {daily_calls} calls")


def initialise_household_return_history(households):
    """Create the data structure used to store return-history series.

    Args:
        households: Iterable of household objects in the simulation.

    Returns:
        A dictionary containing overall and group-level output series.
    """

    grouped_households = {}
    for household in households:
        grouped_households.setdefault(household.demographic_group, []).append(household)

    group_sizes = {
        group: len(group_households)
        for group, group_households in grouped_households.items()
    }

    return {
        "time": [],
        "responded_count": [],
        "proportion_returned": [],
        "total_households": len(households),
        "active_households": [],
        "group_sizes": group_sizes,
        "group_active_households": {group: [] for group in grouped_households},
        "group_proportion_returned": {group: [] for group in grouped_households},
    }


def aggregate_unit_return_histories(unit_histories):
    """Aggregate multiple unit histories into one combined output series.

    Args:
        unit_histories: Iterable of unit history dictionaries created by
            ``initialise_household_return_history``.

    Returns:
        A history dictionary in the same shape as unit histories, containing
        summed counts and weighted proportions across all units.
    """

    if not unit_histories:
        return {
            "time": [],
            "responded_count": [],
            "proportion_returned": [],
            "total_households": 0,
            "active_households": [],
            "group_sizes": {},
            "group_active_households": {},
            "group_proportion_returned": {},
        }

    all_groups = sorted(
        {
            group
            for history in unit_histories
            for group in history.get("group_proportion_returned", {}).keys()
        }
    )
    aggregate_group_sizes = {
        group: sum(history.get("group_sizes", {}).get(group, 0) for history in unit_histories)
        for group in all_groups
    }

    aggregate_history = {
        "time": list(unit_histories[0]["time"]),
        "responded_count": [],
        "proportion_returned": [],
        "total_households": sum(history.get("total_households", 0) for history in unit_histories),
        "active_households": [],
        "group_sizes": aggregate_group_sizes,
        "group_active_households": {group: [] for group in all_groups},
        "group_proportion_returned": {group: [] for group in all_groups},
    }

    for index, _ in enumerate(aggregate_history["time"]):
        total_responded = sum(history["responded_count"][index] for history in unit_histories)
        aggregate_history["responded_count"].append(total_responded)

        total_active_households = sum(
            history.get("active_households", [history.get("total_households", 0)])[index]
            for history in unit_histories
        )
        aggregate_history["active_households"].append(total_active_households)

        if total_active_households:
            aggregate_history["proportion_returned"].append(
                total_responded / total_active_households
            )
        else:
            aggregate_history["proportion_returned"].append(0)

        for group in all_groups:
            group_total = 0
            weighted_group_responded = 0
            for history in unit_histories:
                active_counts = history.get("group_active_households", {}).get(group)
                group_size = (
                    active_counts[index] if active_counts is not None
                    else history.get("group_sizes", {}).get(group, 0)
                )
                group_total += group_size
                if group_size == 0:
                    continue
                group_proportion = history["group_proportion_returned"][group][index]
                weighted_group_responded += group_proportion * group_size

            aggregate_history["group_active_households"][group].append(group_total)
            aggregate_history["group_proportion_returned"][group].append(
                weighted_group_responded / group_total if group_total else 0
            )

    return aggregate_history


def daily_response_totals(env, households):
    """Print the most recent three daily response totals for debugging.

    Args:
        env: SimPy environment.
        households: Iterable of household objects in the simulation.

    Yields:
        SimPy timeout events that record totals once per day.
    """

    response_list = []
    while True:
        yield env.timeout(1)
        response_list.append(sum(h.responded for h in households))
        print(f"on day {env.now}, the last 3 days of response are {response_list[-3:]}")


def record_household_return_proportions(env, households, history):
    """Record overall and demographic-group return proportions over time.

    Args:
        env: SimPy environment.
        households: Iterable of household objects in the simulation.
        history: Mutable dictionary of output series created by
            ``initialise_household_return_history``.

    Yields:
        SimPy timeout events that record one sample per simulated day.
    """

    grouped_households = {}
    for household in households:
        grouped_households.setdefault(household.demographic_group, []).append(household)

    yield env.timeout(0.9)
    initial_active_households = [h for h in households if h.is_active]
    initial_returned_count = sum(h.responded for h in initial_active_households)
    initial_total_households = len(initial_active_households)
    history["time"].append(round(env.now - 0.9, 10))
    history["active_households"].append(initial_total_households)
    history["responded_count"].append(initial_returned_count)
    history["proportion_returned"].append(
        (initial_returned_count / initial_total_households) if initial_total_households else 0
    )
    for group in history["group_proportion_returned"]:
        group_households = [
            household
            for household in households
            if household.demographic_group == group and household.is_active
        ]
        history["group_active_households"][group].append(len(group_households))
        history["group_proportion_returned"][group].append(
            (sum(h.responded for h in group_households) / len(group_households))
            if group_households
            else 0
        )

    while True:
        yield env.timeout(1)
        active_households = [h for h in households if h.is_active]
        total_households = len(active_households)
        returned_count = sum(h.responded for h in active_households)
        history["time"].append(round(env.now - 0.9, 10))
        history["active_households"].append(total_households)
        history["responded_count"].append(returned_count)
        history["proportion_returned"].append(
            returned_count / total_households if total_households else 0
        )
        for group in history["group_proportion_returned"]:
            group_households = [
                household
                for household in households
                if household.demographic_group == group and household.is_active
            ]
            history["group_active_households"][group].append(len(group_households))
            history["group_proportion_returned"][group].append(
                (sum(h.responded for h in group_households) / len(group_households))
                if group_households
                else 0
            )


def plot_household_return_proportions(
    history,
    sms_day=None,
    field_first_day=None,
    call_centre_history=None,
    show_plot=False,
    output_path=None,
    region_histories=None,
    reminder_letter_days=None,
):
    """Plot the overall response curves above named regional panels.

    Args:
        history: Output-series dictionary created during the simulation run.
        sms_day: Optional simulation day on which SMS messages are sent.
        field_first_day: Optional first simulation day on which field visits begin.
        call_centre_history: Optional call-centre history dictionary containing
            daily call counts. Included for compatibility but not plotted.
        show_plot: Whether to display an interactive chart window.
        output_path: Optional image path to save the chart.
        region_histories: Optional mapping of region names to history dictionaries,
            shown in a grid below the overall chart.
        reminder_letter_days: Optional reminder sending days, not delivery days.
    """

    all_groups = set(history.get("group_proportion_returned", {}).keys())
    if region_histories:
        for region_history in region_histories.values():
            all_groups.update(region_history.get("group_proportion_returned", {}).keys())
    ordered_groups = sorted(all_groups)
    color_palette = plt.get_cmap("tab10")
    group_colors = {
        group: color_palette(index % 10)
        for index, group in enumerate(ordered_groups)
    }

    def draw_response_curves(axis, chart_history, include_labels):
        has_interval = "proportion_returned_lower_95" in chart_history
        if has_interval:
            axis.fill_between(
                chart_history["time"],
                chart_history["proportion_returned_lower_95"],
                chart_history["proportion_returned_upper_95"],
                color="black",
                alpha=0.12,
                label="95% run interval" if include_labels else None,
            )
        axis.plot(
            chart_history["time"],
            chart_history["proportion_returned"],
            linewidth=2.2,
            color="black",
            label=("Mean overall" if has_interval else "Overall") if include_labels else None,
        )
        for group in ordered_groups:
            proportions = chart_history.get("group_proportion_returned", {}).get(group)
            if proportions is None:
                continue
            axis.plot(
                chart_history["time"],
                proportions,
                linewidth=1.8,
                color=group_colors[group],
                label=f"Group {group}" if include_labels else None,
            )

        if sms_day is not None:
            axis.axvline(
                sms_day,
                color="tab:orange",
                linestyle=":",
                linewidth=1.6,
                label="SMS sent" if include_labels else None,
            )

        if field_first_day is not None:
            axis.axvline(
                field_first_day,
                color="tab:red",
                linestyle=":",
                linewidth=1.6,
                label="Field visits start" if include_labels else None,
            )

        if reminder_letter_days is not None:
            for index, day in enumerate(sorted(set(reminder_letter_days))):
                axis.axvline(
                    day,
                    color="tab:purple",
                    linestyle="--",
                    linewidth=1.6,
                    label="Reminder letters sent" if include_labels and index == 0 else None,
                )

        axis.set_ylim(0, 1)
        axis.grid(True, alpha=0.25)

    if not region_histories:
        fig, main_axis = plt.subplots(figsize=(8, 5))
        draw_response_curves(main_axis, history, include_labels=True)
        main_axis.set_title("Overall: England and Wales")
        main_axis.set_xlabel("Time")
        main_axis.set_ylabel("Proportion of households returned")
        handles, labels = main_axis.get_legend_handles_labels()
        if handles:
            fig.legend(handles, labels, loc="lower center", ncol=min(5, len(labels)))
        fig.tight_layout(rect=(0, 0.06, 1, 1))
    else:
        region_count = len(region_histories)
        num_columns = min(3, max(1, math.ceil(math.sqrt(region_count))))
        num_rows = math.ceil(region_count / num_columns)

        fig = plt.figure(figsize=(4 * num_columns, 3.6 + 2.1 * num_rows))
        grid = fig.add_gridspec(
            nrows=1 + num_rows,
            ncols=num_columns,
            height_ratios=[2.3] + [1.0] * num_rows,
        )

        main_axis = fig.add_subplot(grid[0, :])
        draw_response_curves(main_axis, history, include_labels=True)
        main_axis.set_title("Overall: England and Wales")
        main_axis.set_xlabel("Time")
        main_axis.set_ylabel("Proportion of households returned")

        for index, (region_name, region_history) in enumerate(region_histories.items()):
            row = 1 + (index // num_columns)
            column = index % num_columns
            region_axis = fig.add_subplot(grid[row, column])
            draw_response_curves(region_axis, region_history, include_labels=False)
            region_axis.set_title(textwrap.fill(region_name, width=24))
            region_axis.set_xlabel("")
            region_axis.set_ylabel("")

        total_slots = num_rows * num_columns
        for index in range(region_count, total_slots):
            row = 1 + (index // num_columns)
            column = index % num_columns
            empty_axis = fig.add_subplot(grid[row, column])
            empty_axis.axis("off")

        handles, labels = main_axis.get_legend_handles_labels()
        if handles:
            fig.legend(
                handles,
                labels,
                loc="lower center",
                ncol=min(6, len(labels)),
                frameon=False,
            )
        fig.tight_layout(rect=(0, 0.06, 1, 1))

    if output_path:
        fig.savefig(output_path, dpi=150)
    if show_plot:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    print(
        "functions_output.py is a helper module and does not run a simulation on its own. "
        "Run simulation.py from the project root to execute the model."
    )
