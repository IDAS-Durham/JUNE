import calendar
import datetime
import yaml
from typing import List

SECONDS_PER_DAY = 24 * 60 * 60


class Timer:
    def __init__(
        self,
        initial_day: str = "2020-03-01",
        total_days: int = 10,
        weekday_step_duration: List[int] = (12, 12),
        weekend_step_duration: List[int] = (24,),
        weekday_activities: List[List[str]] = (
            ("primary_activity", "residence"),
            ("residence",),
        ),
        weekend_activities: List[List[str]] = (("residence",),),
    ):

        self.initial_date = datetime.datetime(
            *[int(value) for value in initial_day.split("-")]
        )
        self.total_days = total_days
        self.weekday_step_duration = weekday_step_duration
        self.weekend_step_duration = weekend_step_duration
        self.weekday_activities = weekday_activities
        self.weekend_activities = weekend_activities

        self.previous_date = self.initial_date
        self.final_date = self.initial_date + datetime.timedelta(days=total_days)
        self.date = datetime.datetime(*[int(value) for value in initial_day.split("-")])
        self.shift = 0
        self.delta_time = datetime.timedelta(hours=self.shift_duration)

    @classmethod
    def from_file(cls, config_filename):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        time_config = config["time"]
        return cls(
            initial_day=time_config["initial_day"],
            total_days=time_config["total_days"],
            weekday_step_duration=time_config["step_duration"]["weekday"],
            weekend_step_duration=time_config["step_duration"]["weekend"],
            weekday_activities=time_config["step_activities"]["weekday"],
            weekend_activities=time_config["step_activities"]["weekend"],
        )

    @property
    def is_weekend(self):
        week_number = self.date.weekday()
        if week_number < 5:
            return False
        return True
    
    @property
    def day_type(self):
        week_number = self.date.weekday()
        if week_number < 5:
            return "weekday"
        else:
            return "weekend"

    @property
    def now(self):
        difference = self.date - self.initial_date
        return difference.total_seconds() / SECONDS_PER_DAY

    @property
    def date_str(self):
        return self.date.date().strftime("%Y-%m-%d")

    @property
    def duration(self):
        return self.delta_time.total_seconds() / SECONDS_PER_DAY

    @property
    def day(self):
        return int(self.now)

    @property
    def day_of_week(self):
        return calendar.day_name[self.date.weekday()]

    @property
    def activities(self):
        type_day = "weekend" if self.is_weekend else "weekday"
        return getattr(self, type_day + "_activities")[self.shift]

    @property
    def shift_duration(self):
        type_day = "weekend" if self.is_weekend else "weekday"
        return getattr(self, type_day + "_step_duration")[self.shift]

    def reset(self):
        self.date = self.initial_date
        self.shift = 0
        self.delta_time = datetime.timedelta(hours=self.shift_duration)
        self.previous_date = self.initial_date

    def reset_to_new_date(self, date):
        self.date = date
        self.shift = 0
        self.delta_time = datetime.timedelta(hours=self.shift_duration)
        self.previous_date = self.initial_date

    def __next__(self):
        self.previous_date = self.date
        self.date += self.delta_time
        self.shift += 1
        if self.previous_date.day != self.date.day:
            self.shift = 0
        self.delta_time = datetime.timedelta(hours=self.shift_duration)
        return self.date
