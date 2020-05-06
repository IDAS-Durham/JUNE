from covid.groups.people import demography as d


def test_create_demography():
    demography = d.Demography.from_super_area(
        "NorthEast"
    )
    assert demography.super_area == "NorthEast"
