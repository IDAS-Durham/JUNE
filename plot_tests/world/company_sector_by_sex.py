from collections import Counter import pandas as pd
import numpy as np
import pickle

import seaborn as sns

from june.inputs import Inputs 
from june.world import World

sns.set_context('paper')



def company_sector_freq_by_sex(world):
    """
    Fraction of woman (or man) working in a specific company sector
    averaged over all areas.
    """
    # get company sex distribution from input data
    in_compsec_by_sex_df = world.inputs.compsec_by_sex_df
    nr_of_areas = len(in_compsec_by_sex_df.index)
    m_columns = [col for col in in_compsec_by_sex_df.columns.values if "m " in col]
    f_columns = [col for col in in_compsec_by_sex_df.columns.values if "f " in col]
    in_compsec_by_sex_df = in_compsec_by_sex_df.sum(axis='rows')
    in_compsec_by_sex_df = in_compsec_by_sex_df.div(nr_of_areas, axis='rows')
    in_compsec_by_sex_df = in_compsec_by_sex_df.reset_index()
    in_compsec_by_sex_df = in_compsec_by_sex_df.rename(
        columns={"index":"sex_sec", 0:"ratio"}
    )

    # get company sex distribution from output data
    sex_decoder = {0:'m', 1:'f'}
    out_compsec_by_sex_df = []
    index = []
    for area in world.areas.members[:]:
        index.append(area.name)
        
        company_sec_label = {col: 0 for idx,col in enumerate(m_columns)}
        for col in f_columns:
            company_sec_label[col] = 0

        labels = [
            [sex_decoder[person.sex]+' '+person.industry] for person in area.people
            if person.industry is not None
        ]
        
        for lab in labels:
            company_sec_label[lab[0]] += 1
            
        out_compsec_by_sex_df.append(list(company_sec_label.values()))
        
    out_compsec_by_sex_df = pd.DataFrame(
        data=out_compsec_by_sex_df,
        columns=list(company_sec_label.keys()),
        index=index,
    )
    # convert counts to ratios
    out_compsec_by_sex_df.loc[:, m_columns] = out_compsec_by_sex_df.loc[:, m_columns].div(
        out_compsec_by_sex_df[m_columns].sum(axis=1), axis=0
    )
    out_compsec_by_sex_df.loc[:, f_columns] = out_compsec_by_sex_df.loc[:, f_columns].div(
        out_compsec_by_sex_df[f_columns].sum(axis=1), axis=0
    )
    
    # merge input and output data to prepare for plot
    nr_of_areas = len(out_compsec_by_sex_df.index)
    out_compsec_by_sex_df = out_compsec_by_sex_df.sum(axis='rows')
    out_compsec_by_sex_df = out_compsec_by_sex_df.div(nr_of_areas, axis='rows')
    out_compsec_by_sex_df = out_compsec_by_sex_df.reset_index()
    out_compsec_by_sex_df = out_compsec_by_sex_df.rename(
        columns={"index":"sex_sec", 0:"ratio"}
    )
    in_compsec_by_sex_df["src"] = ["input"] * len(in_compsec_by_sex_df.index.values)
    out_compsec_by_sex_df["src"] = ["output"] * len(out_compsec_by_sex_df.values)
    compsec_by_sex_df = pd.concat([in_compsec_by_sex_df, out_compsec_by_sex_df], axis=0)
    return compsec_by_sex_df


if __name__=='__main__':
    world = World.from_pickle()
    compsec_by_sex_df = company_sector_freq_by_sex(world)
    
    fig = sns.catplot(
        x="sex_sec",
        y="ratio",
        hue="src",
        data=compsec_by_sex_df,
        kind="bar",
        palette="muted",
        height=5, # make the plot 5 units high
        aspect=3,
    )
    fig.savefig(
        'company_sector_by_sex.png',
        dpi=250,
        bbox_to_anchor='tight',
    )


