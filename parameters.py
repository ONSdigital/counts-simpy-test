import dataclasses as dc


@dc.dataclass(frozen=True)
class SimulationParameters:
    scenario_name: str = "baseline"
    num_households: int = 10
    sms_response_probability: float = 0.3
    seed: int = 1
    sms_timing: int = 10
    intervention_costs: dict[str, float] = dc.field(
        default_factory=lambda: {"sms": 0.05}
    )



DEFAULT_PARAMETERS = SimulationParameters()
new_parameters = dc.replace(DEFAULT_PARAMETERS, scenario_name = "new_scenario", num_households = 20)
