from parameters import baseline_parameters, SimulationParameters


def test_default_parameters_capture_the_current_baseline_scenario():
    assert baseline_parameters == SimulationParameters()
    assert baseline_parameters.scenario_name == "baseline"
    assert baseline_parameters.num_households == 10
    assert baseline_parameters.sms_response_probability == 0.3
    assert baseline_parameters.seed == 1
    assert baseline_parameters.sms_timing == 10
    assert baseline_parameters.intervention_costs == {"sms": 0.05}


    assert baseline_parameters.scenario_name == "baseline"
    assert baseline_parameters.sms_response_probability == 0.3
    assert baseline_parameters.intervention_costs == {"sms": 0.05}
