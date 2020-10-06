import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import argparse

import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import matplotlib.ticker as mtick
import matplotlib.dates as mdates

from june import paths

# paths for real world hospital admissions and deaths
default_admissions_data_file = (
    paths.data_path / "covid_real_data/adjusted-admissions-mean.csv"
)

default_deaths_data_file = (
    paths.data_path / "covid_real_data/regional_deaths_sitrep_strat.csv"
)

plt.style.use(['science'])
plt.style.reload_library()

class ResultsPlots():
    """
    Class for plotting JUNE results

    Parameters
    ----------
    csv_dir (str): Directory containing JUNE output csv files
            world_summary_xxx.csv
            regional_summary_xxx.csv
            age_summary_xxx.csv
    run_no (int): number of the run to plot as integer, i.e. run 005 would be run_no=5
    """

    def __init__(self, csv_dir, run_no):       
        self.csv_dir = csv_dir
        self.run_no = run_no


    def load_sitrep_data(
            self,
            admissions_data_file = default_admissions_data_file,
            deaths_data_file = default_deaths_data_file
        ):
        "Load real world data and process to a more friendly format for plotting."

        # load csvs
        admissions_data = pd.read_csv(default_admissions_data_file, index_col='Unnamed: 0')
        admissions_data.replace({'Admissions_85+': 'Admissions_85-99'}, inplace=True)
        admissions_regions = admissions_data['Region'].unique()
        admissions_bands = admissions_data['Band'].unique()

        deaths_data = pd.read_csv(default_deaths_data_file)
        deaths_data.rename(columns={'85+': '85-99'}, inplace=True)
        deaths_data = deaths_data.melt(id_vars=['region_name', 'date_of_death'], var_name='Band', value_name='Deaths')
        deaths_regions = deaths_data['region_name'].unique()
        deaths_bands = deaths_data['Band'].unique()

        # make data more easily plottable
        admissions_df = {}
        for band in admissions_bands:
            dfs = {}
            for region in admissions_regions:
                tmp_df = admissions_data[(admissions_data['Band']==band) & (admissions_data['Region']==region)].filter(items=['Date', 'Admissions'])
                tmp_df.index = pd.to_datetime(tmp_df['Date'])
                tmp_df.drop(columns=['Date'], inplace=True)
                # rename regions to match JUNE output
                if region == 'East Of England':
                    region = region.replace('Of', 'of')
                elif region == 'North East And Yorkshire':
                    region = region.replace('And', 'and')
                dfs[region] = tmp_df
            dfs['England'] = pd.concat({key: val for key, val in dfs.items()}).sum(level=1).sort_index()
            admissions_df[band] = pd.concat({key: val for key, val in sorted(dfs.items())})
        admissions_df = pd.concat({key: val for key, val in admissions_df.items()})

        deaths_df = {}
        for band in deaths_bands:
            dfs = {}
            for region in deaths_regions:
                tmp_df = deaths_data[(deaths_data['Band']==band) & (deaths_data['region_name']==region)].filter(items=('date_of_death', 'Deaths'))
                tmp_df.index = pd.to_datetime(tmp_df['date_of_death'])
                tmp_df.drop(columns=['date_of_death'], inplace=True)
                # rename regions to match JUNE output
                if region == 'East Of England':
                    region = region.replace('Of', 'of')
                dfs[region] = tmp_df
            dfs['England'] = pd.concat({key: val for key, val in dfs.items()}).sum(level=1).sort_index()
            deaths_df[band] = pd.concat({key: val for key, val in sorted(dfs.items())})
        deaths_df['All ages'] = pd.concat({key: val for key, val in deaths_df.items()}).sum(level=[1,2]).sort_index()
        deaths_df = pd.concat({key: val for key, val in deaths_df.items()})

        self.admissions_data_df = admissions_df
        self.deaths_data_df = deaths_df

        return None


    def load_csv_files(self):
        "Load JUNE output csv files into Pandas DataFrames."

        world_df = pd.read_csv(self.csv_dir + f'/world_summary_{self.run_no:03}.csv')
        # I think the Beyonce summary files are named weirdly since this regional summary is not daily...
        # will probably have to be careful about this for future plots
        regional_df = pd.read_csv(self.csv_dir + f'/daily_regional_summary_{self.run_no:03}.csv')
        age_df = pd.read_csv(self.csv_dir + f'/age_summary_{self.run_no:03}.csv')
        
        world_df = self.process_world_df(world_df)
        region_dfs = self.process_regional_df(regional_df)
        age_dfs = self.process_age_df(age_df)

        self.world_df = world_df
        self.region_dfs = region_dfs
        self.age_dfs = age_dfs

        return None
        

    def process_world_df(self, df):
        "Process raw world dataframe into daily summary."
        df.set_index('time_stamp', inplace=True)
        df.index = pd.to_datetime(df.index)
        return self.convert_to_daily_summary(df)


    def process_age_df(self, df):
        "Process raw age dataframe into daily summary by age groups."

        df.set_index('time_stamp', inplace=True)
        df.index = pd.to_datetime(df.index)
        age_dfs = []
        for age, group in df.groupby('age_range'):
            age_df = group
            age_df.insert(0, 'age', int(age.split('_')[0]))
            age_dfs.append(age_df)
        age_df = pd.concat(age_dfs)
        # SITREP/NHS age bins
        age_range = [0, 6, 18, 65, 85, 100]
        labels = ['_'.join((str(age_range[i]), str(age_range[i+1]-1))) for i in range(len(age_range)-1)]
        
        # assign age ranges
        age_df['age_range'] = pd.cut(age_df.age, bins=age_range,
                                    labels=labels, include_lowest=True, right=False)
        
        # make new dataframe for age ranges
        age_dfs = {}
        for age_range, group in age_df.groupby('age_range'):
            age_df = group.drop(columns=['age', 'age_range'])
            age_df = age_df.groupby('time_stamp').sum()
            age_dfs[age_range] = self.convert_to_daily_summary(age_df)
        return pd.concat({age_range: df for age_range, df in sorted(age_dfs.items())},
                          names=['age_range', 'time_stamp'])
        

    def process_regional_df(self, df):
        "Process raw regional dataframe into daily summary by region."

        region_dfs = {}
        # group regions together to match data
        df = self.group_regions(df, 'East Midlands', 'West Midlands', 'Midlands')
        df = self.group_regions(df, 'North East', 'Yorkshire and The Humber', 'North East and Yorkshire')
        for region, group in df.groupby('region'):
            region_df = group
            region_df.set_index('time_stamp', inplace=True)
            region_df.drop(columns=['region'], axis=1, inplace=True)
            region_df.index = pd.to_datetime(region_df.index)
            region_dfs[region] = self.convert_to_daily_summary(region_df)
        # return dataframe with daily regional data
        return pd.concat({region: df for region, df in region_dfs.items()},
                          names=['region', 'time_stamp'])


    def group_regions(self, df, region1, region2, grouped_name):
        "Group two regions into one region."

        df1 = df[df['region'] == region1]
        df2 = df[df['region'] == region2]
        df1.set_index('time_stamp', inplace=True)
        df2.set_index('time_stamp', inplace=True)
        df1.index = pd.to_datetime(df1.index)
        df2.index = pd.to_datetime(df2.index)
        
        grouped_df = df1 + df2
        grouped_df['region'] = grouped_name
        df = pd.concat([df, grouped_df.reset_index()])
        df = df.reset_index()
        
        df.drop(df[df['region'] == region1].index, inplace=True)
        df.drop(df[df['region'] == region2].index, inplace=True)
        return df


    def convert_to_daily_summary(self, df):
        "Converts dataframes into a daily summary."

        # columns to sum to get total population of a given group
        total_pop_cols = ['current_infected',
                          'current_recovered',
                          'current_dead',
                          'current_susceptible']

        # calculate population of a given group
        world_pop = df[total_pop_cols].iloc[0].sum()

        df['seroprevalence'] = 100.*df['daily_infections'].cumsum() / world_pop

        # filter out columns depending on daily or not
        daily_df = df.filter(regex="daily_*").resample('D').sum()
        current_df = df.filter(regex="current_*").resample('D').last()
        daily_df = pd.concat([current_df, daily_df], axis=1)

        daily_df['seroprevalence'] = (
            100.*daily_df['daily_infections'].cumsum() / world_pop
        )
        return daily_df


    def get_start_end_date(self):
        "Get start and end date for plotting, depending on where real data is up to."
        self.start_date = self.world_df.index[0]
        self.end_date = min(max(self.admissions_data_df.index.get_level_values(2)),
                        max(self.deaths_data_df.index.get_level_values(2)))


    def format_axes(self, ax):
        "Format axes in a consistent way"
        for axes in ax.ravel():
            # soft lockdown
            axes.axvline(datetime(2020, 3, 16, 0, 0), linestyle='--', color='C2', label='16th March\nSoft Lockdown')
            # hard lockdown
            axes.axvline(datetime(2020, 3, 23, 0, 0), linestyle='--', color='C3', label='23rd March\nHard Lockdown')
            # leisure reopen
            axes.axvline(datetime(2020, 7, 4, 0, 0), linestyle='--', color='C1', label='4th July\nLeisure re-open')
            # set major ticks on month
            axes.xaxis.set_major_locator(mdates.MonthLocator())
            # set minor ticks half way through month
            axes.xaxis.set_minor_locator(mdates.MonthLocator(bymonthday=15))
            # rotate ticks by 45 degrees
            for tick in axes.get_xticklabels():
                tick.set_rotation(45)


    def plot_england_results(self):
        "Plot England summary plots."
        fig, ax = plt.subplots(2, 2, figsize=(8, 6))
        fig.suptitle(f'England summary plots (run {self.run_no:03})')
        ax[0, 0].plot(self.world_df['daily_infections'][self.start_date:self.end_date],
                      label='JUNE')

        ax[0, 1].plot(self.world_df['daily_hospital_admissions'][self.start_date:self.end_date],
                      label='JUNE')
        ax[0, 1].plot(self.admissions_data_df.loc['Admissions_Total', 'England'][self.start_date:self.end_date],
                      label='Data', color='k')

        ax[1, 0].plot(self.world_df['daily_icu_admissions'][self.start_date:self.end_date],
                      label='JUNE')

        ax[1, 1].plot(self.world_df[['daily_deaths_hospital', 'daily_deaths_icu']].sum(axis=1)[self.start_date:self.end_date],
                      label='JUNE')
        ax[1, 1].plot(self.deaths_data_df.loc['All ages', 'England'][self.start_date:self.end_date],
                      label='Data', color='k')

        ax[0, 0].set_ylabel('Daily infections')
        ax[0, 1].set_ylabel('Daily hospital admissions')
        ax[1, 0].set_ylabel('Daily ICU admissions')
        ax[1, 1].set_ylabel('Daily hospital deaths')
        self.format_axes(ax)
        plt.tight_layout()

        # move legend outside of subplots
        box = ax.ravel()[-1].get_position()
        ax.ravel()[-1].set_position([box.x0, box.y0 + box.height * 0.1,
                    box.width, box.height * 0.9])
        ax.ravel()[-1].legend(loc='upper center', bbox_to_anchor=(-0.15, -0.3),
                              fancybox=True, shadow=True, ncol=5, fontsize=11)
        plt.subplots_adjust(top=0.9, bottom=0.2)

        return fig
    

    def plot_age_stratified_results(self):
        "Plot SITREP age stratified summary plots."
        age_ranges = sorted(self.age_dfs.index.get_level_values(0).unique(), key=lambda x: int(x.split('_')[0]))

        fig, ax = plt.subplots(5, 2, figsize=(8, 12))
        fig.suptitle(f'SITREP Age stratified summary (run {self.run_no:03})')
        for i, age_range in enumerate(age_ranges):
            ax[i, 0].plot(self.age_dfs.loc[age_range]['daily_hospital_admissions'][self.start_date:self.end_date],
                          label='JUNE')
            ax[i, 0].plot(self.admissions_data_df.loc['Admissions_' + age_range.replace('_', '-'), 'England'][self.start_date:self.end_date],
                          label='Data', color='k')
            ax[i, 1].plot(self.age_dfs.loc[age_range][['daily_deaths_hospital', 'daily_deaths_icu']].sum(axis=1)[self.start_date:self.end_date],
                          label='JUNE')
            ax[i, 1].plot(self.deaths_data_df.loc[age_range.replace('_', '-'), 'England'][self.start_date:self.end_date],
                          label='Data', color='k')
            
            # put age labels on right hand side of subplots
            ax[i, 1].text(1.05, 0.5, age_range.replace('_', '-'), transform=ax[i, 1].transAxes,
                        verticalalignment='center', fontsize=14)
            ax[i, 0].set_ylabel('Daily hospital\nadmissions')
            ax[i, 1].set_ylabel('Daily hospital deaths')
        self.format_axes(ax)
        plt.tight_layout()

        # move legend outside of subplots
        box = ax.ravel()[-1].get_position()
        ax.ravel()[-1].set_position([box.x0, box.y0 + box.height * 0.1,
                    box.width, box.height * 0.9])
        ax.ravel()[-1].legend(loc='upper center', bbox_to_anchor=(-0.15, -0.3),
            fancybox=True, shadow=True, ncol=5, fontsize=11)
        plt.subplots_adjust(top=0.95, bottom=0.1)

        return fig


    def plot_regional_hospital_admissions(self):
        fig = plt.figure(figsize=(12, 6))
        fig.suptitle(f'Regional hospital admissions (run {self.run_no:03})')

        # make subplots for different regions... awkward because odd number
        ax1 = plt.subplot2grid(shape=(2,8), loc=(0,0), colspan=2)
        ax2 = plt.subplot2grid((2,8), (0,2), colspan=2)
        ax3 = plt.subplot2grid((2,8), (0,4), colspan=2)
        ax4 = plt.subplot2grid((2,8), (0,6), colspan=2)
        ax5 = plt.subplot2grid((2,8), (1,1), colspan=2)
        ax6 = plt.subplot2grid((2,8), (1,3), colspan=2)
        ax7 = plt.subplot2grid((2,8), (1,5), colspan=2)
        ax = np.array([ax1, ax2, ax3, ax4, ax5, ax6, ax7])

        regions = self.region_dfs.index.get_level_values(0).unique()

        for i, region in enumerate(regions):
            ax[i].set_title(region)
            ax[i].plot(self.region_dfs.loc[region]['daily_hospital_admissions'][self.start_date:self.end_date],
                       label='JUNE')
            ax[i].plot(self.admissions_data_df.loc['Admissions_Total', region][self.start_date:self.end_date],
                       label='Data', color='k')
            ax[i].set_ylabel('Daily hospital admissions')
        self.format_axes(ax)
        plt.tight_layout()

        box = ax.ravel()[-1].get_position()
        ax.ravel()[-1].set_position([box.x0, box.y0 + box.height * 0.1,
                    box.width, box.height * 0.9])
        ax.ravel()[-1].legend(loc='upper center', bbox_to_anchor=(-0.8, -0.3),
            fancybox=True, shadow=True, ncol=5, fontsize=12)
        plt.subplots_adjust(top=0.9, bottom=0.2)

        return fig


    def plot_regional_hospital_deaths(self):
        fig = plt.figure(figsize=(12, 6))
        fig.suptitle(f'Regional hospital deaths (run {self.run_no:03})')
        ax1 = plt.subplot2grid(shape=(2,8), loc=(0,0), colspan=2)
        ax2 = plt.subplot2grid((2,8), (0,2), colspan=2)
        ax3 = plt.subplot2grid((2,8), (0,4), colspan=2)
        ax4 = plt.subplot2grid((2,8), (0,6), colspan=2)
        ax5 = plt.subplot2grid((2,8), (1,1), colspan=2)
        ax6 = plt.subplot2grid((2,8), (1,3), colspan=2)
        ax7 = plt.subplot2grid((2,8), (1,5), colspan=2)
        ax = np.array([ax1, ax2, ax3, ax4, ax5, ax6, ax7])

        regions = self.region_dfs.index.get_level_values(0).unique()

        for i, region in enumerate(regions):
            ax[i].set_title(region)
            ax[i].plot(self.region_dfs.loc[region][['daily_deaths_hospital', 'daily_deaths_icu']].sum(axis=1)[self.start_date:self.end_date],
                       label='JUNE')
            ax[i].plot(self.deaths_data_df.loc['All ages', region][self.start_date:self.end_date],
                       label='Data', color='k')
            
            ax[i].set_ylabel('Daily hospital deaths')
        self.format_axes(ax)
        plt.tight_layout()

        box = ax.ravel()[-1].get_position()
        ax.ravel()[-1].set_position([box.x0, box.y0 + box.height * 0.1,
                    box.width, box.height * 0.9])
        ax.ravel()[-1].legend(loc='upper center', bbox_to_anchor=(-0.8, -0.3),
            fancybox=True, shadow=True, ncol=5, fontsize=12)
        plt.subplots_adjust(top=0.9, bottom=0.2)

        return fig


    def plot_cumulative_infected(self):
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.suptitle(f'Cumulative infections as percentage of population (run {self.run_no:03})')
        regions = self.region_dfs.index.get_level_values(0).unique()
        for region in regions:
            ax.plot(self.region_dfs['seroprevalence'][region][self.start_date:self.end_date], label=region)
        ax.plot(self.world_df['seroprevalence'][self.start_date:self.end_date], label='England', color='k')
        self.format_axes(np.array([ax]))
        ax.set_ylabel('Percentage cumulative infected')
        ax.legend(bbox_to_anchor=(1, 1))
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        plt.tight_layout()
        plt.subplots_adjust(top=0.9)

        return fig
