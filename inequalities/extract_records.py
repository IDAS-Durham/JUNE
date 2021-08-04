import numpy as np
import time
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import argparse

from june.records import Record, RecordReader

def parse():
    """
    Parse arguments
    """

    parser = argparse.ArgumentParser(description=
                                     """
                                     Extracting data from records for assessing the population and disease data
                                     """
    )

    parser.add_argument(
        "--record_path",
        dest = "record_path"
        help = "path to record"
    )

    parser.add_argument(
        "--save_path",
        dest = "save_path"
        help = "path to save extracted data"
        default = None
    )

    args = parser.parse_args()

    return args

class Extract:

    def __init__(self, record_path, save_path = None):
        self.record_path = record_path
        self.save_path = save_path

        if self.save_path is None:
            self.save_path = self.record_path

        self.read = RecordReader(self.record_path)

    def extract_infections(self):

        infections_df = read.get_table_with_extras(
            'infections',
            'infected_ids'
        )

        infections_df.to_csv(save_path + "/infections.csv")

    def extract_deaths(self):

        deaths_df = read.get_table_with_extras(
            'deaths', 
            'dead_person_ids'
        )

        deaths_df.to_csv(self.save_path + "/deaths.csv")

    def extract_people(self):

        people_df = read.table_to_df('population')

        people_df.to_csv(self.save_path + "/people.csv")

    def extract(self):

        self.extract_infections()
        self.extract_deaths()
        self.extract_people()

    

if __name__ == "__main__":

    args = parse()

    extractor = Extract(args.record_path, args.save_path)
    extractor.extract
