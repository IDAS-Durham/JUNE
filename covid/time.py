from collections import Iterator 
import calendar

class DayIterator():
    def __init__(self, initial_day='Friday'):
        self.day = 0
        self.initial_day = initial_day
        self.weekend = self.is_weekend()
    
    def __next__(self):
        self.day += 1
        self.weekend = self.is_weekend()
        
    def is_weekend(self):
        initial_day_index = list(calendar.day_name).index(self.initial_day)
        calendar_day = calendar.day_name[(self.day + initial_day_index - 1)%7]
        if (calendar_day == 'Saturday') or (calendar_day == 'Sunday'):
            return True
        else:
            return False

    def get_current_day(self):
        return self.day 

    def get_time_stamp(self):

        return f'{self.day}D '

    def time_stamp2hours(self, time_stamp):
        return int(time_stamp.split(' ')[0].strip('D'))*24

class DayShiftIterator():
    def __init__(self, day_iterator, time_config=None):
        self.day_iterator = day_iterator
        self.shift = 0
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
        self.duration += self.get_shifts_duration(self.type_day)

    def get_n_shifts(self, type_day):
        return len(self.time_config['step_duration'][type_day].keys())

    def get_shifts_duration(self, type_day):
        return self.time_config['step_duration'][type_day][self.shift+1]

    def get_time_stamp(self):

        return f'{self.day_iterator.day}D {self.duration}H'

    def time_stamp2hours(self, time_stamp):
        hours = self.day_iterator.time_stamp2hours(time_stamp)
        hours += int(time_stamp.split(' ')[1].strip('H'))
        return hours


    def get_time_ellapsed(self, time_stamp):

        current_time_stamp = self.get_time_stamp()
        current_hours = self.time_stamp2hours(current_time_stamp)
        time_stamp_hours = self.time_stamp2hours(time_stamp)

        return current_hours - time_stamp_hours



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

    

