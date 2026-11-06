from functions.functions_field import remove_household_from_all_intervention_lists


def deliver_reminder_letter(
    env, household, postal_delay, response_probability, rng,
    open_households, intervention_lists, history,
):
    """Deliver a posted reminder and make one response attempt on arrival."""
    yield env.timeout(postal_delay)
    if not household.is_active:
        return
    history["letters_delivered"] += 1
    if household.responded or household.paper_first or household.refusal:
        return
    if rng.random() < response_probability:
        household.responded = True
        history["responses"] += 1
        if household in open_households:
            open_households.remove(household)
        remove_household_from_all_intervention_lists(household, intervention_lists)


def send_reminder_letters(
    env, households, sending_days, postal_delay, response_probability, rng,
    open_households, intervention_lists, history,
):
    """Post one letter to each active non-respondent on every configured day."""
    for day in sorted(sending_days):
        yield env.timeout(day + 0.85 - env.now)
        recipients = [
            household for household in households
            if household.is_active and not household.responded
        ]
        history["time"].append(env.now)
        history["letters_sent"].append(len(recipients))
        history["total_letters_sent"] += len(recipients)
        for household in recipients:
            env.process(
                deliver_reminder_letter(
                    env, household, postal_delay, response_probability, rng,
                    open_households, intervention_lists, history,
                )
            )
