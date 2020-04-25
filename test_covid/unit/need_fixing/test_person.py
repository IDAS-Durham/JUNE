import pytest

from covid.groups import Person


def test_insanity():
    Person(
        age=10,
        sex="F"
    )
    with pytest.raises(
            AssertionError
    ):
        Person(
            age=-1,
            sex="F"
        )
    with pytest.raises(
            AssertionError
    ):
        Person(
            age=10,
            sex="G"
        )
