#returns snapshot of the returns over last three days
def daily_response_totals(env, households):
    response_list = []
    while True:
        yield env.timeout(1)
        response_list.append(sum(h.responded for h in households))
        print(f"on day {env.now}, the last 3 days of response are {response_list[-3:]}")