import pandas as pd

from june import paths

default_seroprevalence_file = paths.data_path / 'input/health_index/seroprevalence_by_age_imperial.csv'

def convert_to_intervals(age: str)->pd.Interval:
    return pd.Interval(left=int(age.split('-')[0]),
        right=int(age.split('-')[1]),
        closed='both'
    )


class Data2Rates():

    def __init__(self, seroprevalence_df: pd.DataFrame):
        self.seroprevalence_df = seroprevalence_df


    @classmethod
    def from_files(cls,
            seroprevalence_file:str = default_seroprevalence_file)->'Data2Rates':

        seroprevalence_df = pd.read_csv(default_seroprevalence_file,
                converters={'age': convert_to_intervals}
        )
        seroprevalence_df.set_index('age', inplace=True)
        return cls(seroprevalence_df=seroprevalence_df)
    

if __name__=='__main__':
    rates = Data2Rates.from_files()
    print(rates.seroprevalence_df)
