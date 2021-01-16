#!/usr/bin/env python
# coding: utf-8

# In[26]:


import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt
import datetime
import json
import bokeh
from bokeh.plotting import figure, output_notebook, show#, vplot
from bokeh.palettes import Spectral11
from bokeh.models import Legend, LegendItem
from bokeh.models.tools import HoverTool
output_notebook()

from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa


# In[2]:


# with open('yahoo_creds.json', 'rb') as f:
#     YAHOO_CREDS = json.load(f)


# In[3]:


sc = OAuth2(None, None, from_file='/home/runner/secrets/yahoo_creds.json')
print('sc:')
print(sc)

# In[4]:


gm = yfa.Game(sc, 'nba')
gm.league_ids(year=2020)


# In[5]:


lg = gm.to_league('402.l.27278')
lg.stat_categories()


# In[6]:


lg.teams()['402.l.27278.t.3']['managers'][0]['manager']['nickname']


# In[7]:


teams_list = []

for team_key, team_data in lg.teams().items():
    print(team_key)
    name = team_data['name']
    team_id = team_data['team_id']
    nickname = team_data['managers'][0]['manager']['nickname']
    teams_list.append([team_key, team_id, name, nickname])


# In[8]:


team_mapping = pd.DataFrame(teams_list, columns=['team_key', 'team_id', 'team_name', 'nickname'])
team_mapping


# In[9]:


stat_id_mapping = {'9004003': 'FGM/FGA',
                   '5': 'FG%',
                   '9007006': 'FTM/FTA',
                   '8': 'FT%',
                   '10': '3PTM',
                   '12': 'PTS',
                   '15': 'REB',
                   '16': 'AST',
                   '17': 'ST',
                   '18': 'BLK',
                   '19': 'TO'
                  }
stat_id_mapping


# #### Build dictionary of weekly matchups (between team ids) and results

# In[10]:


all_results = pd.DataFrame()

for week in np.arange(1, lg.current_week()+1):
    for idx, m in lg.matchups(week=week)['fantasy_content']['league'][1]['scoreboard']['0']['matchups'].items():
        if idx in ['0', '1', '2', '3', '4', '5']:  # 12 teams, each week as 6 matchups
            stat_winners = m['matchup']['stat_winners']
            rows_list = []
            for row in stat_winners:
                rows_list.append(row['stat_winner'])
            week_result_df = pd.DataFrame(rows_list)
            week_result = week_result_df.winner_team_key.value_counts().reset_index().rename(columns={'index': 'team_key', 
                                                                                       'winner_team_key': 'score_raw'
                                                                                      })
            if week_result.loc[0]['score_raw'] > week_result.loc[1]['score_raw']:
                results_list = [1, 0]
            elif week_result.loc[0]['score_raw'] < week_result.loc[1]['score_raw']:
                results_list = [0, 1]
            else:
                results_list = [.5, .5]

            week_result['score_final'] = results_list
            week_result['week'] = week
            week_result['opponent_team_key'] = '' 
            two_teams = list(week_result.team_key.unique())
            for i, row in week_result.iterrows():
                week_result.loc[i, 'opponent_team_key'] = [t for t in two_teams if t != row['team_key']][0]
            week_result = pd.merge(week_result, team_mapping[['team_key', 'team_id', 'team_name']], how='left', on='team_key')
            week_result = pd.merge(week_result,
                                     team_mapping[['team_key', 'team_id', 'team_name']].rename(columns={'team_key': 'opponent_team_key',
                                                                                               'team_id': 'opponent_team_id',
                                                                                               'team_name': 'opponent_team_name'}),
                                     how='left',
                                     on='opponent_team_key')
            week_result = week_result[['week', 'team_name', 'team_id', 'opponent_team_name', 'opponent_team_id', 'score_final', 'score_raw']]
            all_results = pd.concat([all_results, week_result], sort=False)
            
all_results = all_results.reset_index(drop=True)
all_results.team_id = all_results.team_id.astype(int)


# In[11]:


all_results


# In[12]:


all_results.groupby('week')['score_final'].sum()  # check looks good


# #### Build stats summary table, at the team-week level

# In[13]:


df = pd.DataFrame(columns = ['week', 'team_id'] + list(stat_id_mapping.values()))

for week in np.arange(1, lg.current_week()+1):
    for idx, m in lg.matchups(week=week)['fantasy_content']['league'][1]['scoreboard']['0']['matchups'].items():
        if idx in ['0', '1', '2', '3', '4', '5']:  # 12 teams, each week as 6 matchups
            teams = m['matchup']['0']['teams']

            # create stats summary, by team and week
            new_matchup = []
            for i, team in teams.items():
                if isinstance(team, dict):
                    team_id = team['team'][0][1]['team_id']
                    stats_raw = team['team'][1]['team_stats']['stats']
                    rows_list = []
                    for row in stats_raw:
                        rows_list.append(row['stat'])
                    df_raw = pd.DataFrame(rows_list)
                    df_raw.stat_id = df_raw.stat_id.replace(stat_id_mapping)
                    df_raw = df_raw.rename(columns={'value': f'{team_id}', 'stat_id': 'stat_category'})
                    df_raw = df_raw.set_index('stat_category').T.reset_index().rename(columns={'index': 'team_id'})
                    df_raw['week'] = week
                    print(df_raw)
                    df = pd.concat([df, df_raw], sort=False)            

df = pd.merge(df, team_mapping[['team_id', 'team_name']], how='left', on='team_id')
df = df[['week', 'team_name', 'team_id', 'FGM/FGA', 'FG%', 'FTM/FTA', 'FT%', '3PTM', 'PTS',
       'REB', 'AST', 'ST', 'BLK', 'TO']]
df = df.sort_values(['week', 'team_name'])
df = df.reset_index(drop=True)
df['FGM'] = df['FGM/FGA'].str.split('/').apply(lambda x: x[0])
df['FGA'] = df['FGM/FGA'].str.split('/').apply(lambda x: x[1])
df['FTM'] = df['FTM/FTA'].str.split('/').apply(lambda x: x[0])
df['FTA'] = df['FTM/FTA'].str.split('/').apply(lambda x: x[1])
df = df.drop(['FGM/FGA', 'FTM/FTA'], axis=1)
all_stats = df


# In[14]:


all_stats.info()


# In[15]:


for colname in ['week', 'team_id', '3PTM', 'PTS', 'REB', 'AST', 'ST', 'BLK', 'TO', 'FGM', 'FGA', 'FTM', 'FTA']:
        all_stats[colname] = all_stats[colname].astype(int)
        
for colname in ['FG%', 'FT%']:
        all_stats[colname] = all_stats[colname].astype(float)


# In[16]:


all_stats.info()


# In[17]:


all_stats.groupby(['week']).mean()


# In[18]:


df = pd.merge(all_stats, all_results, on=['week', 'team_name', 'team_id'], how='left')
print(df.shape)
df.head()


# In[19]:


df.groupby(['week', 'score_final']).mean()


# #### Plot some line graphs

# In[62]:


def get_weekday(x):
    if x == 0:
        return 'Mon'
    elif x == 1:
        return 'Tue'
    elif x == 2:
        return 'Wed'
    elif x == 3:
        return 'Thu'
    elif x == 4:
        return 'Fri'
    elif x == 5:
        return 'Sat'
    else:
        return 'Sun'


# In[64]:


def plot_weekly_stats(plot_df, stat, save_filepath=None, plot_team='Flat Earthers'):
    """
    """
    plot_df = plot_df.rename(columns={'FG%': 'FG_PCT', 'FT%': 'FT_PCT'})
    runtime = datetime.datetime.now()

    p = figure(title=f'{stat}   (last updated: {get_weekday(runtime.weekday())} {runtime.strftime("%m/%d %H:%M")})',
                 x_axis_label='Week',
                 y_axis_label=stat,
                 width=600,
                 height=400)

    xs = [plot_df.week.unique()] * 12

    ys = [plot_df[plot_df.team_name == plot_team][stat].values]
    for team in plot_df[plot_df.team_name != plot_team].team_name.unique():
        ys.append(plot_df[plot_df.team_name == team][stat].values)

    opps = plot_df[plot_df.team_name == plot_team]['opponent_team_name'].to_numpy()
    opp_vals = plot_df[(plot_df.team_name.isin(opps)) & (plot_df.opponent_team_name  == plot_team)][stat].values

    r = p.multi_line(xs, ys, 
                   line_color=['blue'] + ['grey'] * 11, 
                   alpha=[1] + [0.5] * 11, 
                   line_width=2)
    p.circle('week', f'{stat}', 
             source=plot_df[(plot_df.team_name == plot_team)], 
             color='blue', fill_color='white', size=12)
    p.circle('week', f'{stat}', 
             source=plot_df[(plot_df.team_name.isin(opps)) & (plot_df.opponent_team_name  == plot_team)], 
             color='red', fill_color='white', size=12)
    # p.circle(xs[1], opp_vals, color='red', fill_color='white', size=10)


    legend = Legend(items=[
        LegendItem(label=plot_team, renderers=[r], index=0),
    ])

    p.add_tools(HoverTool(
        tooltips=[
            ('Team', '@team_name'),
            (f'{stat}', f'@{stat}')
        ]
    ))

    p.add_layout(legend)
    if save_filepath:
        print('Saving to', save_filepath)
        bokeh.plotting.output_file(save_filepath)
        show(p)
    else:
        show(p)
    return p


# In[65]:


plot_list = []
for category in ['FG_PCT', 'FT_PCT', '3PTM', 'PTS', 'REB', 'AST', 'ST', 'BLK', 'TO']:
    p = plot_weekly_stats(plot_df=df, stat=category, save_filepath=f"img/{category}_plot.html") #, plot_team='Olly-G Anunoby')
    plot_list.append(p)


# In[66]:


bokeh.plotting.output_file('index.html')
show(bokeh.layouts.gridplot(plot_list, ncols=2))


# In[ ]:




