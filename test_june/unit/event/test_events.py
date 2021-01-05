import datetime
from june.event import Event, Events


def test__event_dates():
    event = Event(start_time="2020-01-05", end_time="2020-12-05")
    assert event.start_time.strftime("%Y-%m-%d") == "2020-01-05"
    assert event.end_time.strftime("%Y-%m-%d") == "2020-12-05"
    assert event.is_active(datetime.datetime.strptime("2020-03-05", "%Y-%m-%d"))
    assert not event.is_active(datetime.datetime.strptime("2030-03-05", "%Y-%m-%d"))


