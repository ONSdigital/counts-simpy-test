import dataclasses as dc
from pathlib import Path

import streamlit as st

import functions.functions_output as out
from parameters import baseline_parameters
from functions.simulation_runner import run_simulation


st.set_page_config(page_title="Counts SimPy Runner", layout="wide")
st.title("Counts SimPy Simulation")
st.caption("Lightweight UI for scenario tuning and output plotting")

base_params = baseline_parameters

with st.sidebar:
    st.header("Scenario Parameters")
    num_households = st.number_input(
        "Number of households",
        min_value=100,
        max_value=30_000_000,
        value=base_params.num_households,
        step=100,
    )
    num_field_officers = st.number_input(
        "Number of field officers",
        min_value=1,
        max_value=500,
        value=base_params.num_field_officers,
        step=1,
    )
    daily_field_visits = st.number_input(
        "Daily field visits per officer",
        min_value=0,
        value=base_params.daily_field_visits,
        step=1,
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
    )
    run_until = st.number_input(
        "Run until day",
        min_value=10,
        max_value=120,
        value=50,
        step=1,
    )

    run_clicked = st.button("Run simulation", type="primary")

if field_last_day < field_first_day:
    st.error("Field operations last day must be greater than or equal to first day.")
elif run_clicked:
    scenario_params = dc.replace(
        base_params,
        num_households=num_households,
        num_field_officers=num_field_officers,
        daily_field_visits=daily_field_visits,
        field_first_day=field_first_day,
        field_last_day=field_last_day,
        sms_timing=sms_timing,
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
    progress_messages = []

    def on_progress(day):
        day_value = int(day)
        progress_fraction = min(day_value / int(run_until), 1.0)
        progress_bar.progress(progress_fraction)
        progress_messages.append(f"Simulation reached day {day_value}")
        progress_placeholder.text("\n".join(progress_messages[-20:]))

    progress_placeholder.info("Starting simulation run...")

    with st.spinner("Running simulation..."):
        result = run_simulation(
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
            unit_histories=[unit.return_history for unit in result.units],
        )

    st.success("Simulation completed")

    final_proportion = result.aggregate_history["proportion_returned"][-1]
    final_responded = result.aggregate_history["responded_count"][-1]
    final_active = result.aggregate_history["active_households"][-1]
    total_calls = sum(result.call_centre_history["daily_calls"])
    doorstep_completions = sum(
        household.doorstep_completions
        for unit in result.units
        for household in unit.households
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Final overall proportion", f"{final_proportion:.3f}")
    c2.metric("Final responded count", f"{final_responded}")
    c3.metric("Final active households", f"{final_active}")
    c4.metric("Total call-centre calls", f"{total_calls}")
    c5.metric("Doorstep completions", f"{doorstep_completions}")

    if output_path.exists():
        st.image(str(output_path), caption="Household returns over time", use_container_width=True)
    else:
        st.warning("Plot output file was not found.")
else:
    st.info("Set parameter inputs and click 'Run simulation'.")
