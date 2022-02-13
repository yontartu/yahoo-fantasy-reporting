#!/usr/bin/env python
# coding: utf-8
# %%
import pandas as pd
import numpy as np
import datetime
import json
import bokeh
import pretty_errors
from bokeh.plotting import figure, output_notebook, show#, vplot
from bokeh.palettes import Spectral11
from bokeh.models import Legend, LegendItem
from bokeh.models.tools import HoverTool
output_notebook()

import nba_api
from nba_api.stats.endpoints import ScoreboardV2
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa

# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText

# %%
def authenticate_yahoo(run_on_gh=True):
    if run_on_gh:
        sc = OAuth2(None, None, from_file='/home/runner/secrets/yahoo_creds.json')
        print('sc:', sc)
    else:  # run locally
        sc = OAuth2(None, None, from_file='yahoo_creds.json')
        print('sc:', sc)
    return sc


# %%
sc = authenticate_yahoo()


# %%
gm = yfa.Game(sc, 'nba')
gm.league_ids(year=2021)


# %%
# set constants
LEAGUE_ID = '410.l.21086'
TEAM_NAME = 'Backpack Kids'  
TEAM_ID = '410.l.21086.t.8'


# %%
lg = gm.to_league(LEAGUE_ID)
lg.stat_categories()

# %%
joeys_team = lg.to_team(TEAM_ID)
joeys_team


# %%
joeys_team.roster()


# %% [markdown]
# #### Games in the next week

# %%
free_agents = pd.DataFrame()

for pos in ['G', 'F', 'C']:
    new_df = pd.DataFrame(lg.free_agents(position=pos))
    free_agents = pd.concat([free_agents, new_df], sort=False)

free_agents = free_agents.drop_duplicates(subset=['player_id'])
free_agents = free_agents.sort_values('percent_owned', ascending=False)
free_agents = free_agents.reset_index(drop=True)
print(free_agents.shape)
free_agents.head()


# %%
def get_team_abbr(player_id):
    details = lg.player_details([player_id])
    return details[0]['editorial_team_abbr'].upper()


# %%
team_name_mapping = {
    'GS': 'GSW',
    'NO': 'NOP',
    'NY': 'NYK',
    'SA': 'SAS',
    'PHO': 'PHX'
}


# %%
free_agents['team'] = free_agents.player_id.apply(get_team_abbr)
free_agents.team = free_agents.team.replace(team_name_mapping)
free_agents


# %%
def get_games_next_week(weeks_forward=[1]):
    base_df = pd.DataFrame({'team': ['ATL', 'BOS', 'CHA', 'CHI', 'CLE', 'DAL', 'DET', 'GSW', 'HOU',
                                     'IND', 'LAC', 'LAL', 'MEM', 'MIL', 'MIN', 'NOP', 'NYK', 'OKC',
                                     'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'TOR', 'UTA', 'WAS', 'BKN',
                                     'DEN', 'MIA', 'SAS']})
    for w in weeks_forward:
        week_start = str(lg.week_date_range(week=lg.current_week() + w)[0])
        week_end = str(lg.week_date_range(week=lg.current_week() + w)[1])
        week_range = [str(x.date()) for x in (pd.date_range(week_start, week_end))]
        
        games = pd.DataFrame()
        for date in week_range:
            print(date)
            new_df = ScoreboardV2(game_date=date).get_data_frames()[0]
            games = pd.concat([games, new_df], sort=False)

        games['home_team'] = games.GAMECODE.str[-3:]
        games['visitor_team'] = games.GAMECODE.str[-6:-3]
        games = games[games.GAME_STATUS_TEXT != 'PPD']
        games = games.reset_index(drop=True)
        print(games.shape)
        
        home_games = games.groupby('home_team').size().reset_index()
        home_games.columns = ['team', 'home_games']

        visitor_games = games.groupby('visitor_team').size().reset_index()
        visitor_games.columns = ['team', 'visitor_games']

        games_next_week = pd.merge(home_games, visitor_games, how='outer', on='team')
        games_next_week = games_next_week.fillna(0)
        games_next_week[f'games_next_week_{week_start}'] = games_next_week.home_games + games_next_week.visitor_games
        games_next_week = games_next_week[['team', f'games_next_week_{week_start}']]
        
        base_df = pd.merge(base_df, games_next_week, how='left', on='team')
    return games_next_week


# %%
base_df = pd.DataFrame({'team': ['ATL', 'BOS', 'CHA', 'CHI', 'CLE', 'DAL', 'DET', 'GSW', 'HOU',
       'IND', 'LAC', 'LAL', 'MEM', 'MIL', 'MIN', 'NOP', 'NYK', 'OKC',
       'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'TOR', 'UTA', 'WAS', 'BKN',
       'DEN', 'MIA', 'SAS']})


# %%
plus_1 = 1

week_start = str(lg.week_date_range(week=lg.current_week() + plus_1)[0])
week_end = str(lg.week_date_range(week=lg.current_week() + plus_1)[1])
week_range = [str(x.date()) for x in (pd.date_range(week_start, week_end))]
week_range


# %%
games = pd.DataFrame()

for date in week_range:
    print(date)
    new_df = ScoreboardV2(game_date=date).get_data_frames()[0]
    games = pd.concat([games, new_df], sort=False)
    
games['home_team'] = games.GAMECODE.str[-3:]
games['visitor_team'] = games.GAMECODE.str[-6:-3]
games = games[games.GAME_STATUS_TEXT != 'PPD']
games = games.reset_index(drop=True)

print(games.shape)
games.head()


# %%
home_games = games.groupby('home_team').size().reset_index()
home_games.columns = ['team', 'home_games']

visitor_games = games.groupby('visitor_team').size().reset_index()
visitor_games.columns = ['team', 'visitor_games']

games_next_week = pd.merge(home_games, visitor_games, how='outer', on='team')
games_next_week = games_next_week.fillna(0)
games_next_week[f'games_next_week_{week_start}'] = games_next_week.home_games + games_next_week.visitor_games
games_next_week = games_next_week[['team', f'games_next_week_{week_start}']]
games_next_week.head()


# %%
free_agents_games = pd.merge(free_agents, games_next_week, how='left', on='team')
free_agents_games = free_agents_games[(free_agents_games[f'games_next_week_{week_start}'] == free_agents_games[f'games_next_week_{week_start}'].max()) &
                  (free_agents_games.percent_owned > 1)]
free_agents_games


# %%
games_next_week.to_csv('_games.csv', index=False)


# %%
free_agents_games.to_csv('_free_agents.csv', index=False)

# %% [markdown]
# #### Report on all currently injured players

# %%
taken_players = pd.DataFrame(lg.taken_players())
injuries = taken_players[taken_players.status.isin(['INJ', 'GTD', 'O'])].sort_values('percent_owned', ascending=False)
injuries['team'] = injuries.player_id.apply(get_team_abbr)
injuries.team = injuries.team.replace(team_name_mapping)
injuries = pd.merge(injuries, games_next_week, how='left', on='team')
injuries


# %%
injuries.to_csv('_injuries.csv', index=False)

# %% [markdown]
# #### My team's game outlook next week

# %%
roster = pd.DataFrame(joeys_team.roster(week=lg.current_week() + plus_1))
roster


# %%
roster['team'] = roster.player_id.apply(get_team_abbr)
roster.team = roster.team.replace(team_name_mapping)
roster_games = pd.merge(roster, games_next_week, how='left', on='team')
roster_games


# %%
roster_games.to_csv('_joeys_roster.csv', index=False)


# %%

# %%
