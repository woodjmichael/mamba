
# v1.1: Re-working capex calculation logic
# v1: Basic data import and clean, plots and capex table

# To-do's:
# Iron out pv capex calc (pv type priorities)

import os
import csv
import numpy as np
import datetime as dt
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

pd.options.mode.chained_assignment = None  # default='warn'

class ParamSet:
    def __init__(me, pv, bp, be, bh, gp, gt):
        me.pv = pv
        me.bp = bp
        me.be = be
        me.bh = bh
        me.gp = gp
        me.gt = gt

def interpret_resilience_metadata(datacsv):
    # read in PV, batt, etc. and pass back to file importer
    for row in datacsv:
        if len(row)>0:
            if row[0] == 'PV scaling factor':
                pv = row[1]
            elif row[0] == 'Battery power [kW]':
                bp = row[1]
            elif row[0] == 'Battery energy [kWh]':
                be = row[1]
            elif row[0] == 'Battery hours [kWh]':
                bh = row[1]
            elif row[0] == 'Generator 1 power [kW]':
                gp = row[1]
            elif row[0] == 'Generator 1 tank [gal]':
                gt = row[1]
    params = ParamSet(pv=pv, bp=bp, be=be, bh=bh, gp=gp, gt=gt)
    return(params)

def import_resilience_data(datacsv, params):
    data_header_row = 60
    for line_num, content in enumerate(datacsv):
        if len(content) > 0:
            if content[0] == 'Outage':
                data_header_row = line_num
    datacsv = datacsv[(data_header_row+2):]
    outage = []
    outage_start = []
    ttff = []
    cot = []
    for line in datacsv:
        if len(line) == 4:
            outage.append(line[0])             
            outage_start.append(dt.datetime.strptime(line[1], '%Y-%m-%d %H:%M:%S'))
            ttff.append(line[2])
            cot.append(line[3])
    data = pd.DataFrame({'outage':outage, 'outage_start':outage_start, 'ttff':ttff, 'cot':cot,
                         'pv':params.pv, 'bp': params.bp, 'be':params.be, 'gp':params.gp, 'gt':params.gt})
    data[['outage', 'ttff', 'cot', 'pv', 'bp', 'be', 'gp', 'gt']] =  data[['outage', 'ttff', 'cot', 'pv', 'bp', 'be', 'gp', 'gt']].apply(pd.to_numeric)
    return(data)
    
    
def summarize_tradespace(conf_seq):
    summary = pd.DataFrame()
    for filename in resilience_files:
        # open csv connection
        print(filename)
        filepath = dir + filename
        datacsv = list(csv.reader(open(filepath,'r'), delimiter=","))
        
        params = interpret_resilience_metadata(datacsv) # list of params
        
        data = import_resilience_data(datacsv, params) # 2920 x [4 mamba cols + 6 uniform params]

        # calculate confidence and add as a column
        for conf_duration in conf_seq:
            data[str(np.floor(conf_duration))] = len(data[data['ttff']>=conf_duration])/len(data)
            
        # once conf is calculated can drop the outage-specific cols and take only unique rows
        data = data.drop(['outage', 'outage_start', 'ttff', 'cot'], axis=1)
        data = data.drop_duplicates() # should be a one-row dataframe
        summary = summary.append(data)
    return(summary)

def make_long_tradespace(summary_wide, filter_successful = False, dur=np.NaN, conf=np.NaN):

    summary = summary_wide
    if filter_successful:
        # select only the rows for which the duration column (indicated by param) has a confidence value greater than that indicated
        summary = summary[summary_wide[str(float(dur))] >= conf]

    # make long: just one duration column and one conf column
    summary = summary.melt(id_vars = ['pv', 'bp', 'be', 'gp', 'gt'], var_name = 'duration', value_name = 'confidence')
    summary['duration'] = summary['duration'].astype(str).astype(float)
    summary['bh'] = summary['be'] / summary['bp']
    # print(summary)
    return(summary)

def tradespace_conf_plot(summary_df, title='', conf=np.NaN):
    if summary_df.shape[0] == 0:
        return None
    for gp in summary_df['gp'].unique():
        plot_df = summary_df[summary_df.loc[:,'gp'] == gp]
        g = sns.FacetGrid(plot_df, row="bp", col="pv", hue="bh")
        conf_plot = g.map(sns.scatterplot, "duration", "confidence", )
        conf_plot = conf_plot.map(sns.lineplot, "duration", "confidence")
        conf_plot = conf_plot.map(plt.axhline, y=conf, ls='--', c='black')
        conf_plot = conf_plot.add_legend()
        plt.savefig('conf_plot_' + title + '_gen' + str(gp) + '.png')

    #### Next tweaks:
    # fix labels
    # title with site etc. idk

def summarize_capex(summary_df, duration_standard, pv_rf_cap, pv_rf_cost, pv_cp_cost, bp_cost, be_cost):
    if summary_df.shape[0] == 0:
        return None
    capex_df = summary_df[summary_df.loc[:,'duration'] == duration_standard]
    def calc_pv(pv):
        if pv <= pv_rf_cap:
            return(pv * pv_rf_cost)
        elif pv > pv_rf_cap:
            return(pv_rf_cap * pv_rf_cost + (pv - pv_rf_cap) * pv_cp_cost)
        else:
            return('somethings wrong')
    capex_df.loc[:,'capex_pv'] = [calc_pv(pv) for pv in capex_df.loc[:, 'pv']]
    capex_df.loc[:,'capex'] = capex_df.loc[:,'capex_pv'] + capex_df.loc[:,'bp'] * bp_cost + capex_df.loc[:,'be'] * be_cost
    capex_df.drop(columns=['capex_pv'])
    return(capex_df)    

def tradespace_capex_plot(capex_df, title=''):
    if capex_df is None:
        return None
    capex_max = capex_df['capex'].max()
    capex_min = capex_df['capex'].min()
    cols = capex_df['bh'].unique()
    cols = np.sort(cols)
    rows = capex_df['pv'].unique()
    rows = np.sort(rows)

    def draw_heatmap(*args, **kwargs):
        data = kwargs.pop('data')
        piv = data.pivot(index=args[1], columns=args[0], values=args[2])
        piv = piv.reindex(cols, axis=1).reindex(rows, axis=0)
        p = sns.heatmap(piv, **kwargs, vmax=capex_max, vmin=capex_min)
        p.invert_yaxis()
        return(p)

    fg = sns.FacetGrid(capex_df, row='bp', col='gp')
    fg.map_dataframe(draw_heatmap, 'bh', 'pv', 'capex', cbar=True)
    #plt.show()
    plt.savefig('capex_plot_' + title + '.png')

def capex_table(capex_df):
    if capex_df is None:
        return None
    df1 = capex_df.groupby(['pv'])
    df2 = df1.apply(lambda x: x.sort_values(['capex']))
    df3 = df2.reset_index(drop=True)
    df4 = df3.groupby(['pv']).head(10)
    return(df4)

# These vars (or some version) should ultimately be params for this script
dir = 'Data/Output/cvh_gencase/'
conf_seq = np.linspace(24, 504, 11)
duration_standard = 504
confidence_standard = 0.5
pv_rf_cost = 2500
pv_rf_cap = 339.6
pv_cp_cost = 3500
bp_cost = 100
be_cost = 1000

# Begin processing
all_files = os.listdir(dir)
resilience_files = [file for file in all_files if "resilience" in file \
                    and "superloop" not in file]
summary_wide = summarize_tradespace(conf_seq)
summary = make_long_tradespace(summary_wide)
summary_only_successful = make_long_tradespace(summary_wide, filter_successful=True, conf = confidence_standard, dur = duration_standard)
print(summary_only_successful)

# Plots / tables
tradespace_conf_plot(summary, 'all_cases', confidence_standard)
tradespace_conf_plot(summary_only_successful, 'successful_cases', confidence_standard)
capex_df = summarize_capex(summary_only_successful, duration_standard, pv_rf_cap, pv_rf_cost, pv_cp_cost, bp_cost, be_cost)
tradespace_capex_plot(capex_df)
capex_table = capex_table(capex_df)
if capex_table is not None:
    capex_table.to_csv('capex_table.csv', index=False) # needs to be only the ten cheapest systems
