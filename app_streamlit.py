import dataclasses as dc
import math
from pathlib import Path

import streamlit as st

import functions.functions_output as out
from parameters import FIELD_VISIT_SLOTS, WEEKDAYS, RegionParameters, baseline_parameters
from functions.simulation_runner import run_monte_carlo


st.set_page_config(page_title="Counts SimPy Runner", layout="wide")
st.title("Counts SimPy Simulation")
st.caption("Lightweight UI for scenario tuning and output plotting")

base_params = baseline_parameters

with st.expander("Regional parameters", expanded=True):
    region_rows = st.data_editor(
        [
            {
                "Region": name,
                "Households": region.num_households,
                "Officers": region.num_field_officers,
                **region.household_type_proportions,
            }
            for name, region in base_params.regions.items()
        ],
        disabled=["Region"],
        hide_index=True,
        column_config={
            "Households": st.column_config.NumberColumn(min_value=0, step=1, required=True),
            "Officers": st.column_config.NumberColumn(min_value=0, step=1, required=True),
            **{
                group: st.column_config.NumberColumn(
                    f"{group} share", min_value=0.0, max_value=1.0, step=0.01,
                    format="%.4f", required=True,
                )
                for group in ("A", "B", "C")
            },
        },
        key="regional_parameters",
    )

with st.sidebar:
    st.header("Scenario Parameters")
    census_start_weekday = st.selectbox(
        "Census starting weekday (day 0)",
        WEEKDAYS,
        index=WEEKDAYS.index(base_params.census_start_weekday),
    )
    monte_carlo_repeats = st.number_input(
        "Monte Carlo repeats",
        min_value=1,
        value=base_params.monte_carlo_repeats,
        step=1,
    )
    st.subheader("Field visit slots")
    field_visit_mode = st.selectbox(
        "Field visit mode", ("simple", "detailed"),
        index=("simple", "detailed").index(base_params.field_visit_mode),
    )
    refusal_probability = st.slider(
        "Simple per-knock refusal probability", 0.0, 1.0,
        float(base_params.refusal_probability), step=0.01,
    )
    field_vacancy_probability = st.slider(
        "Simple per-knock vacancy probability", 0.0, 1.0,
        float(base_params.field_vacancy_probability), step=0.01,
    )
    st.caption(
        "Simple: one draw for doorstep/refusal/vacancy/success/no outcome. "
        "Detailed: original door-answer decision tree. Refusing households are not revisited."
    )
    field_officer_working_hours_by_slot = {}
    field_answer_door_probability_by_slot = {}
    field_visit_response_probability_if_answer_by_slot = {}
    field_success_probability_by_slot = {}
    for slot in FIELD_VISIT_SLOTS:
        field_officer_working_hours_by_slot[slot] = st.number_input(
            f"{slot.capitalize()} working hours per day",
            min_value=0.0,
            value=float(base_params.field_officer_working_hours_by_slot[slot]),
            step=0.5,
        )
        field_answer_door_probability_by_slot[slot] = st.slider(
            f"{slot.capitalize()} door-answer probability",
            min_value=0.0,
            max_value=1.0,
            value=float(base_params.field_answer_door_probability_by_slot[slot]),
            step=0.01,
            help="Detailed mode only.",
        )
        field_success_probability_by_slot[slot] = st.slider(
            f"{slot.capitalize()} simple success probability",
            min_value=0.0, max_value=1.0,
            value=float(base_params.field_success_probability_by_slot[slot]),
            step=0.01,
            help="Simple mode only; excludes the separate doorstep-completion outcome.",
        )
        field_visit_response_probability_if_answer_by_slot[slot] = st.slider(
            f"{slot.capitalize()} response probability after answering",
            min_value=0.0,
            max_value=1.0,
            value=float(base_params.field_visit_response_probability_if_answer_by_slot[slot]),
            step=0.01,
            help="Detailed mode only: response chance without doorstep completion or paper order.",
        )
    st.caption("Morning/afternoon/evening: Monday-Friday. Weekend: Saturday and Sunday only.")
    field_officer_visits_per_hour = st.number_input(
        "Field officer visits per hour",
        min_value=0.1,
        value=base_params.field_officer_visits_per_hour,
        step=0.25,
    )
    field_first_day = st.number_input(
        "Field operations first day",
        min_value=1,
        max_value=100,
        value=base_params.field_first_day,
        step=1,
    )
    field_last_day = st.number_input(
        "Field operations last day",
        min_value=1,
        max_value=100,
        value=base_params.field_last_day,
        step=1,
    )
    sms_timing = st.number_input(
        "SMS day",
        min_value=1,
        max_value=100,
        value=base_params.sms_timing,
        step=1,
    )
    st.subheader("Reminder letters")
    reminder_letter_days = st.multiselect(
        "Reminder letter sending days",
        options=sorted(set(range(121)) | set(base_params.reminder_letter_days)),
        default=base_params.reminder_letter_days,
        help="Post to all active non-respondents on each selected day. Empty disables reminders.",
    )
    reminder_letter_response_probability = st.slider(
        "Reminder letter response probability",
        min_value=0.0,
        max_value=1.0,
        value=float(base_params.reminder_letter_response_probability),
        step=0.01,
    )
    st.subheader("Daily baseline probabilities")
    daily_probability_table = st.data_editor(
        {
            "Day": list(range(1, 51)),
            **base_params.daily_response_probabilities_by_group,
        },
        disabled=["Day"],
        hide_index=True,
        column_config={
            group: st.column_config.NumberColumn(
                group,
                min_value=0.0,
                max_value=1.0,
                step=0.001,
                format="%.4f",
                required=True,
            )
            for group in ("A", "B", "C")
        },
        key="daily_probability_table",
    )
    sms_response_probability = st.slider(
        "SMS response probability",
        min_value=0.0,
        max_value=1.0,
        value=float(base_params.sms_response_probability),
        step=0.01,
    )
    field_doorstep_completion_probability = st.slider(
        "Proportion of doorstep completions",
        min_value=0.0,
        max_value=1.0,
        value=float(base_params.field_doorstep_completion_probability),
        step=0.01,
        help="Simple: per-knock automatic success, including while awaiting paper. "
             "Detailed: completion probability conditional on answering.",
    )
    run_until = st.number_input(
        "Run until day",
        min_value=10,
        max_value=120,
        value=50,
        step=1,
    )

    run_clicked = st.button("Run simulation", type="primary")

configured_regions = {}
for row in region_rows:
    try:
        configured_regions[row["Region"]] = RegionParameters(
            num_households=row["Households"],
            num_field_officers=row["Officers"],
            household_type_proportions={group: row[group] for group in ("A", "B", "C")},
        )
    except (TypeError, ValueError) as error:
        st.error(f"Invalid parameters for {row['Region']}: {error}")
        configured_regions = None
        break

invalid_simple_slots = [
    slot for slot, success in field_success_probability_by_slot.items()
    if math.fsum((
        field_doorstep_completion_probability, refusal_probability, field_vacancy_probability, success,
    )) > 1
] if field_visit_mode == "simple" else []

if invalid_simple_slots:
    st.error(
        "Simple doorstep, refusal, vacancy and success probabilities must sum to at most 1 "
        f"for each slot. Invalid slots: {', '.join(invalid_simple_slots)}."
    )
elif field_last_day < field_first_day:
    st.error("Field operations last day must be greater than or equal to first day.")
elif run_clicked and configured_regions is not None:
    scenario_params = dc.replace(
        base_params,
        regions=configured_regions,
        census_start_weekday=census_start_weekday,
        monte_carlo_repeats=monte_carlo_repeats,
        field_visit_mode=field_visit_mode,
        refusal_probability=refusal_probability,
        field_vacancy_probability=field_vacancy_probability,
        field_success_probability_by_slot=field_success_probability_by_slot,
        field_officer_working_hours_by_slot=field_officer_working_hours_by_slot,
        field_answer_door_probability_by_slot=field_answer_door_probability_by_slot,
        field_visit_response_probability_if_answer_by_slot=field_visit_response_probability_if_answer_by_slot,
        field_officer_visits_per_hour=field_officer_visits_per_hour,
        field_first_day=field_first_day,
        field_last_day=field_last_day,
        sms_timing=sms_timing,
        reminder_letter_days=reminder_letter_days,
        reminder_letter_response_probability=reminder_letter_response_probability,
        daily_response_probabilities_by_group={
            group: list(daily_probability_table[group])
            for group in ("A", "B", "C")
        },
        sms_response_probability=sms_response_probability,
        field_doorstep_completion_probability=field_doorstep_completion_probability,
    )

    output_path = Path("streamlit_household_returns.png")
    progress_placeholder = st.empty()
    progress_bar = st.progress(0)

    def on_progress(completed_days):
        total_days = int(run_until) * monte_carlo_repeats
        progress_fraction = min(completed_days / total_days, 1.0)
        progress_bar.progress(progress_fraction)
        repeat_number = min((int(completed_days) - 1) // int(run_until) + 1, monte_carlo_repeats)
        day_number = int(completed_days) - (repeat_number - 1) * int(run_until)
        weekday = scenario_params.weekday_at(day_number)
        progress_placeholder.text(
            f"Run {repeat_number}/{monte_carlo_repeats}: day {day_number} ({weekday})"
        )

    progress_placeholder.info("Starting simulation run...")

    with st.spinner("Running simulation..."):
        result = run_monte_carlo(
            scenario_params=scenario_params,
            run_until=run_until,
            progress_interval=None,
            progress_callback=on_progress,
            generate_plot=False,
            show_plot=False,
            output_path=str(output_path),
        )

    with st.spinner("Rendering plots..."):
        out.plot_household_return_proportions(
            result.aggregate_history,
            sms_day=scenario_params.sms_timing,
            field_first_day=scenario_params.field_first_day,
            call_centre_history=result.call_centre_history,
            show_plot=False,
            output_path=str(output_path),
            region_histories=result.region_histories,
            reminder_letter_days=scenario_params.reminder_letter_days,
        )

    st.success("Simulation completed")

    summary = result.overall_summary

    st.subheader("Overall: England and Wales")
    st.caption(
        f"Field mode: {result.params.field_visit_mode}; "
        f"{monte_carlo_repeats} runs; {result.aggregate_history['total_households']:,} "
        f"households across {len(result.region_histories)} regions"
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Mean returned (%)", f"{100 * summary['proportion_returned']['mean']:.1f}")
    c2.metric("Mean returned count", f"{summary['responded_count']['mean']:,.1f}")
    c3.metric("Mean active households", f"{summary['active_households']['mean']:,.1f}")
    c4.metric("Mean call-centre calls", f"{summary['total_calls']['mean']:,.1f}")
    c5.metric("Mean doorstep completions", f"{summary['doorstep_completions']['mean']:,.1f}")
    st.dataframe(
        out.monte_carlo_summary_rows(summary),
        hide_index=True,
        column_config={
            column: st.column_config.NumberColumn(format="%.2f")
            for column in ("Mean", "95% lower", "95% upper")
        },
    )
    st.caption("95% run intervals are the 2.5th and 97.5th percentiles across repeats.")
    if monte_carlo_repeats == 1:
        st.warning("One run cannot estimate variation; its interval limits equal its result.")

    st.subheader("Regional results")
    st.dataframe(
        [
            {
                "Region": name,
                "Households": values["total_households"]["mean"],
                "Officers": scenario_params.regions[name].num_field_officers,
                "Mean active households": values["active_households"]["mean"],
                "Returned": values["responded_count"]["mean"],
                "Mean returned (%)": 100 * values["proportion_returned"]["mean"],
                "95% lower (%)": 100 * values["proportion_returned"]["lower_95"],
                "95% upper (%)": 100 * values["proportion_returned"]["upper_95"],
                "Mean field visits": values["field_visits"]["mean"],
                "Mean doorstep completions": values["doorstep_completions"]["mean"],
            }
            for name, values in result.region_summaries.items()
        ],
        hide_index=True,
        column_config={
            column: st.column_config.NumberColumn(format="%.2f")
            for column in ("Returned", "Mean returned (%)", "95% lower (%)", "95% upper (%)")
        },
    )

    if output_path.exists():
        st.image(str(output_path), caption="Overall and regional household returns", width="stretch")
    else:
        st.warning("Plot output file was not found.")
else:
    st.info("Set parameter inputs and click 'Run simulation'.")
