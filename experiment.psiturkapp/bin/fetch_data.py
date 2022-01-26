#!/usr/bin/env python2

import os
import logging
import urllib2
import pandas as pd
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import ast
import re
import json
from collections import defaultdict

logging.basicConfig(level="INFO")

def to_snake_case(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub(r'[.:\/]', '_', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


class Labeler(object):
    """Assigns unique integer labels."""
    def __init__(self, init=()):
        self._labels = {}
        self._xs = []
        for x in init:
            self.label(x)

    def label(self, x):
        if x not in self._labels:
            self._labels[x] = len(self._labels)
            self._xs.append(x)
        return self._labels[x]

    def unlabel(self, label):
        return self._xs[label]

    __call__ = label

def add_auth(url, username, password):
    """Add HTTP authencation for opening urls with urllib2.

    Based on http://www.voidspace.org.uk/python/articles/authentication.shtml
    """
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()

    # because we have put None at the start it will always use this
    # username/password combination for urls for which `theurl` is a super-url
    passman.add_password(None, url, username, password)

    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)

    # All calls to urllib2.urlopen will now use our handler. Make sure not to
    # include the protocol in with the URL, or HTTPPasswordMgrWithDefaultRealm
    # will be very confused.  You must (of course) use it when fetching the
    # page though.
    opener = urllib2.build_opener(authhandler)
    urllib2.install_opener(opener)


def fetch(site_root, filename, version, force=True):
    """Download `filename` from `site_root` and save it in the
    data/human_raw/`version` data folder.
    """
    url = os.path.join(site_root, version, filename)

    # get the destination to save the data, and don't do anything if
    # it exists already
    dest = os.path.join('data/human_raw', version, "{}.csv".format(os.path.splitext(filename)[0]))
    if os.path.exists(dest) and not force:
        print('{} already exists. Use --force to overwrite.'.format(dest))
        return

    # download the data
    try:
        handler = urllib2.urlopen(url)
    except IOError as err:
        if getattr(err, 'code', None) == 401:
            logging.error("Server authentication failed.")
            raise err
        else:
            raise
    else:
        data = handler.read()
        logging.info("Fetched succesfully: %s", url)

    # write out the data file
    if not os.path.exists(os.path.dirname(dest)):
        os.makedirs(os.path.dirname(dest))
    with open(dest, "w") as fh:
        fh.write(data)
    logging.info("Saved to '%s'", os.path.relpath(dest))
    if filename == 'questiondata':
        df = pd.read_csv(dest, header=None)
        n_pid = df[0].unique().shape[0]
        logging.info('Number of participants: %s', n_pid)


def reformat_data(version):
    data_path = 'data/human_raw/{}/'.format(version)
    pid_labeler = Labeler()
    identifiers = {'worker_id': [], 'assignment_id': [], 'pid': []}

    # Create participants dataframe (pdf).
    def parse_questiondata():
        qdf = pd.read_csv(data_path + 'questiondata.csv', header=None)
        for uid, df in qdf.groupby(0):
            try:
                row = ast.literal_eval(list(df[df[1] == 'params'][2])[0])
            except:
                row = {}
            wid, aid = uid.split(':')
            identifiers['worker_id'].append(wid)
            identifiers['assignment_id'].append(aid)
            identifiers['pid'].append(pid_labeler(wid))
            row['pid'] = pid_labeler(wid)

            completed_row = df[df[1] == 'completed']
            if len(completed_row):
                assert len(completed_row) == 1
                row['completed'] = True
                data = ast.literal_eval(completed_row[2].iloc[0])
                for k, v in data.items():
                    print(k, v)
                    row[k] = v
            else:
                bonus_row = df[df[1] == 'final_bonus']
                if len(bonus_row):
                    bonus = float(list(bonus_row[2])[0])
                    row['bonus'] = bonus
                    row['completed'] = True
                else:
                    row['bonus'] = 0
                    row['completed'] = False
            yield row

    pdf = pd.DataFrame(parse_questiondata())
    pdf['version'] = version
    idf = pd.DataFrame(pd.DataFrame(identifiers).set_index('pid'))
    idf.to_csv(data_path + 'identifiers.csv')

    # Create trials dataframe (tdf).
    def parse_trialdata():
        tdf = pd.read_csv(data_path + 'trialdata.csv', header=None)
        tdf = pd.DataFrame.from_records(tdf[3].apply(json.loads)).join(tdf[0])
        wids = tdf[0].apply(lambda x: x.split(':')[0])
        tdf['pid'] = wids.apply(pid_labeler)
        return tdf.drop(0, axis=1)

    tdf = parse_trialdata()

    # Split tdf into separate dataframes for each type of trial.
    data = {'participants': pdf}
    for trial_type, df in tdf.groupby('trial_type'):
        # df = df.dropna(axis=1)
        df = df.drop('internal_node_id', axis=1)
        df = df.drop('trial_index', axis=1)
        df.columns = [to_snake_case(c) for c in df.columns]
        data[trial_type] = df


    # Write data.
    path = 'data/human/{}/'.format(version)
    if not os.path.isdir(path):
        os.makedirs(path)
    for name, df in data.items():
        dest = path + name + '.csv'
        df.to_csv(dest, index=False)
        print('wrote {} with {} rows.'.format(dest, len(df)))

    return data

def main(version, address, username, password):
    add_auth(address, username, password)
    files = ["trialdata", "eventdata", "questiondata"]
    for filename in files:
        fetch(address, filename, version)


if __name__ == "__main__":
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "version",
        help=("Experiment version. This corresponds to the experiment_code_version "
              "parameter in the psiTurk config.txt file that was used when the "
              "data was collected."))

    url = "https://ball-exp.herokuapp.com/data"
    if url == "https://ball-exp.herokuapp.com/data":
        print('Set the URL in this file before usage. Then delete this ')
        exit(1)

    args = parser.parse_args()
    main(args.version, url, 'user', 'pw')  # from config.txt
