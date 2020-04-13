import calendar

class DayIterator():
    def __init__(self, time_config, initial_day='Friday'):
        self.day = 1
        self.previous_day = 0
        self.shift = 0
        self.initial_day = initial_day
        self.weekend = self.is_weekend()
        self.time_config =time_config
        self.duration = self.get_shifts_duration(self.weekend)
        self.total_days = time_config['total_days']
    
    def __next__(self):
        self.previous_day = self.day
        self.day += self.duration
        self.shift += 1
        if int(self.day) == self.day:
            self.shift = 0
        self.weekend = self.is_weekend()
        self.duration = self.get_shifts_duration(self.weekend)
   
    def get_shifts_duration(self, weekend):
        self.type_day = 'weekend' if weekend else 'weekday'
        return self.time_config['step_duration'][self.type_day][self.shift+1]/24.

    def is_weekend(self):
        self.initial_day_index = list(calendar.day_name).index(self.initial_day)
        calendar_day = calendar.day_name[(int(self.day) + self.initial_day_index - 1)%7]
        if (calendar_day == 'Saturday') or (calendar_day == 'Sunday'):
            return True
        else:
            return False

    def day_of_week(self):
        return calendar.day_name[(int(self.day) + self.initial_day_index - 1)%7]

    def get_time_stamp(self):
        return self.day

    def active_groups(self):
        # households are always active
        always_active = ["households"]
        active = self.time_config["step_active_groups"][self.type_day][self.shift+1]
        return active + always_active 



if __name__ == '__main__':

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

    day_iter = DayIterator(config['time'])

    while day_iter.day <= day_iter.total_days:

        print('Current time : ', day_iter.get_time_stamp())
        print('Previous time : ', day_iter.previous_day)
        print('Day of the week ', day_iter.day_of_week())
        print('Active groups : ', day_iter.active_groups())
        
        next(day_iter)
