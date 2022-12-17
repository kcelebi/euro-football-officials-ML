import numpy as np
import pandas as pd
import lxml.etree as etree
import sqlite3 as sql
from tqdm.notebook import tqdm
import matplotlib.pyplot as plt

from sklearn.metrics import (
    precision_recall_fscore_support,
    confusion_matrix,
    ConfusionMatrixDisplay,
    precision_score, recall_score
    )
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

__all__ = ['DB', 'CM', 'metric_suite', 'transform_target', 'RFpipe', 'RFinterpipe', 'Logitpipe', 'train_test']

'''
    dfghjkl;
'''
def metric_suite(clf, X, y_true, labels = ['W' , 'D', 'L'], type_ = '', cm = True, save = None):
    y_pred = clf.predict(X)

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true = y_true, y_pred = y_pred, labels = labels, zero_division = 0
    )

    metrics = {
        'Class' : labels + ['Total'],
        'Accuracy' : [np.mean(y_pred[y_true == x] == y_true[y_true == x]) for x in labels] + [np.mean(y_pred == y_true)],
        'Precision' : list(precision) + [np.dot(precision, support)/np.sum(support)],
        'Recall' : list(recall) + [np.dot(recall, support)/np.sum(support)],
        'F1' : list(f1) + [np.dot(f1, support)/np.sum(support)],
        'Support' : list(support) + [np.sum(support)]
    }

    if cm:
        CM(y_pred = y_pred, y_true = y_true, type_ = type_, labels = labels, save = save)

    return pd.DataFrame(metrics)

'''
    dfrtgyuio
'''
def CM(y_pred, y_true, type_ = '', labels = ['W', 'D', 'L'], save = None):
    fig, axs = plt.subplots(1, 2, figsize = (15, 5))

    cm = confusion_matrix(y_true = y_true, y_pred = y_pred, labels = labels)#, normalize = 'true')
    disp = ConfusionMatrixDisplay(
        confusion_matrix = cm,
        display_labels = labels
    )
    disp.plot(cmap =  plt.cm.Blues, ax = axs[0])
    
    axs[0].set(title = type_ + ' Accuracy: ' + str(round(np.mean(y_pred == y_true),2)))
    
    cm = confusion_matrix(y_true = y_true, y_pred = y_pred, labels = labels, normalize = 'true')    
    disp = ConfusionMatrixDisplay(
        confusion_matrix = cm,
        display_labels = labels
    )
    disp.plot(cmap =  plt.cm.Blues, ax = axs[1])
    
    axs[1].set(title = type_ + ' Normalized')

    if save != None:
        plt.savefig(save, dpi = 200)

    plt.show()

def transform_target(X, y, class_labels = ['W', 'D', 'L'], weight = True, down_sample = True):
    if weight and down_sample:
        size = np.min(np.unique(pd.concat([y[y == x] for x in class_labels]), return_counts = True)[1])
        idx = [np.random.choice(y[y == x].index.values, size = size) for x in class_labels]
        down_idx = np.concatenate(idx)
        weights = {}
        for class_ in class_labels:
            weights[class_] = y[y == class_].shape[0]/size

        return X.iloc[down_idx], y[down_idx], weights
    elif weight and not down_sample:
        size = np.max(np.unique(pd.concat([y[y == x] for x in class_labels]), return_counts = True)[1])
        weights = {}
        for i, class_ in enumerate(class_labels):
            weights[class_] = size/y[y == class_].shape[0]
        return X, y, weights
    else:
        y_ = pd.concat([y[y == x] for x in class_labels])
        return X.iloc[y_.index], y_, None

def RFpipe(weights = None, params = {}):
    return Pipeline(steps = [
        ('scaler', StandardScaler()),
        ('rf', RandomForestClassifier(class_weight = weights, **params))
    ])

def RFinterpipe(weights = None, params = {}):
    return Pipeline(steps = [
        ('scaler', StandardScaler()),
        ('inter', PolynomialFeatures(2, interaction_only = True, include_bias = False)),
        ('rf', RandomForestClassifier(class_weight = weights, **params))
    ])

def Logitpipe(weights = None, params = {}):
    return Pipeline(steps = [
        ('scaler', StandardScaler()),
        ('logit', LogisticRegression(class_weight = weights, **params))
    ])

def train_test(func, X, y, weight, down_sample, class_labels = ['W', 'D', 'L'], cm = False, seed = None, return_clf = False):
    if seed != None:
        np.random.seed(seed)
    X_ds, y_ds, weights = transform_target(X, y, class_labels = class_labels, weight = weight, down_sample = down_sample)
    X_train, X_test, y_train, y_test = train_test_split(X_ds, y_ds, test_size = 0.2, stratify = y_ds)

    print('>>>Preprocess done', weights)

    clf = func(weights = weights).fit(X_train, y_train)
    print(metric_suite(clf, X_train, y_train, labels = class_labels, cm = cm))
    print(metric_suite(clf, X_test, y_test, labels = class_labels, cm = cm))
    
    if return_clf:
        return clf, X_train, X_test, y_train, y_test


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

    def joinMatchTeamDF(self):
        columns = [
            'match_api_id','league_id', 'date',
            'home_team_api_id', 'away_team_api_id',
            'home_team_goal', 'away_team_goal',
            'foulcommit', 'card', 'corner'
        ]
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
            'match_api_id', 'league_id', 'date',
            'home_team_api_id', 'home_team_name',
            'away_team_api_id', 'away_team_name',
            'home_team_goal', 'away_team_goal',
            'foulcommit', 'card', 'corner'
        ]

        return m2[final_columns]


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

        return foul_df


    def stackFoulCardDF(self, custom_range = None):
        if custom_range == None:
            custom_range = range(self.match_team.shape[0])

        df_card = pd.concat(
            [pd.get_dummies(self.unravelCardDF(x), columns = ['card_color', 'card_reason']) for x in tqdm(custom_range, desc = 'Stacking Cards') if self.unravelCardDF(x).shape[0] > 0]
        ).groupby(by = ['match_id', 'carded_team'], as_index = False).sum()

        df_foul = pd.concat(
            [pd.get_dummies(self.unravelFoulDF(x), columns = ['foul_reason']) for x in tqdm(custom_range, desc = 'Stacking Fouls') if self.unravelFoulDF(x).shape[0] > 0]
        ).groupby(by = ['match_id', 'fouling_team'], as_index = False).sum()

        df = pd.merge(self.match_team, df_card, left_on = 'match_api_id', right_on = 'match_id').drop(['match_id'], axis = 1)
        df = pd.merge(df, df_foul, left_on = 'match_api_id', right_on = 'match_id').drop(['match_id'], axis = 1)
        df = df.drop(['foulcommit', 'card', 'corner'], axis = 1)

        return df


    def unravelCardDF(self, index):
        columns = [
            'match_id',
            'card_type',
            'subtype',
            'team'
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
                card_df[col] = [None] * card_df.shape[0]

        card_df = card_df[columns]
        card_df['match_id'] = [match_id] * card_df.shape[0]

        card_df = card_df.rename(columns = {
            'subtype' : 'card_reason',
            'card_type' : 'card_color',
            'team' : 'carded_team'
        })

        return card_df




