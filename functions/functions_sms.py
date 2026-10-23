from functions import intervention_lists


def sms_day_n_increase_baseline(env, sms_list, n, sms_response_probability):
    """Apply the SMS intervention to households on the configured day.

    Args:
        env: SimPy environment.
        sms_list: Mutable list of households eligible for SMS.
        n: Simulation day on which SMS messages are sent.
        sms_response_probability: Probability uplift applied by SMS.

    Yields:
        SimPy timeout events for SMS timing and post-send cleanup.
    """

    yield env.timeout(n + 0.85)
    for household in sms_list:
        household.response_probability += sms_response_probability
    print(f" Day {env.now}, SMS sent to houses on sms_list. Probabilities updated")
    yield env.timeout(0.6)
    sms_list[:] = [household for household in sms_list if household.responded is False]

def populate_sms_list(env, households, sms_list):
    """Populate the SMS list with households eligible for messaging.

    Args:
        env: SimPy environment.
        households: Iterable of household objects in the simulation.
        sms_list: Mutable list that receives SMS-eligible households.

    Yields:
        SimPy timeout event scheduled shortly after first-day responses.
    """

    yield env.timeout(0.1)
    for household in households:
        if household.sms_available and not household.responded:
            sms_list.append(household)