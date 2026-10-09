from parameters import DEFAULT_PARAMETERS, SimulationParameters


def test_default_parameters_capture_the_current_baseline_scenario():
    assert DEFAULT_PARAMETERS == SimulationParameters()
    assert DEFAULT_PARAMETERS.scenario_name == "baseline"
    assert DEFAULT_PARAMETERS.num_households == 10
    assert DEFAULT_PARAMETERS.sms_response_probability == 0.3
    assert DEFAULT_PARAMETERS.seed == 1
    assert DEFAULT_PARAMETERS.sms_timing == 10
    assert DEFAULT_PARAMETERS.intervention_costs == {"sms": 0.05}


    assert DEFAULT_PARAMETERS.scenario_name == "baseline"
    assert DEFAULT_PARAMETERS.sms_response_probability == 0.3
    assert DEFAULT_PARAMETERS.intervention_costs == {"sms": 0.05}
    