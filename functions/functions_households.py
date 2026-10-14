#define a household class. Many of the attributes are currently random but to be set by ML/MI
class Household:
    def __init__(self, id, rng, baseline_response_probability, first_day_probability):
        self.id = id
        #is the household sent paper in the first wave. 
        self.paper_first = rng.choice([True, False])
        #has the household refused to take part
        self.refusal = False
        #is the household high on the 'hard to count' scale and therefore eligible for field officer visits
        self.hard_to_count = rng.choice([True, False])
        #is there a valid phone number for SMS messages linked to the household
        self.sms_available = rng.choice([True, False])
        #baseline probability of responding on a given day
        self.response_probability = baseline_response_probability
        #probability of responding on the first day without any specific intervention
        self.first_day_probability = first_day_probability
        # Add more attributes as needed

        #has the household been marked as responded to the census. 
        self.responded = False

    #change how the household is represented when printed
    def __repr__(self):
        return (
            f"Household(id={self.id}, paper_first={self.paper_first}, refusal={self.refusal}, "
            f" hard_to_count={self.hard_to_count}, responded={self.responded})"
        )
    
#first day responses. A one off event that captures those households that respond on the first day of the census.
def first_day_responses(env, households, rng):
    yield env.timeout(0)
    for household in households:
        if rng.random()<household.first_day_probability:
            household.responded = True
            print(f"Household {household.id} responded on the first day")


    
#event to update houses daily with their latest probability of responding from end of day one onwards
def daily_response_updates(env, households, rng):
    yield env.timeout(1.5)
    while True:
        for household in households:
            if household.responded is False:
                if rng.random() < household.response_probability:
                    household.responded = True
        yield env.timeout(1)