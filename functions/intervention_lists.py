class intervention_lists:
    """Store the mutable intervention lists used during a simulation run."""

    def __init__(self):
        """Initialise empty intervention lists for each intervention type."""

        self.sms_list = []
        self.field_officer_list = []
        self.reminder_card_list = []
