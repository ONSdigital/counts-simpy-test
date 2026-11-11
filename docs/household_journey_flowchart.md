# Household Journey Flowchart

This file stores the Mermaid source code for the household-level end-to-end model flow.

```mermaid
flowchart TD
    R["One shared SimPy clock<br/>One shared call centre and paper stock<br/>One national SMS list and intervention"] --> RC["For each region:<br/>allocate A/B/C household counts<br/>divide households between its officers"]
    RC --> A
    A["t=0.0<br/>Create household<br/>hard_to_count=1..5<br/>sms_available=True/False<br/>responded=False<br/>waiting_for_pq=False<br/>is_active=True<br/>field_knocks=0<br/>next_field_visit_day=0"] --> B["t=0.0<br/>First-day check"]

    B --> B1{"responded=False<br/>refusal=False<br/>paper_first=False?"}
    B1 -- No --> P
    B1 -- Yes --> B2{"rand < first group-table value?"}
    B2 -- Yes --> B3["responded=True"]
    B2 -- No --> P
    B3 --> P

    P["Parallel processes"] --> S0["t=0.1<br/>Populate national sms_list once across all regions"]
    S0 --> S1{"sms_available=True<br/>and responded=False?"}
    S1 -- Yes --> S2["Add to sms_list"]
    S1 -- No --> S3["Do not add"]

    S2 --> S4["t=day+0.85 for each sorted sms_days entry<br/>One national SMS send per configured day"]
    S3 --> S4
    S4 --> S6{"Listed, active, not responded,<br/>not refusing, not paper-first?"}
    S6 -- Yes --> S7{"rand < sms_response_probability?"}
    S7 -- Yes --> S8["responded=True<br/>remove from open households and sms_list immediately"]
    S6 -- No --> SMS_END["End this day's SMS intervention<br/>No delayed cleanup"]
    S7 -- No --> SMS_END
    S8 --> SMS_END
    SMS_END -- More configured days --> S4

    P --> D0["t=1.8, 2.8, 3.8...<br/>Daily response loop"]
    D0 --> D4["Read group/day baseline table<br/>days after 50 use day 50<br/>no intervention carryover"]
    D4 --> D1{"is_active=True<br/>responded=False<br/>refusal=False<br/>paper_first=False?"}
    D1 -- Yes --> D2{"rand < response_probability?"}
    D2 -- Yes --> D3["responded=True<br/>remove from open households and sms_list immediately"]
    D2 -- No --> D0
    D1 -- No --> D0
    D3 --> D0

    P --> C0["t=1.85 then daily<br/>Call-centre loop"]
    C0 --> C1{"is_active & paper_first<br/>not responded, not refusing<br/>not waiting_for_pq?"}
    C1 -- No --> C0
    C1 -- Yes --> C2{"rand < call probability?"}
    C2 -- No --> C0
    C2 -- Yes --> C3["Order PQ<br/>waiting_for_pq=True<br/>delay=postal or printing+postal"]
    C3 --> C4["At delivery time"]
    C4 --> C5{"is_active?"}
    C5 -- No --> C6["waiting_for_pq=False"]
    C5 -- Yes --> C7["paper_first=False<br/>waiting_for_pq=False"]
    C6 --> C0
    C7 --> C0

    P --> F0["t=1.85 then daily<br/>Populate field_officer_list"]
    F0 --> F1{"field_knocks <= hard_to_count<br/>and not responded<br/>and not refusing<br/>and not already in list?"}
    F1 -- Yes --> F2["Add to field list"]
    F1 -- No --> F0
    F2 --> F0

    P --> R0["Each reminder_letter_days day + 0.85:<br/>post to all active non-respondents<br/>record letters sent"]
    R0 --> R1["Wait pQ_postal_delay<br/>no printing delay or paper stock use"]
    R1 --> R2{"Active, not responded,<br/>not paper-first, not refusing?"}
    R2 -- Yes --> R3{"rand below<br/>reminder_letter_response_probability?"}
    R3 -- Yes --> R4["responded=True<br/>remove from open households<br/>and all intervention lists<br/>record reminder response"]
    R2 -- No --> R5["No response attempt"]
    R3 -- No --> R6["No lasting probability change"]

    P --> Q0["Visit days:<br/>field_first_day through field_last_day"]
    Q0 --> Q1["Each day:<br/>active, not responded, not refusing<br/>and next_field_visit_day<=today<br/>Mon-Fri: morning, afternoon, evening<br/>Sat-Sun: weekend only<br/>slot limit=floor(hours x visits/hour)<br/>at most one visit per household per day"]
    Q1 --> Q2["Complete all selected visits<br/>at the same timestamp<br/>repeat next day"]

    Q2 --> V0["Visit:<br/>no elapsed time<br/>field_knocks += 1<br/>record time, household ID and slot"]
    V0 --> MODE{"field_visit_mode?"}
    MODE -- detailed --> V1{"Answer door?<br/>probability by slot"}
    MODE -- simple --> S0{"One draw:<br/>doorstep probability?"}
    S0 -- Yes --> S1["Immediate response<br/>doorstep_completions += 1<br/>remove from open and intervention lists"]
    S0 -- No --> S2{"Awaiting paper?"}
    S2 -- Yes --> S9["No outcome<br/>normal revisit delay"]
    S2 -- No --> S3{"Same draw:<br/>refusal, vacancy, success, remainder"}
    S3 -- refusal --> S4["refusal=True<br/>no further field visits"]
    S3 -- vacancy --> V11
    S3 -- remainder --> S9
    S3 -- success --> S5{"Paper-first?"}
    S5 -- No --> S6["Immediate response<br/>simple_field_successes += 1<br/>remove from open and intervention lists"]
    S5 -- Yes --> S7["Order shared-stock paper<br/>postal plus any printing delay<br/>normal revisit delay"]
    S7 --> S8["On delivery if still eligible:<br/>responded=True<br/>simple_field_successes += 1<br/>remove from open and intervention lists"]

    V1 -- Yes --> V2{"waiting_for_pq?"}
    V2 -- Yes --> V3["next_field_visit_day += days_until_next_visit"]
    V2 -- No --> V4{"Doorstep completion?"}
    V4 -- Yes --> V5["responded=True<br/>remove from field list"]
    V4 -- No --> V6{"paper_first and<br/>not waiting_for_pq?"}
    V6 -- Yes --> V7["Order PQ<br/>waiting_for_pq=True"]
    V6 -- No --> V8{"not refusing and rand <br/>response probability after answer<br/>for assigned slot?"}
    V7 --> V9["next_field_visit_day =<br/>int(now)+days_until_next_visit"]
    V8 -- No --> V9
    V8 -- Yes --> V14["responded=True<br/>remove from open households<br/>and intervention lists"]
    V14 --> Q0
    V3 --> Q0
    V5 --> Q0
    V9 --> Q0

    V1 -- No --> V10{"Vacant on no-answer?"}
    V10 -- Yes --> V11["Set is_active=False<br/>waiting_for_pq=False<br/>remove from households<br/>remove from all lists"]
    V10 -- No --> V13{"not paper-first, not refusing<br/>and rand < response_probability_if_no_answer?"}
    V13 -- Yes --> V14
    V13 -- No --> V12["next_field_visit_day =<br/>int(now)+days_until_next_visit"]
    V11 --> Q0
    V12 --> Q0

    P --> E0["t=field_visit_day+0.55 then daily<br/>Field list cleanup"]
    E0 --> E1["Keep only households<br/>with responded=False"]
    E1 --> E0
```
