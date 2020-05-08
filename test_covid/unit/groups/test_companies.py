from covid.groups import Company, Companies
from covid.groups import Person
from pathlib import Path
import pandas as pd

data_path = (
    Path(__file__).parent.parent.parent.parent
    / "data/processed/census_data/company_data"
)


def test__add_person_to_company():
    company = Company()
    person = Person()
    company.add(person)
    person2 = company.people.pop()
    assert person2 == person
    assert person2.company == company


def test__create_company_from_file():
    company_size_df = pd.read_csv(data_path / "companysize_msoa11cd_2019.csv")
    company_size_df.set_index("MSOA", inplace=True)
    company_sector_df = pd.read_csv(data_path / "companysector_msoa11cd_2011.csv")
    company_sector_df.set_index("MSOA", inplace=True)
    company_size_df = company_size_df.div(company_size_df.sum(axis=1), axis=0)

    comp_sector_part = company_sector_df.loc[['E02002559']]
    comp_size_part = company_size_df.loc[['E02002559']]
    companies = Companies.from_df(comp_size_part, comp_sector_part)
    assert len(companies.members) == 610

    comp_sector_part = company_sector_df.loc[['E02002559', 'E02002560']]
    comp_size_part = company_size_df.loc[['E02002559', 'E02002560']]
    companies = Companies.from_df(comp_size_part, comp_sector_part)
    assert len(companies.members) == 750
