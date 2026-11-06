def sms_day_n_responses(env, sms_list, n, sms_response_probability, rng, open_households=None):
    """Apply the SMS intervention to households on the configured day.

    Args:
        env: SimPy environment.
        sms_list: Mutable SMS contact list; successful respondents are removed immediately.
        n: Simulation day on which SMS messages are sent.
        sms_response_probability: One-off probability of responding to SMS.
        rng: Random number generator used for SMS response draws.
        open_households: Optional outstanding list or list of per-unit outstanding
            lists from which successful responses are removed.

    Yields:
        SimPy timeout event for the one-off SMS intervention.
    """

    yield env.timeout(n + 0.85)
    outstanding_lists = (
        open_households
        if open_households and isinstance(open_households[0], list)
        else [open_households] if open_households is not None else []
    )
    for household in list(sms_list):
        if (
            household.is_active
            and not household.responded
            and not household.refusal
            and not household.paper_first
        ):
            if rng.random() < sms_response_probability:
                household.responded = True
                for outstanding in outstanding_lists:
                    if household in outstanding:
                        outstanding.remove(household)
                sms_list.remove(household)
    print(f" Day {env.now}, SMS sent to houses on sms_list. Response attempts completed")

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