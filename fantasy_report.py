import pandas as pd
import numpy as np
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


def authenticate_yahoo(run_on_gh=True):
    if run_on_gh:
        sc = OAuth2(None, None, from_file='/home/runner/secrets/yahoo_creds.json')
        print('sc:', sc)
    else:  # run locally
        sc = OAuth2(None, None, from_file='yahoo_creds.json')
        print('sc:', sc)
    return sc


sc = authenticate_yahoo()

gm = yfa.Game(sc, 'nba')
gm.league_ids(year=2021)

# set constants
LEAGUE_ID = '410.l.21086'
TEAM_NAME = 'Backpack Kids'  
TEAM_ID = '410.l.21086.t.8'


lg = gm.to_league(LEAGUE_ID)
lg.stat_categories()


teams_list = []

for team_key, team_data in lg.teams().items():
    print(team_key)
    name = team_data['name']
    team_id = team_data['team_id']
    nickname = team_data['managers'][0]['manager']['nickname']
    teams_list.append([team_key, team_id, name, nickname])


team_mapping = pd.DataFrame(teams_list, columns=['team_key', 'team_id', 'team_name', 'nickname'])
team_mapping


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


# #### Get next week's opponent

# +
for idx, m in lg.matchups(week=lg.current_week()+1)['fantasy_content']['league'][1]['scoreboard']['0']['matchups'].items():
    if idx in ['0', '1', '2', '3', '4', '5']:  # 12 teams, each week as 6 matchups
        
        t1_key = m['matchup']['0']['teams']['0']['team'][0][0]['team_key']
        t1_name = m['matchup']['0']['teams']['0']['team'][0][2]['name']
        t2_key = m['matchup']['0']['teams']['1']['team'][0][0]['team_key']
        t2_name = m['matchup']['0']['teams']['1']['team'][0][2]['name']
        
        if TEAM_ID in [t1_key, t2_key]:
            next_df = pd.DataFrame({'team_key': [t1_key, t2_key], 'team_name': [t1_name, t2_name]})
            
next_week_opp_id = next_df[next_df.team_key != TEAM_ID].team_key.iloc[0]
next_week_opp_name = next_df[next_df.team_key != TEAM_ID].team_name.iloc[0]
print(next_week_opp_id)
print(next_week_opp_name)
# -

# #### Build dictionary of weekly matchups (between team ids) and results

all_results = pd.DataFrame()

for week in np.arange(1, lg.current_week()+1):
#     print(week)
    for idx, m in lg.matchups(week=week)['fantasy_content']['league'][1]['scoreboard']['0']['matchups'].items():
#         print(idx)
        if idx in ['0', '1', '2', '3', '4', '5']:  # 12 teams, each week as 6 matchups
            
            t1_key = m['matchup']['0']['teams']['0']['team'][0][0]['team_key']
            t1_name = m['matchup']['0']['teams']['0']['team'][0][2]['name']
#             print(t1_key)
#             print(t1_name)
            t2_key = m['matchup']['0']['teams']['1']['team'][0][0]['team_key']
            t2_name = m['matchup']['0']['teams']['1']['team'][0][2]['name']
#             print(t2_key)
#             print(t2_name)
            teams_df = pd.DataFrame({'team_key': [t1_key, t2_key]})
            
            stat_winners = m['matchup']['stat_winners']
            rows_list = []
            for row in stat_winners:
                rows_list.append(row['stat_winner'])
            week_result_df = pd.DataFrame(rows_list)
            week_result = week_result_df.winner_team_key.value_counts().reset_index().rename(
                columns={'index': 'team_key', 
                         'winner_team_key': 'score_raw'})
            
            week_result = pd.merge(
                teams_df, 
                week_result,
                how='left',
                on='team_key')
            week_result.score_raw.fillna(0, inplace=True)
            
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

all_results.groupby('week')['score_final'].sum()  # check looks good


# #### Build stats summary table, at the team-week level

df = pd.DataFrame(columns = ['week', 'team_id'] + list(stat_id_mapping.values()))

for week in np.arange(1, lg.current_week()+1):
    for idx, m in lg.matchups(week=week)['fantasy_content']['league'][1]['scoreboard']['0']['matchups'].items():
        if idx in ['0', '1', '2', '3', '4']:  # 10 teams, each week as 5 matchups
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

all_stats.info()


for colname in ['week', 'team_id', '3PTM', 'PTS', 'REB', 'AST', 'ST', 'BLK', 'TO', 'FGM', 'FGA', 'FTM', 'FTA']:
    all_stats[colname] = all_stats[colname].astype(int)

for colname in ['FG%', 'FT%']:
    all_stats[colname] = all_stats[colname].astype(float)

all_stats.info()


all_stats.groupby(['week']).mean()

df = pd.merge(all_stats, all_results, on=['week', 'team_name', 'team_id'], how='left')
print(df.shape)
df.head()

df.groupby(['week', 'score_final']).mean()

df


# #### Plot some line graphs

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

# +
# def plot_weekly_stats(plot_df, stat, save_filepath=None, plot_team=TEAM_NAME):
#     """
#     """
#     plot_df = plot_df.rename(columns={'FG%': 'FG_PCT', 'FT%': 'FT_PCT'})
#     runtime = datetime.datetime.now()

#     p = figure(title=f'{stat}   (last updated: {get_weekday(runtime.weekday())} {runtime.strftime("%m/%d %H:%M")})',
#                  x_axis_label='Week',
#                  y_axis_label=stat,
#                  width=600,
#                  height=400)

#     xs = [plot_df.week.unique()] * 12

#     ys = [plot_df[plot_df.team_name == plot_team][stat].values]
#     for team in plot_df[plot_df.team_name != plot_team].team_name.unique():
#         ys.append(plot_df[plot_df.team_name == team][stat].values)

#     opps = plot_df[plot_df.team_name == plot_team]['opponent_team_name'].to_numpy()
#     opp_vals = plot_df[(plot_df.team_name.isin(opps)) & (plot_df.opponent_team_name  == plot_team)][stat].values

#     r = p.multi_line(xs, ys, 
#                    line_color=['blue'] + ['grey'] * 11, 
#                    alpha=[1] + [0.2] * 11, 
#                    line_width=2)
#     r2 = p.line('week', f'{stat}',
#            source=plot_df[plot_df.team_name == opps[-1]],
#            color='red', alpha=1, line_width=2)
#     p.circle('week', f'{stat}', 
#              source=plot_df[(plot_df.team_name == plot_team)], 
#              color='blue', fill_color='white', size=12)
#     p.circle('week', f'{stat}', 
#              source=plot_df[(plot_df.team_name.isin(opps)) & (plot_df.opponent_team_name  == plot_team)], 
#              color='red', fill_color='white', size=12)
    
#     # add next opponent
    

#     legend = Legend(items=[
#         LegendItem(label=plot_team, renderers=[r], index=0),
#         LegendItem(label=opps[-1], renderers=[r2], index=1)
#     ])

#     p.add_tools(HoverTool(
#         tooltips=[
#             ('Team', '@team_name'),
#             (f'{stat}', f'@{stat}')
#         ]
#     ))

#     p.add_layout(legend)
#     p.xaxis.ticker = plot_df.week.unique()
    
#     if save_filepath:
#         print('Saving to', save_filepath)
#         bokeh.plotting.output_file(save_filepath)
#         show(p)
#     else:
#         show(p)
#     return p

# +
# plot_list = []
# for category in ['FG_PCT', 'FT_PCT', '3PTM', 'PTS', 'REB', 'AST', 'ST', 'BLK', 'TO']:
#     p = plot_weekly_stats(plot_df=df, stat=category)
#     plot_list.append(p)
# -


def plot_weekly_stats(plot_df, stat, next_opp_id, next_opp_name, save_filepath=None, plot_team=TEAM_NAME):
    """
    """
    plot_df = plot_df.rename(columns={'FG%': 'FG_PCT', 'FT%': 'FT_PCT'})
    runtime = datetime.datetime.now()

    p = figure(title=f'{stat}   (last updated: {get_weekday(runtime.weekday())} {runtime.strftime("%m/%d %H:%M")})',
                 x_axis_label='Week',
                 y_axis_label=stat,
                 width=600,
                 height=400)

    xs = [plot_df.week.unique()] * 10

    ys = [plot_df[plot_df.team_name == plot_team][stat].values]
    for team in plot_df[plot_df.team_name != plot_team].team_name.unique():
        ys.append(plot_df[plot_df.team_name == team][stat].values)

    opps = plot_df[plot_df.team_name == plot_team]['opponent_team_name'].to_numpy()
    opp_vals = plot_df[(plot_df.team_name.isin(opps)) & (plot_df.opponent_team_name  == plot_team)][stat].values

    # add next opponent
    r3 = p.line('week', f'{stat}',
           source=plot_df[plot_df.team_name == next_opp_name],
           color='orange', alpha=0.5, line_width=2)    
    
    r = p.multi_line(xs, ys, 
                   line_color=['blue'] + ['grey'] * 9, 
                   alpha=[1] + [0.1] * 9, 
                   line_width=2)
    r2 = p.line('week', f'{stat}',
           source=plot_df[plot_df.team_name == opps[-1]],
           color='red', alpha=1, line_width=2)
    p.circle('week', f'{stat}', 
             source=plot_df[(plot_df.team_name == plot_team)], 
             color='blue', fill_color='white', size=12)
    p.circle('week', f'{stat}', 
             source=plot_df[(plot_df.team_name.isin(opps)) & (plot_df.opponent_team_name  == plot_team)], 
             color='red', fill_color='white', size=12)
    
    legend = Legend(items=[
        LegendItem(label=plot_team, renderers=[r], index=0),
        LegendItem(label=opps[-1], renderers=[r2], index=1),
        LegendItem(label=next_opp_name, renderers=[r3], index=1)        
    ])

    p.add_tools(HoverTool(
        tooltips=[
            ('Team', '@team_name'),
            (f'{stat}', f'@{stat}')
        ]
    ))

    p.add_layout(legend)
    p.xaxis.ticker = plot_df.week.unique()
    p.legend.click_policy="hide"
    
    if save_filepath:
        print('Saving to', save_filepath)
        bokeh.plotting.output_file(save_filepath)
        show(p)
    else:
        show(p)
    return p

plot_list = []
for category in ['FG_PCT', 'FT_PCT', '3PTM', 'PTS', 'REB', 'AST', 'ST', 'BLK', 'TO']:
    p = plot_weekly_stats(plot_df=df, stat=category, 
                          next_opp_id=next_week_opp_id[-1], 
                          next_opp_name=next_week_opp_name)
    plot_list.append(p)


bokeh.plotting.output_file('index.html')
show(bokeh.layouts.gridplot(plot_list, ncols=2))




