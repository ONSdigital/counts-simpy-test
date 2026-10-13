#import packages
import simpy
import random 
import functions.functions_households as hh
import functions.functions_sms as sms
import functions.functions_output as out
import functions.intervention_lists as il

#import scenario parameters
from parameters import new_scenario_parameters as params
num_of_households = params.num_households
sms_response_probability = params.sms_response_probability
SEED = params.seed
rng = random.Random(SEED)
sms_timing = params.sms_timing
intervention_costs = params.intervention_costs
baseline_response_probability = params.baseline_response_probability
first_day_probability = params.first_day_probability

#setup environment
env = simpy.Environment()

#setup dummy households
hh_list = [hh.Household(id=i, rng=rng, baseline_response_probability=baseline_response_probability, first_day_probability=first_day_probability) for i in range(num_of_households)]

#setup intervention lists
intervention_lists = il.intervention_lists()

#setup processes
env.process(hh.first_day_responses(env, hh_list, rng))
env.process(hh.daily_response_updates(env, hh_list, rng))
env.process(sms.sms_day_n_increase_baseline(env, intervention_lists.sms_list, sms_timing))
env.process(out.daily_response_totals(env, hh_list))


#run simulation
env.run(until = 50)
