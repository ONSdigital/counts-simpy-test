import simpy

#create the field officer/s that will service this household list
def create_field_officer(env: simpy.Environment):
    return simpy.Resource(env, capacity=1)

#from the household list, populate those that are in need of a visit. This is done once, immediately after the first day response. 
def populate_field_officer_list(env: simpy.Environment, households, field_officer_list):
    yield env.timeout(0.1)
    for household in households:
        if household.hard_to_count and not household.responded:
            field_officer_list.append(household)

#set up the queue of households to be visited the next day, and process the visits
def queue_field_officer_visits(
    env,
    field_officer,
    field_officer_list,
    start_day,
    visit_duration,
    response_probability_increase,
    queue_size,
    random_source,
):
    #wait for the day before start day, after the daily update
    yield env.timeout(max(start_day - 0.4, 0))

    #create the list of houses to be visited the next day. length is parameter, should only take
    #houses that have not been marked as responded, and are eligible for a visit (hard to count).
    while True:
        target_day = int(env.now + 0.4)
        daily_queue = [
            household
            for household in field_officer_list
            if not household.responded
            and getattr(household, "next_field_visit_day", 0) <= target_day
        ][:queue_size]

        #wait for actual day to start
        yield env.timeout(0.4)

        #for each household on the daily list, start a visit process
        for household in daily_queue:
            env.process(
                field_officer_visit(
                    env,
                    field_officer,
                    field_officer_list,
                    household,
                    visit_duration,
                    random_source,
                )
            )
            yield env.timeout(0)
        yield env.timeout(0.6)

#define the actual visit and the various outcomes
def field_officer_visit(
    env: simpy.Environment,
    field_officer: simpy.Resource,
    field_officer_list,
    household,
    visit_duration: float,
    random_source,
):

  
    with field_officer.request() as request:
        yield request

        print(f"Day {env.now}: field officer visiting household {household.id}")
        yield env.timeout(visit_duration)
        

        if random_source.random() < 0.5:
            if household in field_officer_list:
                field_officer_list.remove(household)
                household.responded = True
            visit_outcome = "A"
        else:
            household.next_field_visit_day = int(env.now) + 4
            visit_outcome = "B"

#to remove households from field_officer_list that have responded, after the end of day update
#this occurs after daily update but before the next day queue is created
def end_of_day_remove_responded_houses(env, field_officer_list, start_date):
    yield env.timeout(start_date+0.55)
    while True:
        yield env.timeout(1)
        field_officer_list[:] = [household for household in field_officer_list if not household.responded]
    
    

