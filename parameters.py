import dataclasses as dc
import math


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
FIELD_VISIT_SLOTS = ("morning", "afternoon", "evening", "weekend")


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

    # Weekday at simulation time zero; subsequent weekdays change at integer days.
    census_start_weekday: str = "Monday"

    # Starting seed for reproducible household and intervention random draws.
    seed: int = 1

    # Independent simulation runs used to report means and central 95% run intervals.
    monte_carlo_repeats: int = 1

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
    # Select simple per-knock outcomes or the original answered-door decision tree.
    field_visit_mode: str = "simple"
    field_vacancy_probability: float = 0.05
    field_success_probability_by_slot: dict[str, float] = dc.field(
        default_factory=lambda: dict.fromkeys(FIELD_VISIT_SLOTS, 0.3)
    )

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

    # Chance an eligible household returns on each SMS sending day.
    sms_response_probability: float = 0.3

    # One-off return chance after answering, with no doorstep completion or paper order.
    field_visit_response_probability_if_answer_by_slot: dict[str, float] = dc.field(
        default_factory=lambda: dict.fromkeys(FIELD_VISIT_SLOTS, 0.3)
    )
    
    # One-off return chance for eligible households after no answer and no vacancy.
    field_visit_response_probability_if_no_answer: float = 0.2
    
    # Chance a household answers the door during a visit.
    field_answer_door_probability_by_slot: dict[str, float] = dc.field(
        default_factory=lambda: dict.fromkeys(FIELD_VISIT_SLOTS, 0.3)
    )
    
    # Chance an unanswered visit identifies a vacancy and removes the household.
    field_vacancy_probability_if_no_answer: float = 0.05

    # Daily call chance for non-refusing outstanding paper-first households not awaiting paper.
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

    # Simulation days on which reminders are posted to all active non-respondents.
    reminder_letter_days: list[int] = dc.field(default_factory=lambda: [10, 20, 30])

    # Simple-mode probability of becoming a permanent refusal on each knock.
    refusal_probability: float = 0.01

    # Hours per officer in each weekday slot, or per day on Saturday/Sunday.
    field_officer_working_hours_by_slot: dict[str, float] = dc.field(
        default_factory=lambda: {
            "morning": 3.0, "afternoon": 3.0, "evening": 2.0, "weekend": 8.0,
        }
    )

    # Number of visits a field officer completes per hour.
    field_officer_visits_per_hour: float = 3.75

##Variable parameters
   

    # Simulation days on which SMS messages are sent, late in each day.
    sms_days: list[int] = dc.field(default_factory=lambda: [20])
    
    # First day officers launch visits.
    field_first_day: int = 7

    # Last day officers complete visits.
    field_last_day: int = 30

    # Days used to defer repeat field visits.
    field_days_until_next_visit: int = 3

    # Simple: unconditional per-knock outcome. Detailed: conditional on answering.
    field_doorstep_completion_probability: float = 0.5

    # Shared paper questionnaire stock available without an extra printing delay.
    initial_paper_batch: int = 500

    # Delivery time in days for an ordered paper questionnaire.
    pQ_postal_delay: float = 3

    # Extra delivery delay in days for each paper order after stock runs out.
    printing_delay: float = 2

    # Stored intervention prices; no costs are currently calculated in the model.
    intervention_costs: dict[str, float] = dc.field(
        default_factory=lambda: {"sms": 0.05}
    )

    def field_visit_capacities_at(self, simulation_time: float) -> dict[str, int]:
        """Return whole-visit capacity per active slot for one officer on this day."""
        slots = (
            ("weekend",)
            if self.weekday_at(simulation_time) in ("Saturday", "Sunday")
            else FIELD_VISIT_SLOTS[:3]
        )
        return {
            slot: math.floor(
                self.field_officer_working_hours_by_slot[slot] * self.field_officer_visits_per_hour
            )
            for slot in slots
        }

    def weekday_at(self, simulation_time: float) -> str:
        """Return the weekday at a non-negative simulation time, including fractional days."""
        if (
            isinstance(simulation_time, bool)
            or not isinstance(simulation_time, (int, float))
            or not math.isfinite(simulation_time)
            or simulation_time < 0
        ):
            raise ValueError("Simulation time must be a finite non-negative number")
        start_index = WEEKDAYS.index(self.census_start_weekday)
        return WEEKDAYS[(start_index + math.floor(simulation_time)) % 7]

    def __post_init__(self):
        if self.field_visit_mode not in ("simple", "detailed"):
            raise ValueError("field_visit_mode must be 'simple' or 'detailed'")
        for name in (
            "refusal_probability", "field_vacancy_probability",
            "field_doorstep_completion_probability",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 0 <= value <= 1
            ):
                raise ValueError(f"{name} must be finite and in [0, 1]")
        if self.census_start_weekday not in WEEKDAYS:
            raise ValueError("census_start_weekday must be a weekday name from Monday to Sunday")
        for name in ("sms_days", "reminder_letter_days"):
            days = getattr(self, name)
            if (
                not isinstance(days, list)
                or any(
                    isinstance(day, bool) or not isinstance(day, int) or day < 0
                    for day in days
                )
                or len(set(days)) != len(days)
            ):
                raise ValueError(f"{name} must be a list of unique non-negative integers")
        probability = self.reminder_letter_response_probability
        if (
            isinstance(probability, bool)
            or not isinstance(probability, (int, float))
            or not math.isfinite(probability)
            or not 0 <= probability <= 1
        ):
            raise ValueError("reminder_letter_response_probability must be finite and in [0, 1]")
        delay = self.pQ_postal_delay
        if (
            isinstance(delay, bool)
            or not isinstance(delay, (int, float))
            or not math.isfinite(delay)
            or delay < 0
        ):
            raise ValueError("pQ_postal_delay must be finite and non-negative")
        if (
            isinstance(self.monte_carlo_repeats, bool)
            or not isinstance(self.monte_carlo_repeats, int)
            or self.monte_carlo_repeats < 1
        ):
            raise ValueError("monte_carlo_repeats must be a positive integer")
        if not self.regions:
            raise ValueError("At least one region must be configured")
        for name, region in self.regions.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Each region must have a non-empty name")
            if not isinstance(region, RegionParameters):
                raise ValueError("Each region must contain RegionParameters")
        for name in (
            "field_officer_working_hours_by_slot",
            "field_answer_door_probability_by_slot",
            "field_visit_response_probability_if_answer_by_slot",
            "field_success_probability_by_slot",
        ):
            values = getattr(self, name)
            if not isinstance(values, dict) or set(values) != set(FIELD_VISIT_SLOTS):
                raise ValueError(f"{name} must contain exactly {FIELD_VISIT_SLOTS}")
            for value in values.values():
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value < 0
                    or (name != "field_officer_working_hours_by_slot" and value > 1)
                ):
                    raise ValueError(f"{name} must contain finite non-negative hours or probabilities in [0, 1]")
        if self.field_visit_mode == "simple":
            for slot, success in self.field_success_probability_by_slot.items():
                total = math.fsum((
                    self.field_doorstep_completion_probability, self.refusal_probability,
                    self.field_vacancy_probability, success,
                ))
                if total > 1:
                    raise ValueError(f"Simple field outcome probabilities for {slot} must sum to at most 1")
        rate = self.field_officer_visits_per_hour
        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not math.isfinite(rate)
            or rate <= 0
        ):
            raise ValueError("field_officer_visits_per_hour must be finite and positive")
        if any(
            not math.isfinite(hours * rate)
            for hours in self.field_officer_working_hours_by_slot.values()
        ):
            raise ValueError("Field visit capacity must be finite")
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
