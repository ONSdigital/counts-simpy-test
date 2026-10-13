#class to hold the various intervention lists
class intervention_lists:
    #define the empty lists 
    def __init__(self):
        self.sms_list = []
        self.field_officer_list = []
        self.postcard_list = []

    #add households to the relevant lists
    def add_sms(self, household):
        self.sms_list.append(household)

    def add_field_officer(self, household):
        self.field_officer_list.append(household)

    def add_postcard(self, household):
        self.postcard_list.append(household)

    #update the sms list to remove households that have already responded
    def update_sms(self):
        self.sms_list = [household for household in self.sms_list if not household.responded]