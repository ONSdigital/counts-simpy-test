from functions.intervention_lists import intervention_lists
from functions.functions_field import remove_household_from_all_intervention_lists


def test_intervention_lists_initialises_empty_mutable_lists():
    # This test checks that intervention list container starts with independent empty lists for each intervention type.
    lists = intervention_lists()

    assert lists.sms_list == []
    assert lists.field_officer_list == []
    assert lists.reminder_card_list == []
    assert lists.sms_list is not lists.field_officer_list
    assert lists.field_officer_list is not lists.reminder_card_list


def test_units_share_supplied_sms_list_but_keep_separate_field_lists():
    sms_list = []
    first = intervention_lists(sms_list=sms_list)
    second = intervention_lists(sms_list=sms_list)

    assert first.sms_list is sms_list
    assert second.sms_list is sms_list
    assert first.field_officer_list is not second.field_officer_list
    sms_list.append("household")
    assert first.sms_list == second.sms_list == ["household"]

    remove_household_from_all_intervention_lists("household", second)
    assert sms_list == []
    assert first.sms_list == []
