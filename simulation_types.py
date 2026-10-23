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
