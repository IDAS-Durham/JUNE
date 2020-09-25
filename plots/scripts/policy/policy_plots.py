import numpy as np
import time
from datetime import datetime, timedelta
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

default_policy_filename = '../configs/defaults/policy/policy.yaml'

default_attendance_filename = 'YoY_Seated_Diner_Data.csv'

default_gov_filename = '../custom_data/data-attendance-in-education-and-early-years-settings-during-the-coronavirus-covid-19-outbreak.csv'

class PolicyPlots:

    def __init__(self, world):
        self.world = world

    def plot_restaurant_reopening(
            self,
            attendance_filename = default_attendance_filename,
    ):
        data_file = pd.read_csv(attendance_filename)
        uk_data = data_file[data_file['Name'] == 'United Kingdom']

        dates = []
        change = []
        for column in uk_data.columns[2:]:
            date_year = column + '/20'
            dates.append(datetime.strptime(date_year, '%m/%d/%y').date())
            change.append(float(uk_data[column]))
            
        def f(x, A, B):
            return A*x + B

        popt, pcov = curve_fit(f, np.arange(len(change[137:196])), change[137:196])

        fit_change = list(f(np.arange(len(change[137:196])), popt[0], popt[1]))
        for zero in np.zeros(len(dates[197:])):
            fit_change.append(zero)

        f, ax = plt.subplots()
        ax.plot(dates, change)
        ax.plot(dates[137:-1], fit_change, label='Simualted change', color='maroon')
        ax.vlines(datetime(2020,3,16).date(),-110,230, linestyles='--', color='orange', label = '16th March')
        ax.vlines(datetime(2020,3,23).date(),-110,230, linestyles='--', color='red', label = '23rd March')
        ax.vlines(datetime(2020,7,4).date(),-110,230, linestyles='--',  color='green', label = '4th July')
        ax.hlines(0, dates[0], dates[-1], linestyles='--')
        ax.legend(bbox_to_anchor=(1.05, 1))
        ax.title('Year on year restaurant attendance (OpenTable)')
        ax.ylabel('% difference')
        ax.xlabel('Date')

        return ax
            
    def plot_school_repopening(
            self,
            policy_filename = default_policy_filename,
            gov_filename = default_gov_filename,
    ):

        children = []
        for person in world.people:
            try:
                if person.primary_activity.group.spec == 'school' and person.age < 19:
                    children.append(person)
            except AttributeError:
                pass

        policies = Policies.from_file(policy_filename)

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

        f, ax = plt.subplots()
        ax.plot(dates, per_in_school, label='DfE statistics')
        ax.plot(dfe_dates, dfe_per, label='JUNE')
        ax.vlines(datetime(2020,6,1),1,19,linestyle='--',color='green', label='Early years +\nY6 opening')
        ax.vlines(datetime(2020,6,15),1,19,linestyle='--',color='orange', label='Y10+Y12\noffered support')
        ax.vlines(datetime(2020,7,16),1,19,linestyle='--',color='red', label='Summer holidays')
        ax.xticks(rotation=45)
        ax.ylim((0,20))
        ax.xlim((datetime(2020,4,1),datetime(2020,7,25)))
        ax.ylabel('% pupils attending')
        ax.xlabel('Date')
        ax.legend(loc='upper left')

        return ax
