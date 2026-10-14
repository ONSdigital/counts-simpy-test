#import packages
import simpy
import random 
import functions.functions_households as hh
import functions.functions_field as field
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
field_visit_day = params.field_visit_day
field_visit_duration = params.field_visit_duration
field_visit_response_boost = params.field_visit_response_boost
field_daily_queue_size = params.field_daily_queue_size

#setup environment
env = simpy.Environment()


#setup dummy households
hh_list = [hh.Household(id=i, rng=rng, baseline_response_probability=baseline_response_probability, first_day_probability=first_day_probability) for i in range(num_of_households)]

#setup intervention lists
intervention_lists = il.intervention_lists()
print(intervention_lists.sms_list)
field_officer = field.create_field_officer(env)

#setup processes
env.process(hh.first_day_responses(env, hh_list, rng))
env.process(hh.daily_response_updates(env, hh_list, rng))
env.process(sms.sms_day_n_increase_baseline(env, intervention_lists.sms_list, sms_timing))
env.process(out.daily_response_totals(env, hh_list))
env.process(sms.populate_sms_list(env, hh_list, intervention_lists.sms_list))
env.process(field.populate_field_officer_list(env, hh_list, intervention_lists.field_officer_list))
env.process(
	field.queue_field_officer_visits(
		env,
		field_officer,
		intervention_lists.field_officer_list,
		start_day=field_visit_day,
		visit_duration=field_visit_duration,
		response_probability_increase=field_visit_response_boost,
		queue_size=field_daily_queue_size,
		random_source=rng,
	)
)
env.process(field.end_of_day_remove_responded_houses(env, intervention_lists.field_officer_list, field_visit_day))

#run simulation
env.run(until = 50)
