from june.time import Timer


def test_initial_parameters():
    timer = Timer()
    assert timer.shift == 0
    assert timer.is_weekend() is False
    assert timer.day_of_week == 'Tuesday'

def test_time_is_passing():
    timer = Timer()
    start_time = timer.initial_date_time
    assert start_time == 0
    next(timer)  
    assert timer.now == 0.5 
    assert timer.previous_date == start_time
    next(timer)  
    assert timer.now == 1.


def test_time_reset():
    timer = Timer()
    next(timer)
    next(timer)
    next(timer)
    next(timer)
    start_time = timer.initial_date_time
    assert timer.day == 2
    timer.reset()
    assert timer.day == 0
    assert timer.shift == 0
    assert timer.previous_day == start_time


def test_weekend_transition():
    timer = Timer()
    for _ in range(0, 8):  # 5 days for 3 time steps per day
        next(timer)
    assert timer.is_weekend() is True
    assert timer.activities == ['residence']
    next(timer)
    assert timer.is_weekend() is True
    assert timer.activities == ['residence']
    next(timer)
    assert timer.is_weekend() is False
    assert timer.activities == ['primary_activity','residence']
    # a second test

