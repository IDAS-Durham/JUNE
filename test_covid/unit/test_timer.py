from covid.time import Timer

timer_config = {
    "total_days": 50,
    "step_duration": {"weekday": {1: 8, 2: 6, 3: 10}, "weekend": {1: 24}},
    "step_active_groups": {
        "weekday": {
            1: ["households"],
            2: ["companies", "households"],
            3: ["schools", "companies"],
        },
        "weekend": {1: ["households"],},
    },
}


def test_initial_parameters():
    timer = Timer(timer_config)
    assert timer.total_days == 50
    assert timer.day == 1
    assert timer.day_int == 1
    assert timer.shift == 0
    assert timer.hours == 0
    assert timer.is_weekend() is False
    assert timer.initial_day == "Monday"


def test_time_is_passing():
    timer = Timer(timer_config)
    start_time = timer.now
    assert start_time == 1
    next(timer)  # should be 1.33333
    assert timer.hours == 8
    assert timer.previous == start_time
    next(timer)  # 1.666
    assert timer.hours == 8 + 6
    next(timer)  # 2.0
    assert timer.now == 2
    assert timer.hours == 0


def test_time_reset():
    timer = Timer(timer_config)
    next(timer)
    next(timer)
    next(timer)
    assert timer.day == 2
    timer.reset()
    assert timer.day == 1
    assert timer.day_int == 1
    assert timer.hours == 0
    assert timer.shift == 0
    assert timer.previous_day == 0


def test_weekend_transition():
    timer = Timer(timer_config)
    for _ in range(0, 15):  # 5 days for 3 time steps per day
        next(timer)
    assert timer.is_weekend() is True
    next(timer)
    assert timer.is_weekend() is True
    next(timer)
    assert timer.is_weekend() is False
    # a second test
    timer = Timer(timer_config, initial_day="Friday")
    assert timer.is_weekend() is False
    for _ in range(0, 3):
        next(timer)
    assert timer.is_weekend() is True

