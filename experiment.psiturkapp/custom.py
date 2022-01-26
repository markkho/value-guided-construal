# this file imports custom routes into the experiment server

from flask import Blueprint, render_template, request, jsonify, Response, abort, current_app
from jinja2 import TemplateNotFound
from functools import wraps
from sqlalchemy import or_

from psiturk.psiturk_config import PsiturkConfig
from psiturk.experiment_errors import ExperimentError, InvalidUsage
from psiturk.user_utils import PsiTurkAuthorization, nocache

from psiturk.psiturk_statuses import ALLOCATED, BONUSED, COMPLETED, \
    CREDITED, NOT_ACCEPTED, QUITEARLY, STARTED, SUBMITTED
IGNORE = 100 #custom status for ignoring data for conditioning purposes
PSITURK_STATUSES = {
    "ALLOCATED": ALLOCATED,
    "BONUSED": BONUSED,
    "COMPLETED": COMPLETED,
    "CREDITED": CREDITED,
    "NOT_ACCEPTED": NOT_ACCEPTED,
    "QUITEARLY": QUITEARLY,
    "STARTED": STARTED,
    "SUBMITTED": SUBMITTED,
    "IGNORE": IGNORE
}
import datetime
import json
from collections import Counter

# # Database setup
from psiturk.db import db_session, init_db
from psiturk.models import Participant
from json import dumps, loads

# load the configuration options
config = PsiturkConfig()
config.load_config()
myauth = PsiTurkAuthorization(config)  # if you want to add a password protect route use this

# explore the Blueprint
custom_code = Blueprint('custom_code', __name__, template_folder='templates', static_folder='static')


def get_participants(codeversion):
    return (
        Participant
        .query
        .filter(Participant.codeversion == codeversion)
        # .filter(Participant.status >= 3)  # only take completed
        .all()
    )

@custom_code.route('/testexperiment')
def testexperiment():
    data = {
        key: "{{ " + key + " }}"
        for key in ['uniqueId', 'condition', 'counterbalance', 'adServerLoc', 'mode']
    }
    return render_template('exp.html', **data)

@custom_code.route('/data/<codeversion>/<name>', methods=['GET'])
@myauth.requires_auth
@nocache
def download_datafiles(codeversion, name):
    contents = {
        "trialdata": lambda p: p.get_trial_data(),
        "eventdata": lambda p: p.get_event_data(),
        "questiondata": lambda p: p.get_question_data(),
        "bonusdata": lambda p: f"{p.uniqueid},{p.bonus}\n",
        "conditiondata": lambda p: f"{p.uniqueid},{p.cond}\n"
    }

    if name not in contents:
        abort(404)

    query = get_participants(codeversion)

    # current_app.logger.critical('data %s', data)
    def ret():
        for p in query:
            try:
                yield contents[name](p)
            except TypeError:
                current_app.logger.error("Error loading {} for {}".format(name, p))
                current_app.logger.error(format_exc())
    response = Response(
        ret(),
        mimetype="text/csv",
        headers={
            'Content-Disposition': 'attachment;filename=%s.csv' % name
        })

    return response

@custom_code.route("/set_condition", methods=['GET', 'POST'])
def set_condition():
    new_cond = request.args.get('new_cond', default=None, type=int)
    uniqueId = request.args['uniqueId']
    user = Participant.query. \
        filter(Participant.uniqueid == uniqueId).one()
    old_cond = user.cond
    user.cond = new_cond
    db_session.commit()
    return jsonify(**{'old_cond': old_cond, 'new_cond': new_cond})

@custom_code.route('/compute_bonus', methods=['GET'])
def compute_bonus():
    # check that user provided the correct keys
    # errors will not be that gracefull here if being
    # accessed by the Javascrip client
    if 'uniqueId' not in request.args:
        raise ExperimentError('improper_inputs')  # i don't like returning HTML to JSON requests...  maybe should change this
    uniqueId = request.args['uniqueId']

    try:
        # lookup user in database
        user = Participant.query.\
               filter(Participant.uniqueid == uniqueId).\
               one()

        bonus = 0
        user_data = loads(user.datastring) # load datastring from JSON
        for qname, resp in user_data['questiondata'].items():
            if qname == 'bonusDollars':
                bonus = round(resp, 2)
                break
        bonus = min(bonus, 10)

        user.bonus = bonus
        db_session.add(user)
        db_session.commit()
        resp = {"bonusComputed": "success", 'bonus': bonus}
        return jsonify(**resp)
    except:
        abort(404)  # again, bad to display HTML, but...

def custom_get_condition(mode):
    """
    This is the same as get_random_condcount in experiment.py
    except we excude workers with "debug" in their name.
    """
    current_app.logger.info("Running custom_get_condition")
    cutofftime = datetime.timedelta(minutes=-config.getint('Task Parameters',
                                                           'cutoff_time'))
    starttime = datetime.datetime.now(datetime.timezone.utc) + cutofftime

    try:
        conditions = json.load(
            open(os.path.join(current_app.root_path, 'conditions.json')))
        numconds = len(list(conditions.keys()))
        numcounts = 1
    except IOError:
        numconds = config.getint('Task Parameters', 'num_conds')
        numcounts = config.getint('Task Parameters', 'num_counters')

    participants = Participant.query.\
        filter(Participant.codeversion ==
               config.get('Task Parameters', 'experiment_code_version')).\
        filter(Participant.mode == mode).\
        filter(or_(Participant.status == COMPLETED,
                   Participant.status == CREDITED,
                   Participant.status == SUBMITTED,
                   Participant.status == BONUSED,
                   Participant.beginhit > starttime)).\
        filter(Participant.status != IGNORE).all()
    counts = Counter()
    for cond in range(numconds):
        for counter in range(numcounts):
            counts[(cond, counter)] = 0
    for participant in participants:
        if "debug" in participant.uniqueid:
            continue
        condcount = (participant.cond, participant.counterbalance)
        if condcount in counts:
            counts[condcount] += 1
    mincount = min(counts.values())
    minima = [hsh for hsh, count in counts.items() if count == mincount]
    chosen = choice(minima)
    current_app.logger.info("given %(a)s chose %(b)s" % {'a': counts, 'b': chosen})

    return chosen

@custom_code.route("/set_status", methods=['GET'])
def set_status():
    """ Set the worker's status """
    if 'uniqueId' not in request.args:
        resp = {"status": "Bad Request: uniqueId is required"}
        return jsonify(**resp)
    elif 'new_status' not in request.args:
        resp = {"status": "Bad Request: new_status is required"}
        return jsonify(**resp)
    unique_id = request.args['uniqueId']
    new_status = request.args['new_status'].upper()
    if new_status not in PSITURK_STATUSES:
        resp = {"status": "unrecognized new_status"}
        return jsonify(**resp)
    new_status = PSITURK_STATUSES[new_status]

    try:
        user = Participant.query.\
            filter(Participant.uniqueid == unique_id).one()
        old_status = user.status
        user.status = new_status
        db_session.add(user)
        db_session.commit()
        status_msg = f"Success: Setting {unique_id} status from {old_status} to {new_status}"
        current_app.logger.info(status_msg)
    except Exception as e:
        status_msg = str(e)
        current_app.logger.info(status_msg)
    resp = {"status": status_msg}
    return jsonify(**resp)
