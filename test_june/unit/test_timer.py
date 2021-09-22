from june.time import Timer


def test_initial_parameters():
    timer = Timer(initial_day="2020-03-10", total_days=10)
    assert timer.shift == 0
    assert timer.is_weekend is False
    assert timer.day_of_week == "Tuesday"
    assert timer.date_str == "2020-03-10"


def test_time_is_passing():
    timer = Timer(initial_day="2020-03-10", total_days=10)
    assert timer.now == 0
    next(timer)
    assert timer.now == 0.5
    assert timer.previous_date == timer.initial_date
    next(timer)
    assert timer.now == 1.0


def test_time_reset():
    timer = Timer(initial_day="2020-03-10", total_days=10)
    start_time = timer.initial_date
    assert timer.date_str == "2020-03-10"
    next(timer)
    next(timer)
    assert timer.date_str == "2020-03-11"
    next(timer)
    next(timer)
    assert timer.day == 2
    assert timer.date_str == "2020-03-12"
    timer.reset()
    assert timer.day == 0
    assert timer.shift == 0
    assert timer.previous_date == start_time
    assert timer.date_str == "2020-03-10"
    next(timer)
    next(timer)
    next(timer)
    next(timer)
    assert timer.day == 2


def test_weekend_transition():
    timer = Timer(initial_day="2020-03-10", total_days=10)
    for _ in range(0, 8):  # 5 days for 3 time steps per day
        next(timer)
    assert timer.is_weekend is True
    assert timer.activities == ("residence",)
    next(timer)
    assert timer.is_weekend is True
    assert timer.activities == ("residence",)
    next(timer)
    assert timer.is_weekend is False
    assert timer.activities == ("primary_activity", "residence",)
    # a second test
