import simpy


def create_field_officer(env: simpy.Environment):
    return simpy.Resource(env, capacity=1)


def populate_field_officer_list(env: simpy.Environment, households, field_officer_list):
    yield env.timeout(0.1)
    for household in households:
        if household.hard_to_count and not household.responded:
            field_officer_list.append(household)


def queue_field_officer_visits(
    env,
    field_officer,
    field_officer_list,
    start_day,
    visit_duration,
    response_probability_increase,
    queue_size,
    random_source,
    visit_log=None,
):
    yield env.timeout(max(start_day - 0.4, 0))

    while True:
        target_day = int(env.now + 0.4)
        daily_queue = [
            household
            for household in field_officer_list
            if not household.responded
            and getattr(household, "next_field_visit_day", 0) <= target_day
        ][:queue_size]

        yield env.timeout(0.4)

        for household in daily_queue:
            env.process(
                field_officer_visit(
                    env,
                    field_officer,
                    field_officer_list,
                    household,
                    visit_duration,
                    response_probability_increase,
                    random_source,
                    visit_log,
                )
            )
            yield env.timeout(0)

        yield env.timeout(0.6)


def field_officer_visit(
    env: simpy.Environment,
    field_officer: simpy.Resource,
    field_officer_list,
    household,
    visit_duration: float,
    random_source,
    visit_log=None,
):

    with field_officer.request() as request:
        yield request

        if visit_log is not None:
            visit_log.append(("start", household.id, env.now))

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

        if visit_log is not None:
            visit_log.append(("end", household.id, env.now, visit_outcome))

#to remove households that have responded at the end of each day. 
def end_of_day_remove_responded_houses(env, field_officer_list, field_visit_day):
    yield env.timeout(field_visit_day+0.55)
    while True:
        yield env.timeout(1)
        field_officer_list[:] = [household for household in field_officer_list if not household.responded]
    
    

