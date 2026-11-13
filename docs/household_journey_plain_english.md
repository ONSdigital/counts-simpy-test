# The Complete Census Model Journey

This connected flowchart describes the household's operational journey:
who is outstanding, who is selected for contact, what contact takes place and
what happens afterwards. It represents the **current model**, not a claim that
every step matches current census practice. Model assumptions and limitations
are identified separately for expert review.
Only the simple field behaviour is shown here; the detailed alternative remains
available in the model.

**Reading the chart:** solid arrows show routes and decisions; dotted arrows
show scheduling, shared effects or explanatory notes. Each event finishes by
returning to the shared simulation clock. Events involving lists repeat their
household checks for every household being considered. Dates and probabilities
shown as defaults are configurable.

```mermaid
flowchart TB
    subgraph DEFINITIONS["Key terms: how to read the household journey"]
        DEF_POPULATION["ACTIVE: still included in the census population, whether responded or not<br/>OUTSTANDING: has not yet responded<br/>RESPONDED: recorded as having completed the census<br/>VACANT / INACTIVE: identified as vacant and excluded from follow-up<br/>and the active population used to calculate response rates"]
        DEF_POPULATION ~~~ DEF_PAPER["REQUIRES PAPER / PAPER-FIRST: needs a paper questionnaire before using<br/>ordinary daily, SMS or reminder response routes; doorstep completion can bypass this<br/>REQUESTED PAPER / AWAITING PAPER: a questionnaire has been ordered<br/>through the contact centre or a field visit and has not yet arrived<br/>Receiving paper clears both restrictions; it does not usually mean a response"]
        DEF_PAPER ~~~ DEF_CONTACT["REFUSING: permanently marked as refusing; remains active and outstanding<br/>No further visits, contact-centre calls or daily, SMS or reminder responses<br/>Reminder mailings remain possible<br/>SMS-CONTACTABLE: a text-message contact route is available<br/>HARD-TO-COUNT CATEGORY: a model category from 1 to 5 used in field-list entry checks"]
        DEF_CONTACT ~~~ DEF_LISTS["OUTSTANDING LIST: households still awaiting a census response<br/>SMS LIST: households selected for possible later text-message contact<br/>FIELD FOLLOW-UP LIST: households available for visit consideration, not guaranteed a visit<br/>DUE FOR A VISIT: the household's wait before another visit has elapsed<br/>DOORSTEP COMPLETION: census completed during the officer's visit"]
    end
    DEF_LISTS ~~~ MC_START

    subgraph RUNS["1. Scenario setup and Monte Carlo repeats"]
        MC_START["Choose the scenario<br/>Regional populations and group shares, officer numbers,<br/>response chances, intervention dates, working hours,<br/>postal delays, starting weekday and run length"]
        MC_START --> MC_SEEDS["Choose the number of repeats (default 1) and a starting random seed<br/>Prepare a different reproducible seed for each repeat<br/>Keep the same scenario settings for every repeat"]
        MC_SEEDS --> MC_NEW["Start the next repeat from scratch<br/>No households, lists, stock or outstanding post carry over"]
        MC_NEW --> MC_SHARED["All regions take part in the same census period<br/>Share a central supply of paper questionnaires<br/>Use one national SMS list and text-message intervention<br/>Consider contact-centre demand across all regions"]
        MC_END["Stop this repeat at the chosen time<br/>Events exactly at or after the stop time do not run<br/>Some post may still be in transit"]
        MC_END --> MC_AGG["Combine officer-unit histories into regions,<br/>then combine regions into overall results"]
        MC_AGG --> MC_SAVE["Temporarily keep this repeat's daily response and call histories for averaging<br/>Final snapshot response counts and active population<br/>Total visits and visits by slot, doorstep completions,<br/>simple successes, calls, letters sent, delivered and reminder responses"]
        MC_SAVE --> MC_MORE{"Another repeat to run?"}
        MC_MORE -- "Yes: use the next seed" --> MC_NEW
        MC_MORE -- "No" --> MC_SUMMARY["Across repeats, calculate means and the<br/>2.5th and 97.5th percentiles<br/>These describe run variation, not confidence in the mean"]
        MC_SUMMARY --> MC_REPORT["Report regional and overall summaries<br/>Plot mean response trajectories, with a shaded 95% run interval<br/>for the overall curve in each national or regional panel<br/>Show group mean curves without shaded bands<br/>Mark field start, SMS days and reminder SENDING days"]
        MC_REPORT --> MC_RETAIN["Return combined results and the run seeds only<br/>Individual run histories and household states are not saved separately<br/>Daily calls are summarised but not plotted<br/>With one repeat, the mean and both interval bounds equal its result"]
    end

    subgraph GENERATE["2. Generate regions, officer units and households"]
        GEN_GROUPS["Represent the households in each region<br/>Match the chosen numbers in groups A, B and C<br/>Mix the groups before assigning officer workloads"]
        GEN_SEEDS["Use separate reproducible random draws for regional mixing,<br/>unit behaviour, contact-centre calls, national SMS and reminder letters<br/>All derive from this repeat's seed"]
        GEN_GROUPS -.-> GEN_SEEDS
        GEN_GROUPS --> GEN_UNITS["Give officers roughly equal numbers of households to cover<br/>Households in regions without officers can still use other response routes"]
        GEN_UNITS --> GEN_HOUSE["Identify each household's region,<br/>household group and responsible officer"]
        GEN_HOUSE --> GEN_TRAITS["Identify whether the household needs a paper questionnaire,<br/>can be contacted by text message and how hard it is to count"]
        GEN_TRAITS --> GEN_STATE["At the start of the census period:<br/>The household has not responded or refused<br/>It has not been visited and has no questionnaire on order"]
        GEN_STATE --> GEN_REGISTER["Begin the census response period<br/>Households may respond, request paper or receive follow-up<br/>Contact takes place on the planned intervention dates"]
        GEN_NOTE["Current assumptions:<br/>Paper need varies by household group<br/>SMS availability is 50% in every group<br/>Hard-to-count categories 1 to 5 are equally likely in every group<br/>Configured group differences for these last two traits are not used"]
        GEN_TRAITS -.-> GEN_NOTE
    end

    subgraph CLOCK["3. Progress through the census period"]
        CLK_NEXT["Continue through the census period<br/>The next activity may be a visit, response,<br/>call, mailing, delivery or review of outstanding households"]
        CLK_NEXT --> CLK_LIMIT{"Does it occur before the run stops?"}
        CLK_LIMIT -- "Yes" --> CLK_EVENT["When that activity takes place,<br/>check whether it still applies to the household"]
        CLK_EVENT --> CLK_KIND{"Which event is due?"}
        CLK_DONE["Continue to the next household or activity<br/>Households still outstanding may need further follow-up"]
        CLK_DONE --> CLK_NEXT
        CLK_ORDER["Usual order from day 1:<br/>Start of day: field visits<br/>Day + 0.55: field cleanup once it has begun<br/>Day + 0.8: ordinary response checks<br/>Day + 0.85: scheduled SMS and mailings, list updates and calls<br/>Day + 0.9: response snapshot"]
        CLK_EVENT -.-> CLK_ORDER
        CLK_TIES["Offsets indicate model order, not real clock hours<br/>Same-time events run one at a time in scheduling order<br/>Post can arrive between any daily stages<br/>Later events recheck eligibility after earlier state changes"]
        CLK_EVENT -.-> CLK_TIES
    end

    MC_SHARED --> GEN_GROUPS
    GEN_REGISTER --> CLK_NEXT
    CLK_LIMIT -- "No" --> MC_END

    subgraph INITIAL["4. Initial household journey: day 0"]
        INIT_CHECK{"At the start of the census:<br/>Can the household respond without receiving paper?"}
        INIT_CHECK -- "Yes" --> INIT_DRAW{"Does the household respond?<br/>Use its group's initial response chance"}
        INIT_DRAW -- "Yes" --> INIT_RESPONSE["Mark responded"]
        INIT_DRAW -- "No" --> INIT_OPEN["Identify households that have not yet responded<br/>Add them to their officer area's outstanding list<br/>They remain under consideration for response and follow-up<br/>Households that already responded are not added"]
        INIT_CHECK -- "No" --> INIT_OPEN
        INIT_RESPONSE --> INIT_OPEN
        INIT_OPEN --> CLK_DONE
        INIT_SMS{"At day 0 + 0.1:<br/>Is an outstanding household SMS-contactable?"}
        INIT_SMS -- "Yes" --> INIT_ADD["Add the household to the central national text-message contact list<br/>It may receive the later SMS intervention if still eligible<br/>The list is selected once across all regions at the start of the census<br/>Households needing paper can be listed but must receive paper first"]
        INIT_SMS -- "No" --> CLK_DONE
        INIT_ADD --> CLK_DONE
    end

    CLK_KIND -- "Initial responses and identification of nonrespondents" --> INIT_CHECK
    CLK_KIND -- "Select households for later text-message contact" --> INIT_SMS

    subgraph BASELINE["5. Ordinary daily response opportunity"]
        BASE_ELIG{"From day 1 + 0.8, daily:<br/>Active, outstanding, not refusing<br/>and no longer needing paper?"}
        BASE_ELIG -- "No" --> CLK_DONE
        BASE_ELIG -- "Yes" --> BASE_DRAW{"Does the household respond of its own accord today?<br/>Use its group's daily response chance"}
        BASE_DRAW -- "No" --> CLK_DONE
        BASE_DRAW -- "Yes" --> BASE_RESP["Mark responded<br/>Remove from the outstanding and SMS lists immediately"]
        BASE_RESP --> CLK_DONE
        BASE_NOTE["Days 1 to 50 use the group's daily sequence<br/>Later days keep the day-50 chance<br/>Interventions make separate attempts;<br/>they do not boost the ordinary daily chance"]
        BASE_DRAW -.-> BASE_NOTE
    end
    CLK_KIND -- "Daily response check" --> BASE_ELIG

    subgraph FIELD_LIST["6. Identify households for field follow-up and select visits"]
        FL_ADD_CHECK{"From day 1 + 0.85, daily:<br/>On the outstanding list, not refusing,<br/>not already on the field list,<br/>and previous knocks no greater than its hard-to-count category?"}
        FL_ADD_CHECK -- "Yes" --> FL_ADD["Add the household to its officer's field follow-up list<br/>It can now be considered for a visit on a later day<br/>Being listed does not guarantee a visit:<br/>the officer must have capacity and the household must be due"]
        FL_ADD_CHECK -- "No" --> CLK_DONE
        FL_ADD --> CLK_DONE
        FL_LIMIT_NOTE["The hard-to-count comparison is a list-entry check<br/>It is not enforced again as a strict maximum<br/>for households already on the field list"]
        FL_ADD_CHECK -.-> FL_LIMIT_NOTE
        FL_CLEAN["Review the field follow-up list and remove households that responded<br/>They no longer need a visit<br/>Review daily, starting the day after field operations begin"]
        FL_CLEAN --> CLK_DONE
        FL_WINDOW{"On a day in the field-operation period:<br/>Does this area have an officer making visits?"}
        FL_WINDOW -- "No" --> CLK_DONE
        FL_WINDOW -- "Yes" --> FL_CANDIDATES["Select from the field list in existing list order<br/>Active, outstanding, not refusing and due for a visit<br/>Awaiting paper does not prevent selection"]
        FL_CANDIDATES --> FL_WEEKDAY{"Is this Saturday or Sunday?"}
        FL_WEEKDAY -- "No" --> FL_WEEK["Allocate morning, then afternoon, then evening<br/>Each slot fills before the next"]
        FL_WEEKDAY -- "Yes" --> FL_WEEKEND["Allocate the weekend slot only"]
        FL_WEEK --> FL_CAPACITY["Limit each slot to whole visits:<br/>round down working hours times visits per hour<br/>At most one selection per household per day"]
        FL_WEEKEND --> FL_CAPACITY
        FL_CAPACITY --> FL_GUARD{"For each selected household:<br/>Still active, outstanding and not refusing?"}
        FL_GUARD -- "No" --> CLK_DONE
        FL_GUARD -- "Yes" --> FL_KNOCK["Count the knock and record household, day and slot<br/>All slots happen at the same simulated time"]
        FL_KNOCK --> SIM_DRAW
        FL_DEFAULTS["Default field window: days 7 to 30 inclusive<br/>Weekday capacities: 11 morning, 11 afternoon, 7 evening<br/>Weekend capacity: 30<br/>Slot labels choose probabilities, not separate clock times"]
        FL_CAPACITY -.-> FL_DEFAULTS
    end
    CLK_KIND -- "Field-list refresh" --> FL_ADD_CHECK
    CLK_KIND -- "Field-list response cleanup" --> FL_CLEAN
    CLK_KIND -- "Daily field visit batch" --> FL_WINDOW

    subgraph SIMPLE["7. Simple field behaviour: default mode"]
        SIM_DRAW["Knock on the door and establish one visit outcome:<br/>Complete at the doorstep, refuse, identify a vacancy,<br/>agree to respond or make no progress<br/>If another visit is needed, wait the revisit period"]
        SIM_DRAW --> SIM_DOOR{"Doorstep completion?"}
        SIM_DOOR -- "Yes" --> SIM_DOOR_RESP["Respond immediately, even if awaiting paper<br/>Count a doorstep completion"]
        SIM_DOOR_RESP --> CLK_DONE
        SIM_DOOR -- "No" --> SIM_WAIT{"Already awaiting paper?"}
        SIM_WAIT -- "Yes" --> SIM_NONE["No further outcome on this visit<br/>Remain outstanding until another opportunity"]
        SIM_WAIT -- "No" --> SIM_OTHER{"Which remaining outcome was drawn?"}
        SIM_OTHER -- "Refusal" --> STATE_REFUSE
        SIM_OTHER -- "Vacancy" --> STATE_VACANT
        SIM_OTHER -- "No outcome" --> SIM_NONE
        SIM_OTHER -- "Agrees to respond: ordinary success" --> SIM_PAPER{"Does the household need paper?"}
        SIM_PAPER -- "No" --> SIM_SUCCESS["Respond immediately and count a simple field success<br/>Remove from the outstanding and intervention lists"]
        SIM_SUCCESS --> CLK_DONE
        SIM_PAPER -- "Yes" --> PAPER_ORDER
        SIM_NONE --> CLK_DONE
        SIM_PROBS["Default per-knock chances:<br/>Doorstep 50%, refusal 1%, vacancy 5%,<br/>ordinary success 30% in each slot, no outcome 14%<br/>The outcome probabilities must sum to no more than 100%"]
        SIM_DRAW -.-> SIM_PROBS
    end

    subgraph CALLS["8. Contact-centre calls"]
        CALL_ELIG{"From day 1 + 0.85, daily:<br/>Active, outstanding, not refusing, requires paper<br/>and not already awaiting paper?"}
        CALL_ELIG -- "No" --> CALL_LOG
        CALL_ELIG -- "Yes" --> CALL_DRAW{"Does the household call to request paper today?<br/>Use the daily call chance"}
        CALL_DRAW -- "No" --> CALL_LOG
        CALL_DRAW -- "Yes" --> CALL_COUNT["Count one call and order a questionnaire<br/>No call duration, staffing limit or call queue is modelled"]
        CALL_COUNT --> PAPER_ORDER
        CALL_LOG["Record the day's call total across all regions"]
        CALL_LOG --> CLK_DONE
        CALL_NOTE["Refusing households cannot call or order paper through the contact centre<br/>Paper ordered before refusal can still arrive<br/>Calls do not themselves complete the census"]
        CALL_ELIG -.-> CALL_NOTE
    end
    CLK_KIND -- "Daily contact-centre call opportunity" --> CALL_ELIG
    CALL_COUNT -. "Include in daily total after processing households" .-> CALL_LOG

    subgraph PAPER["9. Shared paper stock, ordering and delivery"]
        PAPER_ORDER["Mark the household as awaiting paper<br/>Use the shared questionnaire service for every order"]
        PAPER_ORDER --> PAPER_STOCK{"Is questionnaire stock available?"}
        PAPER_STOCK -- "Yes" --> PAPER_USE["Use one questionnaire from stock<br/>Schedule arrival after the postal delay"]
        PAPER_STOCK -- "No" --> PAPER_PRINT["Schedule arrival after printing plus postal delay<br/>Each out-of-stock order gets that extra delay"]
        PAPER_USE --> CLK_DONE
        PAPER_PRINT --> CLK_DONE
        PAPER_USE -. "Arrival is a separate later event" .-> PAPER_ARRIVE
        PAPER_PRINT -. "Arrival is a separate later event" .-> PAPER_ARRIVE
        PAPER_ARRIVE{"At the scheduled arrival:<br/>Is the household still active?"}
        PAPER_ARRIVE -- "No" --> PAPER_INACTIVE["Clear the waiting flag<br/>Do not reactivate the household or count a response"]
        PAPER_INACTIVE --> CLK_DONE
        PAPER_ARRIVE -- "Yes" --> PAPER_RELEASE["Clear awaiting-paper and paper-first flags<br/>It can now use eligible daily, SMS and reminder opportunities"]
        PAPER_RELEASE --> PAPER_SOURCE{"Was this paper ordered because of<br/>a successful simple-mode field visit?"}
        PAPER_SOURCE -- "No: contact-centre order" --> PAPER_ELIGIBLE["Receiving paper does not itself complete the census<br/>The household may respond through later daily opportunities or interventions<br/>A future initial paper mailing would use this route; not yet implemented"]
        PAPER_ELIGIBLE --> CLK_DONE
        PAPER_SOURCE -- "Yes" --> PAPER_COMPLETE_CHECK{"Still outstanding and not refusing?"}
        PAPER_COMPLETE_CHECK -- "No" --> CLK_DONE
        PAPER_COMPLETE_CHECK -- "Yes" --> PAPER_COMPLETE["Fill in the questionnaire immediately on arrival<br/>Mark responded and count one simple field success<br/>Remove from the outstanding and intervention lists"]
        PAPER_COMPLETE --> CLK_DONE
        PAPER_TRANSIT["Awaiting paper blocks another paper order<br/>It does not block field visits or reminder mailings<br/>A simple doorstep completion can respond while post is in transit"]
        PAPER_ORDER -.-> PAPER_TRANSIT
    end
    CLK_KIND -- "Questionnaire delivery" --> PAPER_ARRIVE

    subgraph SMS["10. Scheduled national text-message interventions"]
        SMS_ELIG{"On each configured SMS day + 0.85:<br/>On the SMS list, active, outstanding,<br/>not refusing and no longer needing paper?"}
        SMS_ELIG -- "No" --> CLK_DONE
        SMS_ELIG -- "Yes" --> SMS_DRAW{"Does the household respond to the text message?<br/>Use the SMS response chance"}
        SMS_DRAW -- "Yes" --> SMS_RESP["Respond immediately<br/>Remove from the outstanding and SMS lists immediately"]
        SMS_DRAW -- "No" --> CLK_DONE
        SMS_RESP --> CLK_DONE
        SMS_DEFAULT["Default: SMS days = [20]; multiple days supported<br/>Response chance per send: 30%; unsuccessful households can be retried<br/>An empty schedule disables SMS; no separate delivery delay is modelled"]
        SMS_DRAW -.-> SMS_DEFAULT
    end
    CLK_KIND -- "SMS intervention" --> SMS_ELIG

    subgraph REMINDERS["11. Reminder mailing and arrival"]
        REM_ELIG{"On each sending day + 0.85:<br/>Is the household active and outstanding?"}
        REM_ELIG -- "No" --> CLK_DONE
        REM_ELIG -- "Yes" --> REM_SEND["Send one reminder and count it as sent<br/>Include paper-first, awaiting-paper and refusing households<br/>No printing delay or questionnaire-stock use"]
        REM_SEND --> REM_SCHEDULE["Schedule arrival after the postal delay<br/>No reminder waiting list is used<br/>Sending does not block other interventions"]
        REM_SCHEDULE --> CLK_DONE
        REM_SCHEDULE -. "Separate later event" .-> REM_ACTIVE
        REM_ACTIVE{"At reminder arrival:<br/>Is the household still active?"}
        REM_ACTIVE -- "No" --> REM_VACANT["Do not count delivery or attempt a response<br/>The letter remains counted as sent"]
        REM_VACANT --> CLK_DONE
        REM_ACTIVE -- "Yes" --> REM_DELIVERY["Count the letter as delivered<br/>Even if the household has responded since sending"]
        REM_DELIVERY --> REM_RESPONSE_ELIG{"Still outstanding, not refusing<br/>and no longer needing paper?"}
        REM_RESPONSE_ELIG -- "No" --> CLK_DONE
        REM_RESPONSE_ELIG -- "Yes" --> REM_DRAW{"Does the household respond after receiving the reminder?<br/>Use the reminder response chance"}
        REM_DRAW -- "No" --> CLK_DONE
        REM_DRAW -- "Yes" --> REM_RESP["Respond and count a reminder response<br/>Remove from outstanding and all intervention lists"]
        REM_RESP --> CLK_DONE
        REM_DEFAULT["Default sending days: 10, 20 and 30<br/>Postal delay: 3 days; arrival at day + 0.85<br/>One-off reminder response chance: 40%<br/>A later mailing can send another letter if still outstanding"]
        REM_SEND -.-> REM_DEFAULT
    end
    CLK_KIND -- "Reminder sending" --> REM_ELIG
    CLK_KIND -- "Reminder delivery" --> REM_ACTIVE

    subgraph STATES["12. Shared household states and their effects"]
        STATE_REFUSE["Permanent refusal<br/>Keep active and outstanding; remove from the field list<br/>No more field visits, contact-centre calls, ordinary daily responses,<br/>SMS responses or reminder responses<br/>Reminder mailings remain possible"]
        STATE_REFUSE --> CLK_DONE
        STATE_VACANT["Mark vacant and inactive; clear awaiting paper<br/>Remove from outstanding and all intervention lists<br/>Exclude from the active response denominator"]
        STATE_VACANT --> CLK_DONE
        STATE_RESPONSE["After any response:<br/>Keep the household in response reporting<br/>No further response attempts, new mailings, calls or visits<br/>Already posted mail can still arrive"]
        STATE_STALE["Every response removes the household from the SMS list immediately<br/>Ordinary daily or SMS respondents may remain on the field list until review<br/>Current-state checks prevent further visits"]
        STATE_RESPONSE -.-> STATE_STALE
        BASE_RESP -.-> STATE_RESPONSE
        INIT_RESPONSE -.-> STATE_RESPONSE
        SIM_DOOR_RESP -.-> STATE_RESPONSE
        SIM_SUCCESS -.-> STATE_RESPONSE
        PAPER_COMPLETE -.-> STATE_RESPONSE
        SMS_RESP -.-> STATE_RESPONSE
        REM_RESP -.-> STATE_RESPONSE
    end

    subgraph REPORTING["13. Daily observations and model boundaries"]
        OBS_SNAPSHOT["At day 0 + 0.9, then daily:<br/>Record active and responded counts and response proportions<br/>Record the same by household group<br/>Label the snapshot with that integer simulation day"]
        OBS_SNAPSHOT --> CLK_DONE
        OBS_COUNTS["Maintain event counters throughout the run<br/>Visits and doorstep completions at the knock<br/>Simple successes at completion<br/>Calls when ordered; reminders when sent, delivered or successful"]
        OBS_SNAPSHOT -.-> OBS_COUNTS
        OBS_FINAL["Final reported response totals use the last daily snapshot<br/>Event totals count events completed before the stop time<br/>These can refer to slightly different times within the last day"]
        OBS_COUNTS -.-> OBS_FINAL
        OBS_LIMITS["Current model boundaries:<br/>No geography-based travel or route optimisation<br/>No real within-day visit durations<br/>No separate printing capacity or postal queue<br/>No separate paper-return journey<br/>Stored intervention prices do not calculate costs"]
        OBS_SNAPSHOT -.-> OBS_LIMITS
    end
    CLK_KIND -- "Daily response snapshot" --> OBS_SNAPSHOT
    OBS_FINAL -.-> MC_SAVE

    classDef note fill:#eef4fa,stroke:#52718c,color:#172b3a;
    class GEN_NOTE,CLK_ORDER,CLK_TIES,FL_LIMIT_NOTE,FL_DEFAULTS,SIM_PROBS,CALL_NOTE,PAPER_TRANSIT,SMS_DEFAULT,REM_DEFAULT,STATE_STALE,OBS_FINAL,OBS_LIMITS note;
```

Source sections: [regional and household setup](../functions/function_core.py),
[household responses](../functions/functions_households.py),
[field operations](../functions/functions_field.py),
[calls and paper deliveries](../functions/functions_contact_centre.py),
[SMS](../functions/functions_sms.py),
[reminders](../functions/functions_reminder_letters.py),
[run orchestration and Monte Carlo summaries](../functions/simulation_runner.py),
[reporting](../functions/functions_output.py), and [parameters](../parameters.py).

The [original technical flowchart](household_journey_flowchart.md) remains
available separately. This document does not change simulation behaviour.
