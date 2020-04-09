from collections import Iterator 
import calendar

class DayIterator():
    def __init__(self, initial_day='Saturday'):
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

        return f'{self.day_iterator.day}D'


class DayShiftIterator():
    def __init__(self, day_iterator, time_config=None):
        self.day_iterator = day_iterator
        self.shift = 0
        if time_config:
            if day_iterator.weekend:
                self.duration = time_config['weekend']
            else:
                self.duration = time_config['weekday']
        else:
            self.duration = 0

    def __next__(self):
        self.shift += 1

    def get_time_stamp(self):

        return f'{self.day_iterator.day}D {self.shift}S'

if __name__ == '__main__':
        
    day_iterator = DayIterator()
    n_days = 7
    n_shifts = 3
    for i in range(n_days):
        print('Is weekend ? ', day_iterator.weekend)
        next(day_iterator)
        shift_iterator = DayShiftIterator(day_iterator)
        for j in range(n_shifts):
            print(shift_iterator.get_time_stamp())
            next(shift_iterator)


    

