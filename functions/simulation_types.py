import dataclasses as dc

import simpy

import functions.intervention_lists as il


@dc.dataclass
class UnitState:
    unit_id: int
    households: list
    open_households: list
    intervention_lists: il.intervention_lists
    field_officer: simpy.Resource
    return_history: dict
    field_visit_history: list[dict] = dc.field(default_factory=list)
    reminder_letter_history: dict = dc.field(default_factory=lambda: {
        "time": [], "letters_sent": [], "total_letters_sent": 0,
        "letters_delivered": 0, "responses": 0,
    })


@dc.dataclass
class RegionState:
    name: str
    units: list[UnitState]
    return_history: dict

    @property
    def households(self):
        return [household for unit in self.units for household in unit.households]
