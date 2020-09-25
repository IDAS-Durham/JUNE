import numpy as np
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

default_policy_file = '../configs/defaults/policy/policy.yaml'

default_gov_attendance = '../custom_data/data-attendance-in-education-and-early-years-settings-during-the-coronavirus-covid-19-outbreak.csv'

class PolicyPlots:

    def __init__(self, world):
        self.world = world

    def plot_school_repopening(
            self,
            policy_file = default_policy_file,
            gov_attendance = default_gov_attendance,
    ):

        children = []
        for person in world.people:
            try:
                if person.primary_activity.group.spec == 'school' and person.age < 19:
                    children.append(person)
            except AttributeError:
                pass

        policies = Policies.from_file(policy_file)

        activities = ["primary_activity", "residence"]

        no_days = 200
        begin_date = datetime(2020,3,1)

        dates = []
        children_in_school = []

        for i in range(no_days):
            date = begin_date + timedelta(i)
            dates.append(date)
            active_individual_policies = policies.individual_policies.get_active(
                    date=date
                )
            in_school = 0
            for child in children:
                activities_left = policies.individual_policies.apply(
                                    active_individual_policies,
                                    person=child,
                                    activities=activities,
                                    days_from_start=0,
                                  )
                if "primary_activity" in activities_left:
                    in_school += 1
            children_in_school.append(in_school)

        children_in_school = np.array(children_in_school)
        per_in_school = children_in_school*100/len(children)

        dfe_attendance = pd.read_csv(default_gov_attendance)

        dfe_dates = []
        for date in dfe_attendance['date']:
            dfe_dates.append(datetime.strptime(date, '%d/%m/%Y').date())

        tot_child = 1517000/0.159

        dfe_per = []
        for attendance in dfe_attendance['children_attending']:
            dfe_per.append(attendance/tot_child)

        dfe_per = np.array(dfe_per)
        dfe_per *= 100

        plt.plot(dates, per_in_school, label='DfE statistics')
        plt.plot(dfe_dates, dfe_per, label='JUNE')
        plt.vlines(datetime(2020,6,1),1,19,linestyle='--',color='green', label='Early years +\nY6 opening')
        plt.vlines(datetime(2020,6,15),1,19,linestyle='--',color='orange', label='Y10+Y12\noffered support')
        plt.vlines(datetime(2020,7,16),1,19,linestyle='--',color='red', label='Summer holidays')
        plt.xticks(rotation=45)
        plt.ylim((0,20))
        plt.xlim((datetime(2020,4,1),datetime(2020,7,25)))
        plt.ylabel('% pupils attending')
        plt.xlabel('Date')
        plt.legend(loc='upper left')
