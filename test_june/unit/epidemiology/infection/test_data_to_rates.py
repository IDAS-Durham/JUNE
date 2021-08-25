from june import paths
from june.epidemiology.infection.health_index.data_to_rates import (
    read_comorbidity_csv,
    convert_comorbidities_prevalence_to_dict,
)
import pytest


def test__parse_comorbidity_prevalence():
    male_filename = paths.data_path / "input/demography/uk_male_comorbidities.csv"
    female_filename = paths.data_path / "input/demography/uk_female_comorbidities.csv"
    prevalence_female = read_comorbidity_csv(female_filename)
    prevalence_male = read_comorbidity_csv(male_filename)
    for value in prevalence_female.sum(axis=1):
        assert value == pytest.approx(1.0)
    for value in prevalence_male.sum(axis=1):
        assert value == pytest.approx(1.0)

    prevalence_dict = convert_comorbidities_prevalence_to_dict(
        prevalence_female, prevalence_male
    )
    assert prevalence_dict["sickle_cell"]["m"]["0-4"] == pytest.approx(
        3.92152e-05, rel=0.2
    )
    assert prevalence_dict["tuberculosis"]["f"]["4-9"] == pytest.approx(
        5.99818e-05, rel=0.2
    )
    assert prevalence_dict["tuberculosis"]["f"]["4-9"] == pytest.approx(
        5.99818e-05, rel=0.2
    )
