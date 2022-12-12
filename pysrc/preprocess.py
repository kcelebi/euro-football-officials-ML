import numpy as np
import pandas as pd
import lxml.etree as etree
import sqlite3 as sql

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

        self.foul_df = self.getFoulDF()
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

    def getFoulDF(self):
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
        if self.foul_df is not None:
            xml = self.foul_df['foulcommit'].iloc[index]
            match_id = self.foul_df['match_api_id'].iloc[index]
            root = etree.fromstring(xml)
            unique_elems = []
            for child in root:
                if child[0][0].tag not in unique_elems:
                    unique_elems += [child[0][0].tag]

                for child1 in child[1:]:
                    if child1.tag not in unique_elems:
                        unique_elems += [child1.tag]
            unique_elems

            d = {'match_id': []}
            for elem in unique_elems:
                d[elem] = []

            for i, child in enumerate(root):
                d['match_id'] += [match_id]
                d[child[0][0].tag] += [child[0][0].text]

                for child1 in child[1:]:
                    d[child1.tag] += [child1.text]

                key_lengths = [len(d[x]) for x in list(d.keys())]
                for x in list(d.keys()):
                    if len(d[x]) < max(key_lengths):
                        d[x] += [None]

            foul_df = pd.DataFrame(d)
            foul_df = foul_df.fillna({'elapsed_plus':0, 'player1' : -1, 'player2' : -1})
            foul_df['elapsed'] = pd.to_numeric(foul_df['elapsed'])
            foul_df['elapsed_plus'] = pd.to_numeric(foul_df['elapsed_plus'])
            foul_df['elapsed'] += foul_df['elapsed_plus']
            foul_df = foul_df.rename(columns = {'id' : 'foul_id'})
            foul_df = foul_df.drop(['elapsed_plus', 'n', 'sortorder'], axis = 1)
            foul_df = foul_df.astype({
                'foulscommitted' : 'int64',
                'event_incident_typefk' : 'int64',
                'player1' : 'int64',
                'player2' : 'int64',
                'team' : 'int64',
                'foul_id' : 'int64'
            })

            ## Fouls unravelled, now time to merge main df with it
            foul_df = pd.merge(
                self.foul_df.drop('foulcommit', axis = 1), foul_df,
                how = 'inner', left_on = 'match_api_id', right_on = 'match_id'
            )

            player_columns = ['player_api_id', 'player_name']
            df2 = pd.merge(foul_df, self.player[player_columns], left_on = 'player1', right_on = 'player_api_id')
            df2 = df2.rename(columns = {'player_name' : 'player1_name'})

            df3 = pd.merge(df2, self.player[player_columns], left_on = 'player2', right_on = 'player_api_id')
            df3 = df3.rename(columns = {'player_name' : 'player2_name'})

            columns = [
                'match_api_id',
                'date',
                'home_team_api_id',
                'home_team_name',
                'away_team_api_id',
                'away_team_name',
                'card', 'corner',
                'foulscommitted',
                'event_incident_typefk',
                'elapsed',
                'player1_name',
                'player2_name',
                'team',
                'type',
                'subtype',
                'foul_id']

            return df3[columns]

        return None

    '''
    	ss
    '''
    def unravelCardDF(self, index):
        xml = self.foul_df['card'].iloc[index]
        match_id = self.foul_df['match_api_id'].iloc[index]
        root = etree.fromstring(xml)
        unique_elems = []
        for child in root:
            if child[0].tag not in unique_elems:
                unique_elems += [child[0].tag]
            if child[1][0].tag not in unique_elems:
                unique_elems += [child[1][0].tag]
            for child1 in child[2:]:
                if child1.tag not in unique_elems:
                    unique_elems += [child1.tag]
        unique_elems

        d = {'match_id': []}
        for elem in unique_elems:
            d[elem] = []

        for i, child in enumerate(root):
            d['match_id'] += [match_id]
            d[child[0].tag] += [child[0].text]
            d[child[1][0].tag] += [child[1][0].text]

            for child1 in child[2:]:
                d[child1.tag] += [child1.text]

            key_lengths = [len(d[x]) for x in list(d.keys())]
            for x in list(d.keys()):
                if len(d[x]) < max(key_lengths):
                    d[x] += [None]

        card_df = pd.DataFrame(d)
        card_df['elapsed'] = pd.to_numeric(card_df['elapsed'])
        card_df = card_df.rename({'id' : 'card_id'})
        card_df = card_df.drop(['n', 'sortorder'], axis = 1)
        return card_df