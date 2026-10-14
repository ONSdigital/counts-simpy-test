import dataclasses as dc

#define a class that holds the parameters for the simulation
@dc.dataclass(frozen=True)
class SimulationParameters:
    scenario_name: str = "baseline"
    baseline_response_probability: float = 0.05
    first_day_probability: float = 0.5
    num_households: int = 10
    sms_response_probability: float = 0.3
    seed: int = 1
    sms_timing: int = 10
    field_visit_day: int = 7
    field_visit_duration: float = 0.1
    field_visit_response_boost: float = 0.2
    field_daily_queue_size: int = 3
    intervention_costs: dict[str, float] = dc.field(
        default_factory=lambda: {"sms": 0.05}
    )


#Name the baseline paramaters for the simulation
baseline_parameters = SimulationParameters()

#setup example new parameters. No need to make new from scratch, just replace the values you want to change
new_scenario_parameters = dc.replace(baseline_parameters, scenario_name = "new_scenario", num_households = 20)

