class intervention_lists:
    """Store the mutable intervention lists used during a simulation run."""

    def __init__(self, sms_list=None):
        """Reference the supplied national SMS list and create local intervention lists."""

        self.sms_list = sms_list if sms_list is not None else []
        self.field_officer_list = []
        self.reminder_card_list = []
