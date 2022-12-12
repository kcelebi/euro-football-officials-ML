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

        #self.card_df = self.getCardDF()

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


    def unravel(self):
        columns = [
            'match_api_id',
            'date',
            'home_team_name',
            'away_team_name',
            'foul_id',
            'event_incident_typefk_foul',
            'elapsed_foul',
            'player1_name',
            'player2_name',
            'foul_team',
            'foul_type',
            'foul_subtype'
            'event_incident_typefk_card',
            'ycards',
            'elapsed_card',
            'player_card',
            'card_team',
            'card_type',
            'card_subtype',
            'comment'
        ]
        df = self.match_team.copy(deep = True)
        for i in tqdm(range(df.shape[0])):
            df = pd.merge(df, self.unravelFoulDF(i), how = 'left', left_on = 'match_api_id', right_on = 'match_id')
            df = df.drop(['match_id'], axis = 1)
            df = pd.merge(df, self.unravelCardDF(i), how = 'left', left_on = 'match_api_id', right_on = 'match_id')
            df = df.drop(['match_id'], axis = 1)
        return df[columns]

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

            join = pd.merge_asof(
                df1, self.unravelCardDF(i),
                left_on = 'elapsed_foul',
                right_on = 'card_elapsed',
                left_by = 'foul_player1_id',
                right_by = 'card_player_id',
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
    	Unravel foul XML in foulcommits column for the foul_df table.
    '''
    def unravelFoulDF(self, index):
        if self.match_team is not None:
            xml = self.match_team['foulcommit'].iloc[index]
            match_id = self.match_team['match_api_id'].iloc[index]
            root = etree.fromstring(xml)
            unique_elems = []
            for child in root:
                if len(child[0]) != 0 and child[0][0].tag not in unique_elems:
                    unique_elems += [child[0][0].tag]
                
                if len(child[0]) != 0:
                    for child1 in child[1:]:
                        if child1.tag not in unique_elems:
                            unique_elems += [child1.tag]
                else:
                    for child1 in child:
                        if child1.tag not in unique_elems:
                            unique_elems += [child1.tag]
            unique_elems

            d = {'match_id': []}
            for elem in unique_elems:
                d[elem] = []

            for i, child in enumerate(root):
                d['match_id'] += [match_id]
                
                if len(child[0]) != 0:
                    d[child[0][0].tag] += [child[0][0].text]
                    for child1 in child[1:]:
                        d[child1.tag] += [child1.text]
                else:
                    for child1 in child:
                        d[child1.tag] += [child1.text]

                key_lengths = [len(d[x]) for x in list(d.keys())]
                for x in list(d.keys()):
                    if len(d[x]) < max(key_lengths):
                        d[x] += [None]

            foul_df = pd.DataFrame(d)
            foul_df = foul_df.fillna({'elapsed_plus':0, 'player1' : -1, 'player2' : -1, 'foulscommitted' : 1})
            foul_df['elapsed'] = pd.to_numeric(foul_df['elapsed'])
            if 'elapsed_plus' in foul_df.columns:
                foul_df['elapsed_plus'] = pd.to_numeric(foul_df['elapsed_plus'])
                foul_df['elapsed'] += foul_df['elapsed_plus']
                foul_df = foul_df.drop('elapsed_plus', axis = 1)
            foul_df = foul_df.rename(columns = {
                'id' : 'foul_id',
                'event_incident_typefk' : 'event_incident_typefk_foul',
                'elapsed' : 'elapsed_foul',
                'type' : 'foul_type',
                'subtype' : 'foul_subtype',
                'team' : 'foul_team'
            })
            foul_df = foul_df.drop(['n', 'sortorder'], axis = 1)
            foul_df = foul_df.astype({
                'foulscommitted' : 'int64',
                'event_incident_typefk_foul' : 'int64',
                'player1' : 'int64',
                'player2' : 'int64',
                'foul_team' : 'int64',
                'foul_id' : 'int64'
            })

            ## Fouls unravelled, now time to merge main df with it
            player_columns = ['player_api_id', 'player_name']
            df2 = pd.merge(foul_df, self.player[player_columns], left_on = 'player1', right_on = 'player_api_id')
            df2 = df2.rename(columns = {'player_name' : 'foul_player1', 'player_api_id' : 'foul_player1_id'})

            df3 = pd.merge(df2, self.player[player_columns], left_on = 'player2', right_on = 'player_api_id')
            df3 = df3.rename(columns = {'player_name' : 'foul_player2', 'player_api_id' : 'foul_player2_id'})

            foul_df = df3.sort_values(by = 'elapsed_foul')

            columns = [
                'match_id',
                'foul_id',
                'foulscommitted',
                'event_incident_typefk_foul',
                'elapsed_foul',
                'foul_player1',
                'foul_player2',
                'foul_player1_id',
                'foul_player2_id',
                'foul_team',
                'foul_type',
                'foul_subtype'
            ]

            return foul_df[columns]

        return None

    '''
    	ss
    '''
    def unravelCardDF(self, index):
        xml = self.match_team['card'].iloc[index]
        match_id = self.match_team['match_api_id'].iloc[index]
        root = etree.fromstring(xml)
        
        keys_d = [
            'elapsed','match_id', 'id','foulscommitted','event_incident_typefk','player1', 
            'team','type','subtype','ycards','rcards','comment', 'n', 'sortorder', 'card_type'
        ]
        unique_elems = []
        for child in root:
            if child[0].tag not in unique_elems and child[0].tag not in keys_d:
                unique_elems += [child[0].tag]
            if child[1].tag == 'stats' and child[1][0].tag not in unique_elems and child[1][0].tag not in keys_d:
                unique_elems += [child[1][0].tag]
            elif child[1].tag != 'stats':
                for child1 in child[1:]:
                    if child1.tag not in unique_elems and child1.tag not in keys_d and child1.tag != 'del':
                        unique_elems += [child1.tag]
        
            for child1 in child[2:]:
                if child1.tag not in unique_elems and child1.tag not in keys_d:
                    unique_elems += [child1.tag]

        d = {}
        for k in keys_d:
            d[k] = []

        for elem in unique_elems:
            d[elem] = []

        for i, child in enumerate(root):
            d['match_id'] += [match_id]
            d[child[0].tag] += [child[0].text]
    
            if child[1].tag == 'stats':
                d[child[1][0].tag] += [child[1][0].text]

                for child1 in child[2:]:
                    d[child1.tag] += [child1.text]
            else:
                for child1 in child[1:]:
                    if child1.tag != 'del':
                        d[child1.tag] += [child1.text]

            key_lengths = [len(d[x]) for x in list(d.keys())]
            for x in list(d.keys()):
                if len(d[x]) < max(key_lengths):
                    d[x] += [None]

        card_df = pd.DataFrame(d)#.drop('del', axis = 1)
        if 'del' in card_df.columns:
            card_df = card_df.drop('del', axis = 1)

        if card_df.shape[0] != 0:
            card_df = card_df.fillna({'ycards' : 0, 'rcards' : 0, 'elapsed_plus' : 0})
            card_df['elapsed'] = pd.to_numeric(card_df['elapsed'])
            if 'elapsed_plus' in card_df.columns:
                card_df['elapsed_plus'] = pd.to_numeric(card_df['elapsed_plus'])
                card_df['elapsed'] += card_df['elapsed_plus']
                card_df = card_df.drop('elapsed_plus', axis = 1)
            card_df = card_df.rename(columns = {
                'id' : 'card_id',
                'event_incident_typefk' : 'event_incident_typefk_card',
                'elapsed' : 'card_elapsed',
                'player1' : 'card_player',
                'team' : 'card_team',
                'card_type' : 'card_color',
                'type' : 'card_type',
                'subtype' : 'card_subtype'
                })
            card_df = card_df.astype({
                'card_player' : int,
                'card_team' : int,
                'card_id' : int,
                'ycards' : int,
                'rcards' : int,
                'event_incident_typefk_card' : int
                })
            card_df = card_df.drop(['n', 'sortorder'], axis = 1)

            player_columns = ['player_api_id', 'player_name']
            card_df = pd.merge(card_df, self.player[player_columns], how = 'inner', left_on = 'card_player', right_on = 'player_api_id')

            card_df = card_df.drop(['card_player'], axis = 1)

            card_df = card_df.rename(columns = {'player_name' : 'card_player', 'player_api_id' : 'card_player_id'})

            card_df = card_df.sort_values(by = 'card_elapsed')

            #card_df = card_df.fillna({'player1' : -1})
            '''card_df = card_df.astype({
                'ycards' : 'int64',
                'event_incident_typefk' : 'int64',
                'player1' : 'int64',
                'team' : 'int64',
                'card_id' : 'int64'
            })'''

        else:
            # Edge case of no cards
            card_df['match_id'] = [self.match_team['match_api_id'].iloc[index]]
            card_df = card_df.drop(['n', 'sortorder'], axis = 1)
            card_df['card_player_id'] = [-1]
            card_df = card_df.rename(columns = {
                'id' : 'card_id',
                'event_incident_typefk' : 'event_incident_typefk_card',
                'elapsed' : 'card_elapsed',
                'player1' : 'card_player',
                'team' : 'card_team',
                'card_type' : 'card_color',
                'type' : 'card_type',
                'subtype' : 'card_subtype'
            })
            card_df = card_df.fillna({
                'ycards' : 0,
                'rcards' : 0,
                'card_elapsed' : 0,
                'card_id' : -1,
                'card_player' : -1
            })
            card_df = card_df.astype({
                'card_player_id' : int,
                #'card_team' : int,
                'card_id' : int,
                'ycards' : int,
                'rcards' : int,
                'card_elapsed' : int
                #'event_incident_typefk_card' : int
            })



            #card_df = card_df.sort_by(by  = 'card_elapsed')

        
        return card_df