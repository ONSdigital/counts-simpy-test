import dataclasses as dc

#define a class that holds the parameters for the simulation
@dc.dataclass(frozen=True)
class SimulationParameters:
    scenario_name: str = "baseline"
    baseline_response_probability: float = 0.05
    daily_percentage_response_decrease: float = 0.1
    first_day_probability: float = 0.5
    paper_first_probability_by_group: dict[str, float] = dc.field(
        default_factory=lambda: {"A": 0.9, "B": 0.1, "C": 0.5}
    )
    num_households: int = 10000
    num_field_officers: int = 10
    sms_response_probability: float = 0.3
    seed: int = 1
    sms_timing: int = 20
    field_first_day: int = 7
    field_last_day: int = 30
    field_visit_duration: float = 0.01
    field_visit_response_boost_if_answer: float = 0.5
    field_visit_response_boost_if_no_answer: float = 0.2
    field_daily_queue_size: int = 30
    field_answer_door_probability: float = 0.3
    field_doorstep_completion_probability: float = 0.5
    field_vacancy_probability_if_no_answer: float = 0.05
    field_days_until_next_visit: int = 3
    call_centre_call_probability: float = 0.3
    initial_paper_batch: int = 500
    pQ_postal_delay: float = 3
    printing_delay: float = 2
    intervention_costs: dict[str, float] = dc.field(
        default_factory=lambda: {"sms": 0.05}
    )


# Name the baseline parameters used by default in simulation.py and app_streamlit.py
baseline_parameters = SimulationParameters()

# Example scenario variant. Kept as a usage example, not used as the default run baseline.
new_scenario_parameters = dc.replace(baseline_parameters, scenario_name = "new_scenario")

