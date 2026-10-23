from functions.intervention_lists import intervention_lists


def test_intervention_lists_initialises_empty_mutable_lists():
    # This test checks that intervention list container starts with independent empty lists for each intervention type.
    lists = intervention_lists()

    assert lists.sms_list == []
    assert lists.field_officer_list == []
    assert lists.reminder_card_list == []
    assert lists.sms_list is not lists.field_officer_list
    assert lists.field_officer_list is not lists.reminder_card_list
