def deliver_paper_questionnaire(env, household, total_delay):
    """Deliver one posted paper questionnaire after a delay."""

    yield env.timeout(total_delay)
    if not household.is_active:
        household.waiting_for_pq = False
        return
    household.paper_first = False
    household.waiting_for_pq = False


class PaperQuestionnaireService:
    """Manage central paper questionnaire stock and dispatch timing."""

    def __init__(self, initial_paper_batch, postal_delay, printing_delay):
        self.paper_stock_remaining = initial_paper_batch
        self.postal_delay = postal_delay
        self.printing_delay = printing_delay

    def order_paper_questionnaire(self, env, household):
        """Order and dispatch a paper questionnaire for a household."""

        household.waiting_for_pq = True
        if self.paper_stock_remaining > 0:
            self.paper_stock_remaining -= 1
            total_delivery_delay = self.postal_delay
        else:
            total_delivery_delay = self.printing_delay + self.postal_delay

        env.process(deliver_paper_questionnaire(env, household, total_delivery_delay))


def process_call_centre_calls(
    env,
    households,
    call_probability,
    rng,
    call_centre_history,
    paper_questionnaire_service,
):
    """Run daily call-centre demand with one global call flow.

    Args:
        env: SimPy environment.
        households: Either a flat iterable of household objects or an
            iterable of per-unit open-household lists.
        call_probability: Daily probability that a paper-first household calls.
        rng: Random number generator used for call draws.
        call_centre_history: Mutable dictionary storing daily call totals.
        paper_questionnaire_service: Shared paper questionnaire service used
            for ordering and dispatch delays.

    Yields:
        SimPy timeout events that process calls once per simulated day.
    """

    def iter_households(household_collection):
        """Yield households from a flat list or list-of-lists input."""

        for entry in household_collection:
            if isinstance(entry, list):
                for household in entry:
                    yield household
            else:
                yield entry

    yield env.timeout(1.85)
    while True:
        daily_calls = 0
        for household in iter_households(households):
            if (
                household.is_active
                and household.paper_first
                and not household.responded
                and not household.waiting_for_pq
            ):
                if rng.random() < call_probability:
                    daily_calls += 1
                    paper_questionnaire_service.order_paper_questionnaire(env, household)

        call_centre_history["time"].append(env.now)
        call_centre_history["daily_calls"].append(daily_calls)
        yield env.timeout(1)
