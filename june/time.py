import calendar


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


if __name__ == "__main__":

    import yaml
    import os

    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "configs",
        "config_example.yaml",
    )
    with open(config_file, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    day_iter = Timer(config["time"])

    while day_iter.day <= day_iter.total_days:

        # print('Previous time : ', day_iter.previous)
        print("Day of the week ", day_iter.day_of_week())
        print("Current time : ", day_iter.now)
        print("Active groups : ", day_iter.activities())

        print("**********************************")
        next(day_iter)
