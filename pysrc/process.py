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


    def unravelFoulDF(self, index):
        columns = ['subtype','team']
        xml = self.match_team['foulcommit'].iloc[index]
        match_id = self.match_team['match_api_id'].iloc[index]
        
        foul_df = None
        if xml != '<foulcommit />':
            foul_df = pd.read_xml(xml)
        else:
            return pd.DataFrame()

        for col in columns:
            if col not in foul_df.columns:
                foul_df[col] = [None] * foul_df.shape[0]

        foul_df = foul_df[columns]
        foul_df['match_id'] = [match_id] * foul_df.shape[0]

        foul_df = foul_df.rename(columns = {
            'subtype' : 'foul_reason',
            'team' : 'fouling_team'
        })

        

    def unravelCardDF(self, index):
        columns = [
            'match_id',
            'card_type',
            'subtype',
            'team'
        ]
        xml = self.match_team['card'].iloc[index]
        match_id = self.match_team['match_api_id'].iloc[index]
        
        foul_df = None
        if xml != '<card />':
            foul_df = pd.read_xml(xml)
        else:
            return pd.DataFrame()

        for col in columns:
            if col not in card_df.columns:
                card_df[col] = [None] * card_df.shape[0]

        card_df = card_df[columns]
        card_df['match_id'] = [match_id] * card_df.shape[0]

        card_df = card_df.rename(columns = {
            'subtype' : 'card_reason',
            'card_type' : 'card_color',
            'team' : 'carded_team'
        })

        return card_df




