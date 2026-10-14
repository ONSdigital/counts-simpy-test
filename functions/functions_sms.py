#sends sms at start of n, updates sms_list immediately after end of day update
from functions import intervention_lists

#increase the response probability + remove those households that have responded
def sms_day_n_increase_baseline(env, sms_list, n):
    yield env.timeout(n)
    for household in sms_list:
        household.response_probability += 0.1
    print(f" Day {env.now}, SMS sent to houses on sms_list. Probabilities updated")
    yield env.timeout(0.6)
    sms_list[:] = [household for household in sms_list if household.responded is False]

#populate the sms_list immediately after the first day responses. 
def populate_sms_list(env, households, sms_list):
    yield env.timeout(0.1)
    for household in households:
        if household.sms_available and not household.responded:
            sms_list.append(household)