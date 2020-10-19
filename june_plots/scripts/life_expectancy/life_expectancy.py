import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from scipy.stats import binned_statistic

from pathlib import Path

from june import paths

data_path = paths.data_path / "plotting/life_expectancy"

# Geography data
default_oa_lsoa_path = data_path / "oa_lsoa_msoa_lad.csv"
default_wd_wcmd_path = data_path / "w_cmw_lad.csv"
default_oa_wd_path = data_path / "oa_w_lad.csv"
# LE data
default_le_path = data_path / "life_expectancy.xls"
# IOMD data
default_iomd_path = data_path / "eng_lsoa_iomd_2019.xlsx"

class LifeExpectancyPlots:
    """
    Plot life expectancy
    """

    def __init__(self, colors):
        self.colors = colors

    def load_oa_lsoa_mapping(self, oa_lsoa_path=default_oa_lsoa_path):
        oa_lsoa = pd.read_csv(oa_lsoa_path)
        col_dict = {'OA11CD':'oa','LSOA11CD':'lsoa','MSOA11CD':'msoa','RGN11NM':'reg','CTRY11NM':'country'}
        oa_lsoa.rename(col_dict,axis=1,inplace=True)
        drop_cols = [col for col in oa_lsoa.columns if col not in col_dict.values()]
        oa_lsoa.drop(drop_cols,axis=1,inplace=True)
        oa_lsoa.set_index('oa',inplace=True,verify_integrity=True)
        self.oa_lsoa = oa_lsoa

    def load_wd_cmwd_mapping(self, wd_wcmd_path=default_wd_wcmd_path):
        wd_cmwd = pd.read_csv(wd_wcmd_path)
        col_dict = {'WD11CD':'wd', 'CMWD11CD':'cmwd','LAD11CD':'lad'}
        wd_cmwd.rename(col_dict,axis=1,inplace=True)
        drop_cols = [col for col in wd_cmwd.columns if col not in col_dict.values()]
        wd_cmwd.drop(drop_cols,axis=1,inplace=True)
        self.wd_cmwd = wd_cmwd

    def load_oa_wd_mapping(self, oa_wd_path=default_oa_wd_path):
        oa_wd = pd.read_csv(oa_wd_path)
        col_dict = {'OA11CD':'oa','WD11CD':'wd','LAD11CD':'lad'}
        oa_wd.rename(col_dict,axis=1,inplace=True)
        drop_cols = [col for col in oa_wd.columns if col not in col_dict.values()]
        oa_wd.drop(drop_cols,axis=1,inplace=True)
        self.oa_wd = oa_wd

    def merge_geography_mappings(self,):
        oa_cmwd = pd.merge(
            self.oa_wd, self.wd_cmwd, left_on="wd",right_on="wd",how="outer",validate="many_to_one"
        )

        oa_cmwd.set_index('oa',inplace=True) #,verify_integrity=True)
        old_len = len(oa_cmwd)

        mask = oa_cmwd.index.duplicated(keep='first')

        self.oa_cmwd = oa_cmwd[ ~mask ]

        print(f'drop {old_len-len(self.oa_cmwd)} duplicate OAs...')

    def load_geography_data(
        self,
        oa_lsoa_path=default_oa_lsoa_path,
        wd_wcmd_path=default_wd_wcmd_path,
        oa_wd_path=default_oa_wd_path    
    ):
        """Load and merge geography mappings.

        # NOTE:
        ### oa = "output_area"
        ### lsoa = "lower-level super output area"
        ### w = "ward"
        ### cmw = "census merged ward".
        ### there seems to be no nice mapping from OA->CMW available...
        """

        self.load_oa_lsoa_mapping(oa_lsoa_path=oa_lsoa_path)
        self.load_wd_cmwd_mapping(wd_wcmd_path=wd_wcmd_path)
        self.load_oa_wd_mapping(oa_wd_path=oa_wd_path)
        self.merge_geography_mappings()

    @staticmethod
    def get_xtile(data,x=10):
        """what percentiles to the data fall in?"""
        bins = np.linspace(1,data.max()+1,x+1).astype(int)
        counts,edges = np.histogram(data,bins)
        print(f'for {x}-tiles, range of counts from {counts.max()} to {counts.min()} per bin')
        xtiles = np.digitize(data,bins) # -1 as digitize assumes bins are [-inf,bins[0],bins[1]...bins[n],inf]
        return xtiles

    def load_iomd(self, iomd_path=default_iomd_path):
        """
        Read index of multiple deprivation data.
        Data taken from:
        https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019
        """

        # https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019 -> "File 1:..."

        eng_iomd = pd.read_excel(default_iomd_path,sheet_name=1,index_col=0)

        eng_col_dict = {
            'LSOA name (2011)':'lsoa_name',
            'Local Authority District code (2013)':'lad',
            'Local Authority District name (2013)':'lad_name',
            'Index of Multiple Deprivation (IMD) Rank (where 1 is most deprived)':'iomd_rank',
            'Index of Multiple Deprivation (IMD) Decile (where 1 is most deprived 10% of LSOAs)':'ons_iomd_decile'
        }

        eng_drop_cols = ['lsoa_name','lad_name','lad']

        eng_iomd.rename(eng_col_dict,inplace=True,axis=1)
        eng_iomd.drop(eng_drop_cols,inplace=True,axis=1)
        eng_iomd.index.rename('lsoa',inplace=True)



        eng_iomd['iomd_decile'] = self.get_xtile(eng_iomd['iomd_rank'],x=10) / 10 # For testing only.
        eng_iomd['iomd_centile'] = self.get_xtile(eng_iomd['iomd_rank'],x=100) / 100
        #eng_iomd['permiltile'] = get_xtile(eng_iomd['iomd_rank'],x=1000) / 1000

        eng_oa_lsoa = self.oa_lsoa.query('index.str.startswith("E")') # Get rid of all the Welsh OAs


        ### IOMD is given on an LSOA level... we need to find convert to OAs in each LSOA.
        oa_iomd = eng_iomd.loc[ eng_oa_lsoa['lsoa'] ]
        oa_iomd['oa'] = eng_oa_lsoa.index

        oa_iomd.reset_index(inplace=True)
        oa_iomd.set_index('oa',inplace=True,verify_integrity=True)

        oa_iomd = pd.merge(oa_iomd,self.oa_lsoa["msoa"],how="left",left_index=True,right_index=True,validate="one_to_one")

        self.oa_iomd = oa_iomd

    @staticmethod
    def get_xbins(x):
        """sort of like linspace, but includes the endpoint, and does
        -0.005,0.005,0.010...0.995,1.005
        """
        dx = 1./x
        return np.arange(0.-0.5*dx,1.+1.5*dx,dx)

    def load_life_expectancy(self, le_path = default_le_path):
        """Read life expectancy data.

        """

        male_le = pd.read_excel(le_path,sheet_name=1,header=9) # 65 yr olds
        female_le = pd.read_excel(le_path,sheet_name=3,header=9) # 65 yr olds

        le_cols = {
            '2011 Census Ward code' : 'cmwd',
            '2011 Census Ward name' : 'cmwd_nm',
            'Region': 'rgn',
            'Local authority code': 'lad',
            'Local authority name': 'lad_nm',
            'LE (years)': 'le', # life-expectancy
            'HLE (years)': 'hle', #"healthy" life expectance.
            'Inequality in HLE (years)': 'inequality'
        }

        male_le.rename(le_cols,inplace=True,axis=1)
        female_le.rename(le_cols,inplace=True,axis=1)

        male_le.set_index('cmwd',inplace=True,verify_integrity=True)
        female_le.set_index('cmwd',inplace=True,verify_integrity=True)

        male_le = male_le[male_le.index.str.startswith("E")]
        female_le = female_le[female_le.index.str.startswith("E")] # Drop Wales
        
        # A transform from
        labels = self.oa_cmwd.loc[ self.oa_iomd.index ]["cmwd"]

        ## which OAs do we have life expecectancy data for?
        mask = ( labels.isin(male_le.index) ) & ( labels.isin(female_le.index) )

        # Throw out all the OA rows in IOMD who won't have a match for the CMWD in life-expectancy.
        self.oa_iomd = self.oa_iomd[ mask ] 
        labels = labels[ mask ]


        # Need to do "values" as the index for the output array is in terms of cwmd, NOT oa.
        self.oa_iomd["male_le"] = male_le["le"].loc[ labels ].values+65.
        self.oa_iomd["female_le"] = female_le["le"].loc[ labels ].values+65.

        

    def plot_life_expectancy_socioecon_index(self):

        percentile_bins = self.get_xbins(100)
        percentile_mids = 0.5*(percentile_bins[:-1]+percentile_bins[:-1])

        m_mean,_,_ = binned_statistic(
            self.oa_iomd["iomd_centile"], self.oa_iomd["male_le"], statistic='mean', bins=percentile_bins
        )

        m_std,_,_ = binned_statistic(
            self.oa_iomd["iomd_centile"], self.oa_iomd["male_le"], statistic='std', bins=percentile_bins
        )

        f_mean,_,_ = binned_statistic(
            self.oa_iomd["iomd_centile"], self.oa_iomd["female_le"], statistic='mean', bins=percentile_bins
        )

        f_std,_,_ = binned_statistic(
            self.oa_iomd["iomd_centile"], self.oa_iomd["female_le"], statistic='std', bins=percentile_bins
        )

        f,ax = plt.subplots()
        #ax.scatter(oa_iomd["percentile"]+0.005,oa_iomd["male_le"],s=1,alpha=0.1)
        ax.plot(percentile_mids,m_mean,label='male',color=self.colors['male'])
        ax.fill_between(percentile_mids,m_mean-m_std,m_mean+m_std,color=self.colors['male'],alpha = 0.5)
        ax.plot(percentile_mids,f_mean,color=self.colors['female'],label='female')
        ax.fill_between(percentile_mids,f_mean-f_std,f_mean+f_std,color=self.colors['female'],alpha = 0.5)
        #ax.scatter(oa_iomd["percentile"],oa_iomd["female_le"],s=1,alpha=0.1)

        ax.set_xlabel("Scaled socio-economic index (lower is more deprived)")
        ax.set_ylabel("Expected life expectancy (for adults age 65)")
        ax.legend()
        return ax
