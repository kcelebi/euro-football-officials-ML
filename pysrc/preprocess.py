import numpy as np
import pandas as pd
import lxml.etree as etree
import sqlite3 as sql

__all__ = ['unravel_fouls', 'unravel_cards']



def create_connection(db):
	con = sql.connect(db)
	df_match = pd.read_sql_query('SELECT * FROM Match', con)
	df_team = pd.read_sql_query('SELECT * FROM Team', con)
	
'''
	ss
'''
def unravel_fouls(index):
    xml = fouls_teams['foulcommit'].iloc[index]
    match_id = fouls_teams['match_api_id'].iloc[index]
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
    foul_df = foul_df.fillna({'elapsed_plus':0})
    foul_df['elapsed'] = pd.to_numeric(foul_df['elapsed'])
    foul_df['elapsed_plus'] = pd.to_numeric(foul_df['elapsed_plus'])
    foul_df['elapsed'] += foul_df['elapsed_plus']
    foul_df = foul_df.rename({'id' : 'foul_id'})
    foul_df = foul_df.drop(['elapsed_plus', 'n', 'sortorder'], axis = 1)
    return foul_df

'''
	ss
'''
def unravel_cards(index):
    xml = fouls_teams['card'].iloc[index]
    match_id = fouls_teams['match_api_id'].iloc[index]
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