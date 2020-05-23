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

        self.initial_date = datetime.datetime(*[int(value) for value in initial_day.split('-')])
        self.weekday_step_duration = weekday_step_duration 
        self.weekend_step_duration = weekend_step_duration
        self.weekday_activities = weekday_activities
        self.weekend_activities = weekend_activities

        self.previous_date = self.initial_date
        self.date = datetime.datetime(*[int(value) for value in initial_day.split('-')])
        self.shift = 0
        self.delta_time = datetime.timedelta(hours = self.shift_duration)

    @property
    def is_weekend(self):
        week_number = self.date.weekday()
        if week_number < 5:
            return False
        return  True

    @property
    def now(self):
        difference = (self.date - self.initial_date)
        seconds_per_day = 24*60*60
        return difference.total_seconds()/seconds_per_day
    
    @property
    def day(self):
        return int(self.now)

    @property
    def day_of_week(self):
        return calendar.day_name[self.date.weekday()]

    @property
    def activities(self):
        type_day = "weekend" if self.is_weekend else "weekday"
        return getattr(self, type_day + '_activities')[self.shift]

    @property
    def shift_duration(self):
        type_day = "weekend" if self.is_weekend else "weekday"
        return getattr(self, type_day + '_step_duration')[self.shift]

    def reset(self):
        self.date = self.initial_date
        self.shift = 0
        self.delta_time = datetime.timedelta(hours = self.shift_duration)
        self.previous_date = self.initial_date

    def __iter__(self):
        return self

    def __next__(self):
        self.previous_date = self.date
        self.date += self.delta_time
        self.shift += 1
        if self.previous_date.day != self.date.day:
            self.shift = 0
        self.delta_time = datetime.timedelta(hours = self.shift_duration)
        return self.now


if __name__ == '__main__':
    time = Timer()
    for i in range(8):
        print(time.date)
        print(time.now)
        print(time.is_weekend)
        print(time.day_of_week)
        print(time.activities)
        next(time)
    

