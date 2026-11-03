import dataclasses as dc
import math


@dc.dataclass(frozen=True)
class RegionParameters:
    # Total households created in this region.
    num_households: int = 10000
    # Officers assigned to this region; zero disables its field visits.
    num_field_officers: int = 10
    # Regional A/B/C population shares, summing to one; rounded to whole households.
    household_type_proportions: dict[str, float] = dc.field(
        default_factory=lambda: {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}
    )

    def __post_init__(self):
        for name in ("num_households", "num_field_officers"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        shares = self.household_type_proportions
        if set(shares) != {"A", "B", "C"}:
            raise ValueError("Regional household shares must include exactly groups A, B and C")
        if any(not 0 <= share <= 1 for share in shares.values()):
            raise ValueError("Regional household shares must be between 0 and 1")
        if not math.isclose(sum(shares.values()), 1.0, rel_tol=0, abs_tol=1e-9):
            raise ValueError("Regional household shares must sum to 1")

#define a class that holds the parameters for the simulation
@dc.dataclass(frozen=True)
class SimulationParameters:
##Scenario labelling, randomness, and geography
    # Scenario label stored with results; does not change model behaviour.
    scenario_name: str = "baseline"

    # Starting seed for reproducible household and intervention random draws.
    seed: int = 1

 # Regional populations, officer counts and A/B/C splits; illustrative defaults only.
    regions: dict[str, RegionParameters] = dc.field(
        default_factory=lambda: {
            "North East": RegionParameters(),
            "North West": RegionParameters(),
            "Yorkshire and the Humber": RegionParameters(),
            "East Midlands": RegionParameters(),
            "West Midlands": RegionParameters(),
            "East of England": RegionParameters(),
            "London": RegionParameters(num_households = 10000, num_field_officers = 50, household_type_proportions={"A": 0.9, "B": 0.1, "C": 0}),
            "South East": RegionParameters(),
            "South West": RegionParameters(),
            "Wales": RegionParameters(),
        }
    )

##Fixed parameters
    # Daily baseline return chances by group for days 1-50; later days use day 50.
    # Each group's first value also sets its time-zero return chance.
    daily_response_probabilities_by_group: dict[str, list[float]] = dc.field(
        default_factory=lambda: {
            "A": [0.05] * 50,
            "B": [0.05] * 50,
            "C": [0.05] * 50,
        }
    )
    # Chance a household in each group needs paper
    paper_first_probability_by_group: dict[str, float] = dc.field(
        default_factory=lambda: {"A": 0.9, "B": 0.1, "C": 0.5}
    )

    # One-off chance an eligible household returns when SMS is sent.
    sms_response_probability: float = 0.3

    # One-off return chance after answering, with no doorstep completion or paper order.
    field_visit_response_probability_if_answer: float = 0.5
    
    # One-off return chance for eligible households after no answer and no vacancy.
    field_visit_response_probability_if_no_answer: float = 0.2
    
    # Chance a household answers the door during a visit.
    field_answer_door_probability: float = 0.3
    
    # Chance an unanswered visit identifies a vacancy and removes the household.
    field_vacancy_probability_if_no_answer: float = 0.05

    # Daily chance an outstanding paper-first household calls contact centre, if not awaiting paper.
    call_centre_call_probability: float = 0.3

    #probability of phone number being available
    phone_number_probability_by_group: dict[str, float] = dc.field(
        default_factory=lambda: {"A": 0.9, "B": 0.1, "C": 0.5}
    )

    #proportion of households in each group that are hard to count 1, 2, 3, 4, 5
    hard_to_count_probability_by_group: dict[str, float] = dc.field(
        default_factory=lambda: {"A": 0.1, "B": 0.2, "C": 0.3}
    )

    #response rate to a reminder letter
    reminder_letter_response_probability: float = 0.4

    #probability a household is a refusal
    refusal_probability: float = 0.01

    

##Variable parameters
   

    # Day of the single SMS send, late in the simulated day.
    sms_timing: int = 20
    
    # First day officers launch visits.
    field_first_day: int = 7

    # Last day officers complete visits.
    field_last_day: int = 30

    # Days used to defer repeat field visits.
    field_days_until_next_visit: int = 3

    # Chance of immediate doorstep completion after answering, if not awaiting paper.
    field_doorstep_completion_probability: float = 0.5

    # Shared paper questionnaire stock available without an extra printing delay.
    initial_paper_batch: int = 500

    # Delivery time in days for an ordered paper questionnaire.
    pQ_postal_delay: float = 3

    # Extra delivery delay in days for each paper order after stock runs out.
    printing_delay: float = 2

    # Maximum visits completed per officer each day, all at the same simulated time.
    daily_field_visits: int = 30

    # Stored intervention prices; no costs are currently calculated in the model.
    intervention_costs: dict[str, float] = dc.field(
        default_factory=lambda: {"sms": 0.05}
    )

    def __post_init__(self):
        if not self.regions:
            raise ValueError("At least one region must be configured")
        for name, region in self.regions.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Each region must have a non-empty name")
            if not isinstance(region, RegionParameters):
                raise ValueError("Each region must contain RegionParameters")
        if (
            isinstance(self.daily_field_visits, bool)
            or not isinstance(self.daily_field_visits, int)
            or self.daily_field_visits < 0
        ):
            raise ValueError("daily_field_visits must be a non-negative integer")
        table = self.daily_response_probabilities_by_group
        if set(table) != {"A", "B", "C"}:
            raise ValueError("Daily response probabilities must include exactly groups A, B and C")
        for group, probabilities in table.items():
            if len(probabilities) != 50:
                raise ValueError(f"Group {group} must have exactly 50 daily response probabilities")
            if any(not 0 <= probability <= 1 for probability in probabilities):
                raise ValueError(f"Group {group} probabilities must be between 0 and 1")


# Name the baseline parameters used by default in simulation.py and app_streamlit.py
baseline_parameters = SimulationParameters()

# Example scenario variant. Kept as a usage example, not used as the default run baseline.
PoC_parameters = dc.replace(baseline_parameters, scenario_name = "PoC_scenario")

