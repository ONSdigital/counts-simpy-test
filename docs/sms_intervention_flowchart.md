# SMS Intervention: The Household Journey

This chart shows how the current model selects households for text-message
contact, checks whether they can respond and removes them from the SMS list.
Being on the list does not guarantee an SMS response opportunity.

```mermaid
flowchart TD
    subgraph SELECT["1. Select households for text-message contact"]
        START["At the start of the census:<br/>households have their initial chance to respond"]
        START --> OUTSTANDING{"Has the household still not responded?"}
        OUTSTANDING -- "No" --> NOT_LISTED["Do not add to the SMS list"]
        OUTSTANDING -- "Yes" --> CONTACT{"Is a text-message contact route available?"}
        CONTACT -- "No" --> NOT_LISTED
        CONTACT -- "Yes" --> ADD["Add to one central SMS list covering all regions<br/>It is selected for possible contact on the planned SMS day"]
        ADD --> WAIT["Remain listed while waiting for the SMS day<br/>Being listed does not stop visits, calls, mail or other response opportunities"]
        ONCE["The list is selected once, shortly after initial responses on day 0<br/>No households are added later<br/>Households requiring paper can be listed"]
        ADD -.-> ONCE
    end

    subgraph CHANGES["2. Other events can change the household's position"]
        CHANGE{"What happens while the household is listed?"}
        WAIT --> CHANGE
        CHANGE -- "Vacant" --> VACANT_ROUTE[" "]
        VACANT_ROUTE --> REMOVE_NOW["Remove from the SMS list immediately"]
        CHANGE -- "Other successful intervention" --> REMOVE_NOW
        CHANGE -- "Responds of its own accord" --> DAILY_REMOVE["Remove from the SMS list immediately<br/>For example, a day-9 respondent is not listed for day-10 SMS"]
        CHANGE -- "Refuses during a field visit" --> REFUSAL["Remain on the SMS list, but cannot respond through SMS"]
        CHANGE -- "Receives a questionnaire without automatically responding" --> PAPER["No longer requires paper<br/>Can use the SMS response opportunity if still otherwise eligible"]
        CHANGE -- "Nothing changes" --> DAY
        DAILY_REMOVE --> OFF
        REFUSAL --> DAY
        PAPER --> DAY
        REMOVE_NOW --> OFF["No longer on the SMS list"]
    end

    subgraph INTERVENTION["3. One planned text-message intervention"]
        DAY["On the configured SMS day, later in the day<br/>Default: day 20<br/>One national intervention considers each household still on the central SMS list"]
        DAY --> ELIGIBLE{"Still in the census population,<br/>not responded, not refusing<br/>and no longer requiring paper?"}
        ELIGIBLE -- "No" --> SKIP["No SMS response attempt for this household<br/>Listing alone is not enough to make it eligible"]
        ELIGIBLE -- "Yes" --> ATTEMPT["Give the household one chance to respond to the text message<br/>Default response chance: 30%"]
        ATTEMPT --> SUCCESS{"Does the household respond?"}
        SUCCESS -- "Yes" --> RESPONSE["Record its census response immediately<br/>Remove from the outstanding-household and SMS lists immediately"]
        RESPONSE --> OFF
        SUCCESS -- "No" --> NO_RESPONSE["Remain outstanding and on the SMS list<br/>Other response opportunities remain available if eligible"]
        NOTES["The model combines SMS contact and its response attempt<br/>No separate delivery delay, delivery failure or later SMS reply is modelled<br/>An unsuccessful attempt does not change the ordinary daily response chance"]
        ATTEMPT -.-> NOTES
    end

    subgraph AFTER["4. After the one-off intervention"]
        SKIP --> REMAIN["Remain on the SMS list if still listed<br/>No second SMS intervention or scheduled housekeeping review occurs"]
        NO_RESPONSE --> REMAIN
        REMAIN --> LATER["Any later response, whether of its own accord or through an intervention,<br/>removes the household immediately<br/>Identification of a vacancy also removes it immediately"]
        LATER -. "If removed by another route" .-> OFF
    end
    style VACANT_ROUTE fill:transparent,stroke:transparent
```

**Terms:** outstanding means not yet responded. A household remains in the
census population unless identified as vacant. Requiring paper prevents an SMS
response until a questionnaire has arrived; merely ordering it is not enough.

Selection occurs at day 0 + 0.1; the intervention at the configured day + 0.85;
there is no delayed cleanup. These offsets indicate simulation order, not
real clock times. Other events can occur between these stages, and eligibility
is checked using the household's state at the time of the intervention.

Sources: [SMS selection and intervention](../functions/functions_sms.py),
[process registration](../functions/function_core.py),
[ordinary responses](../functions/functions_households.py),
[field responses and vacancy removal](../functions/functions_field.py), and
[reminder responses](../functions/functions_reminder_letters.py).
