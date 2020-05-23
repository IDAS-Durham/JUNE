import calendar
import datetime

class Timer:
    def __init__(
            self, 
            initial_day:str="2020-03-10", 
            weekday_step_duration = [12,12],
            weekend_step_duration = [24],
            weekday_activities = [['primary_activity', 'residence'], ['residence']],
            weekend_activities = [['residence']],
            ):

        self.initial_date_time = datetime.datetime(*[int(value) for value in initial_day.split('-')])
        self.weekday_step_duration = weekday_step_duration 
        self.weekend_step_duration = weekend_step_duration
        self.weekday_activities = weekday_activities
        self.weekend_activities = weekend_activities

        self.previous_date = self.initial_date_time
        self.date_time = datetime.datetime(*[int(value) for value in initial_day.split('-')])
        self.shift = 0
        self.delta_time = datetime.timedelta(hours = self.shift_duration)

    @property
    def is_weekend(self):
        week_number = self.date_time.weekday()
        if week_number < 5:
            return False
        return  True

    @property
    def now(self):
        difference = (self.date_time - self.initial_date_time)
        seconds_per_day = 24*60*60
        return difference.total_seconds()/seconds_per_day
    
    @property
    def day(self):
        return int(self.now)

    @property
    def day_of_week(self):
        return calendar.day_name[self.date_time.weekday()]

    @property
    def activities(self):
        type_day = "weekend" if self.is_weekend else "weekday"
        return getattr(self, type_day + '_activities')[self.shift]

    @property
    def shift_duration(self):
        type_day = "weekend" if self.is_weekend else "weekday"
        return getattr(self, type_day + '_step_duration')[self.shift]

    def reset(self):
        self.date_time = self.initial_date_time
        self.shift = 0
        self.delta_time = datetime.timedelta(hours = self.shift_duration)

    def __iter__(self):
        return self

    def __next__(self):
        self.previous_date = self.date_time
        self.date_time += self.delta_time
        self.shift += 1
        if self.previous_date.day != self.date_time.day:
            self.shift = 0
        self.delta_time = datetime.timedelta(hours = self.shift_duration)
        return self.now


if __name__ == '__main__':
    time = Timer()
    for i in range(8):
        print(time.date_time)
        print(time.now)
        print(time.is_weekend)
        print(time.day_of_week)
        print(time.activities)
        next(time)
    
'''
class Timer:
    def __init__(self, time_config=None, initial_day="Monday"):
        if time_config is None:
            import os
            import yaml

            config_file = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                "..",
                "configs",
                "config_example.yaml",
            )
            with open(config_file, "r") as f:
                config = yaml.load(f, Loader=yaml.FullLoader)

            time_config = config["time"]

        self.time_config = time_config
        self.total_days = time_config["total_days"]
        self.day = 1
        self.day_int = 1
        self.previous_day = 0
        self.shift = 0
        self.hours = 0
        self.initial_day = initial_day
        self.weekend = self.is_weekend()
        self.duration = self.get_shifts_duration(self.weekend)
        self.duration_hours = self.get_shifts_duration(self.weekend, hours=True)

    def __iter__(self):
        return self

    def __next__(self):
        self.previous_day = self.day
        self.day += self.duration
        self.hours += self.duration_hours
        self.shift += 1
        if self.hours == 24.0:
            self.shift = 0
            self.hours = 0
            self.day_int += 1
        self.weekend = self.is_weekend()
        self.duration = self.get_shifts_duration(self.weekend)
        self.duration_hours = self.get_shifts_duration(self.weekend, hours=True)
        return self.day

    @property
    def now(self):
        return self.day

    @property
    def previous(self):
        return self.previous_day

    def get_number_shifts(self, weekend):
        self.type_day = "weekend" if weekend else "weekday"
        return len(self.time_config["step_duration"][self.type_day])

    def get_shifts_duration(self, weekend, hours=False):
        self.type_day = "weekend" if weekend else "weekday"
        if hours:
            return self.time_config["step_duration"][self.type_day][self.shift + 1]
        else:
            return (
                    self.time_config["step_duration"][self.type_day][self.shift + 1] / 24.0
            )

    def is_weekend(self):
        self.initial_day_index = list(calendar.day_name).index(self.initial_day)
        calendar_day = calendar.day_name[
            (self.day_int + self.initial_day_index - 1) % 7
            ]
        if (calendar_day == "Saturday") or (calendar_day == "Sunday"):
            return True
        else:
            return False

    def day_of_week(self):
        return calendar.day_name[(self.day_int + self.initial_day_index - 1) % 7]

    def get_time_stamp(self):
        return self.day

    def activities(self):
        active = self.time_config["step_activities"][self.type_day][self.shift + 1]
        return active

    def reset(self):
        self.day = 1
        self.day_int = 1
        self.previous_day = 0
        self.shift = 0
        self.hours = 0

'''
