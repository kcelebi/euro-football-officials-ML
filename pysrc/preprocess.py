import numpy as np
import pandas as pd
import lxml.etree as etree
import sqlite3 as sql
from tqdm.notebook import tqdm

__all__ = ['DB']

class DB:

    '''
        DB object to make manipulation cleaner. Creates connection and implements function
        to make access cleaner.

        Args:
            db_route: File route to db.sqlite file
    '''
    def __init__(self, db_route):
        self.db_route = db_route
        self.con = self.create_connection(self.db_route)
        self.match = self.getDF('Match')
        self.team = self.getDF('Team')
        self.team_attr = self.getDF('Team_Attributes')
        self.league = self.getDF('League')
        self.player = self.getDF('Player')

        self.match_team = self.joinMatchTeamDF()

        self.foul_columns = [
            'elapsed', 'elapsed_plus',
            'event_incident_typefk', 'id',
            'injury_time','player1',
            'player2','subtype',
            'team','type'
        ]

        self.foul_columns_final  = [
            'match_id', 'elapsed_foul',
            'event_incident_typefk_foul', 'foul_id',
            'injury_time', 'player1_id_foul',
            'player2_id_foul', 'subtype',
            'type', 'team',
            'player1_name_foul', 'player2_name_foul'
        ]

        self.card_columns = [
            'match_id','card_type',
            'elapsed','elapsed_plus',
            'event_incident_typefk','goal_type',
            'id','player1',
            'subtype','team',
            'type'
        ]


    '''
        Creates SQL db connection to db.sqlite file
        Args:
            db_route: Route to db.sqlite file
        Returns:
            SQL connection, saves to class object
    '''
    def create_connection(self, db_route):
    	return sql.connect(db_route)
    	#df_match = pd.read_sql_query('SELECT * FROM Match', con)
    	#df_team = pd.read_sql_query('SELECT * FROM Team', con)

    '''
        Creates Pandas Dataframe from SQL connection in db.sqlite file from requested name.
        Args:
            df_name: Name of table as it appears in sqlite
        Returns:
            Pandas dataframe of requested table
    '''
    def getDF(self, df_name):
        return pd.read_sql_query('SELECT * FROM %s' % df_name, self.con)


    '''
        Combining unravels
    '''
    def combineCardFoulDF(self):
        df = pd.DataFrame()
        for i in tqdm(range(self.match_team.shape[0])):
            base_elapsed = pd.DataFrame({'elapsed_foul' : list(range(120))})
            df1 = pd.merge(base_elapsed, self.unravelFoulDF(i), how = 'left', on = 'elapsed_foul')
            for key in list(df1.dtypes.keys()):
                if df1.dtypes[key] == np.dtype('float64'):
                    if key == 'match_id':
                        mid = df1[~df1['match_id'].isna()]['match_id'].iloc[0]
                        df1 = df1.fillna({key : mid}).astype({str(key) : int})
                    df1 = df1.fillna({key : 0}).astype({str(key) : int})


            # Edge case of no fouls
            if self.unravelCardDF(i).shape[0] > 0:
                join = pd.merge_asof(
                    df1, self.unravelCardDF(i),
                    left_on = 'elapsed_foul',
                    right_on = 'elapsed_card',
                    left_by = 'player1_id_foul',
                    right_by = 'player1_id_card',
                    direction = 'nearest',
                    tolerance = 2
                )
                join = join.drop('match_id_y', axis = 1).rename(columns = {'match_id_x': 'match_id'})
                join = join.reset_index(drop = True)
                df = pd.concat([df, join], ignore_index = True)

        return df


    def joinMatchTeamDF(self):
        columns = ['match_api_id','date','home_team_api_id', 'away_team_api_id', 'foulcommit', 'card', 'corner']
        short_match = self.match.dropna(subset = ['foulcommit'])[columns]
        short_team = self.team[['team_api_id', 'team_long_name']]
        m1 = pd.merge(
            short_match, short_team,
            how = 'inner', left_on = 'home_team_api_id',
            right_on = 'team_api_id', suffixes = ("_x", "_y"))

        m2 = pd.merge(
            m1, short_team,
            how = 'inner', left_on = 'away_team_api_id',
            right_on = 'team_api_id', suffixes = ('_x', '_y'))


        m2 = m2.rename(columns = {
            'team_long_name_x' : 'home_team_name',
            'team_long_name_y' : 'away_team_name'
            }
        )

        final_columns = [
            'match_api_id', 'date',
            'home_team_api_id', 'home_team_name',
            'away_team_api_id', 'away_team_name',
            'foulcommit', 'card', 'corner'
        ]

        return m2[final_columns]

    '''
        Unravel
    '''
    def unravelFoulDF(self, index):
        xml = self.match_team['foulcommit'].iloc[index]
        match_id = self.match_team['match_api_id'].iloc[index]
        
        foul_df = None
        if xml != '<foulcommit />':
            foul_df = pd.read_xml(xml)
        else:
            return pd.DataFrame(columns = self.foul_columns_final)

        for col in self.foul_columns:
            if col not in foul_df.columns:
                foul_df[col] = [None]*foul_df.shape[0]

        foul_df = foul_df[self.foul_columns]
        foul_df['match_id'] = [match_id] * foul_df.shape[0]

        foul_df = foul_df.fillna(0)#({'elapsed_plus' : 0, 'player2' : 0, 'player1' : 0})
        foul_df = foul_df.astype({
            'elapsed': int,
            'elapsed_plus' : int,
            'player1' : int,
            'player2' : int
        })
        foul_df['elapsed'] += foul_df['elapsed_plus']
        foul_df = foul_df.drop('elapsed_plus', axis = 1)

        foul_df = pd.merge(foul_df,
            self.player[['player_api_id', 'player_name']],
            how = 'left', left_on = 'player1', right_on = 'player_api_id'
        ).drop('player_api_id', axis = 1).rename(columns = {'player_name' : 'player1_name_foul'})

        foul_df = pd.merge(foul_df,
            self.player[['player_api_id', 'player_name']],
            how = 'left', left_on = 'player2', right_on = 'player_api_id'
        ).drop('player_api_id', axis = 1).rename(columns = {'player_name' : 'player2_name_foul'})

        foul_df = foul_df.rename(columns = {
            'elapsed' : 'elapsed_foul',
            'player1' : 'player1_id_foul',
            'player2' : 'player2_id_foul',
            'id' : 'foul_id',
            'event_incident_typefk' : 'event_incident_typefk_foul'
        })

        foul_df = foul_df.sort_values(by = 'elapsed_foul').fillna(0)

        return foul_df


    '''
        Unravel
    '''
    def unravelCardDF(self, index):
        columns = [
            'match_id',
            'card_type',
            'elapsed',
            'elapsed_plus',
            'event_incident_typefk',
            'goal_type',
            'id',
            'player1',
            'subtype',
            'team',
            'type'
        ]
        xml = self.match_team['card'].iloc[index]
        match_id = self.match_team['match_api_id'].iloc[index]
        
        card_df = None
        if xml != '<card />':
            card_df = pd.read_xml(xml)
        else:
            return pd.DataFrame()

        for col in columns:
            if col not in card_df.columns:
                card_df[col] = [None]*card_df.shape[0]

        card_df = card_df[columns]
        card_df['match_id'] = [match_id] * card_df.shape[0]

        #card_df = card_df.fillna({'elapsed_plus' : 0}).astype({'elapsed': int, 'elapsed_plus' : int})
        card_df = card_df.fillna(0).astype({'elapsed': int, 'elapsed_plus' : int})
        card_df['elapsed'] += card_df['elapsed_plus']
        card_df = card_df.drop('elapsed_plus', axis = 1)

        card_df = card_df.rename(columns = {
            'elapsed' : 'elapsed_card',
            'event_incident_typefk' : 'event_incident_typefk_card',
            'id' : 'card_id',
            'player1' : 'player1_id_card',
            'subtype' : 'card_subtype',
            'card_type' : 'card_color',
            'type' : 'card_type',
            'team' : 'team_card'
        })

        card_df = card_df.astype({
            'player1_id_card' : int
        })

        return card_df.sort_values(by = 'elapsed_card')