class Household:
    """Represent a household and its response-related simulation state.

    Args:
        id: Unique household identifier.
        rng: Random number generator used to assign initial attributes.
        baseline_response_probability: Initial baseline probability of response,
            also used for the time-zero response draw.
    """

    def __init__(
        self,
        id,
        rng,
        baseline_response_probability,
        paper_first_probability_by_group,
    ):
        self.id = id
        #has the household refused to take part
        self.refusal = False
        #is the household high on the 'hard to count' scale and therefore eligible for field officer visits
        self.hard_to_count = rng.choice([1, 2, 3, 4, 5])
        #is there a valid phone number for SMS messages linked to the household
        self.sms_available = rng.choice([True, False])
        #baseline probability of responding on a given day
        self.baseline_response_probability = baseline_response_probability
        self.response_probability = baseline_response_probability
        #demographic groups
        self.demographic_group = rng.choice(["A", "B", "C"])
        #will the household only respond to paper questionnaire (or doorstep completion)
        paper_first_probability = paper_first_probability_by_group.get(
            self.demographic_group,
            0.5,
        )
        self.paper_first = rng.random() < paper_first_probability
        # Add more attributes as needed

        #has the household been marked as responded to the census. 
        self.responded = False
        #is the household waiting for a posted paper questionnaire delivery
        self.waiting_for_pq = False
        #is the household still active in the simulation population
        self.is_active = True
        #number of times a field officer has knocked at this household
        self.field_knocks = 0
        #number of successful doorstep completions at this household
        self.doorstep_completions = 0
        #day on which the household becomes eligible for another field visit
        self.next_field_visit_day = 0

    def __repr__(self):
        """Return a concise string representation for debugging."""

        return (
            f"Household(id={self.id}, paper_first={self.paper_first}, refusal={self.refusal}, "
            f" hard_to_count={self.hard_to_count}, responded={self.responded})"
        )
    
def first_day_responses(env, households, rng, open_households=None):
    """Apply time-zero responses using each household's initial group baseline.

    Args:
        env: SimPy environment.
        households: Iterable of household objects to update.
        rng: Random number generator used for response draws.

    Yields:
        SimPy timeout event scheduled at time zero.
    """

    yield env.timeout(0)
    for household in households:
        if household.responded is False and household.refusal is False and household.paper_first is False:
            if rng.random() < household.response_probability:
                household.responded = True
                # print(f"Household {household.id} responded on the first day")

    if open_households is not None:
        open_households[:] = [
            household
            for household in households
            if household.is_active and household.responded is False
        ]


    
def daily_response_updates(
    env,
    households,
    rng,
    daily_response_probabilities_by_group,
    open_households=None,
):
    """Update household response status once per simulated day.

    Args:
        env: SimPy environment.
        households: Iterable of household objects to update.
        rng: Random number generator used for daily response draws.
        daily_response_probabilities_by_group: Group-specific baseline values
            for days 1 to 50. Later days retain the final value. Interventions
            make separate response attempts without changing these values.

    Yields:
        SimPy timeout events that advance the process by one day at a time.
    """

    yield env.timeout(1.8)
    day_index = 0
    while True:
        households_to_process = open_households if open_households is not None else households
        for household in list(households_to_process):
            if not household.is_active or household.responded:
                continue
            probabilities = daily_response_probabilities_by_group[household.demographic_group]
            baseline_probability = probabilities[min(day_index, 49)]
            household.baseline_response_probability = baseline_probability
            household.response_probability = baseline_probability

            if household.responded is False and household.refusal is False and household.paper_first is False:
                if rng.random() < household.response_probability:
                    household.responded = True
                    if open_households is not None and household in open_households:
                        open_households.remove(household)

        day_index += 1
        yield env.timeout(1)