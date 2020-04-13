from collections import Iterator 
import calendar

class DayIterator():
    def __init__(self, initial_day='Monday'):
        self.day = 0
        self.initial_day = initial_day
        self.weekend = self.is_weekend()
    
    def __next__(self):
        self.day += 1
        self.weekend = self.is_weekend()
        
    def is_weekend(self):
        initial_day_index = list(calendar.day_name).index(self.initial_day)
        calendar_day = calendar.day_name[(self.day + initial_day_index)%7]
        if (calendar_day == 'Saturday') or (calendar_day == 'Sunday'):
            return True
        else:
            return False

    def get_current_day(self):
        return self.day 

    def get_time_stamp(self):

        return self.day

class DayShiftIterator():
    def __init__(self, day_iterator, time_config=None):
        self.day_iterator = day_iterator
        self.shift = 1
        self.time_config = time_config
        if self.time_config:
            if self.day_iterator.weekend:
                self.type_day = 'weekend'
            else:
                self.type_day = 'weekday'
            self.n_shifts  = self.get_n_shifts(self.type_day)
            self.duration = self.get_shifts_duration(self.type_day)
        else:
            self.n_shifts = 1
            self.duration = 24 

    def __next__(self):
        self.shift += 1
        self.shift_duration = self.get_shifts_duration(self.type_day)
        self.duration += self.shift_duration

    def get_n_shifts(self, type_day):
        return len(self.time_config['step_duration'][type_day].keys())

    def get_shifts_duration(self, type_day):
        return self.time_config['step_duration'][type_day][self.shift]/24.

    def get_time_stamp(self):

        return self.day_iterator.day + self.duration


    def get_time_ellapsed(self, time_stamp):

        current_time_stamp = self.get_time_stamp()
        return current_time_stamp - time_stamp 



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

        
    day_iterator = DayIterator()
    n_days =10 
    n_shifts = 3
    for i in range(n_days):
        print('Is weekend ? ', day_iterator.weekend)
        shift_iterator = DayShiftIterator(day_iterator, config['time'])
        first_time_stamp = shift_iterator.get_time_stamp()
        print(first_time_stamp)
        for j in range(shift_iterator.n_shifts-1):
            next(shift_iterator)
        
        print(shift_iterator.get_time_stamp())
        print(shift_iterator.get_time_ellapsed(first_time_stamp))
        next(day_iterator)

    

