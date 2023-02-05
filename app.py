from flask import Flask, render_template, request, redirect, url_for, send_from_directory, g
from azure.cosmos import CosmosClient
import datetime
import time
import json
import os

app = Flask(__name__)

def random_id(N = 20):
    import string, random
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(N))

def can_be_float(num):
    try:
        fl_num = float(num)
        return True if fl_num > 0.0 else False
    except ValueError:
        return False

def get_client():
    if not hasattr(g, 'client'):
        URL = os.environ["COSMOS_URI"]
        KEY = os.environ["COSMOS_KEY"]
        g.client = CosmosClient(URL, credential=KEY)
    return g.client


def get_db():
    if not hasattr(g, 'database'):
        g.database = get_client().get_database_client('db')
    return g.database


def get_container():
    if not hasattr(g, 'container'):
        g.container = get_db().get_container_client('weights')
    return g.container


@app.route('/')
def index():
    print('Request for index page received')
    usernames = get_container().query_items(
        query='SELECT DISTINCT w.username FROM weights w',
        enable_cross_partition_query=True
    )
    username_strings = []
    for username in usernames:
        username_strings.append(username["username"])
    return render_template('index.html', usernames = username_strings)


@app.route('/weights/<username>')
def weights(username):
    user_data = list(
        get_container().query_items(
            query='SELECT w.weight, w.timestamp FROM weights w WHERE w.username = \'{}\''.format(username),
            enable_cross_partition_query=True
        )
    )

    values = [
        user.get("weight") for user in user_data
    ]

    timestamps = [
        user.get("timestamp") for user in user_data
    ]
    
    labels = [
        str(datetime.datetime.fromtimestamp(timestamp)) for timestamp in timestamps
    ]

    _max = max(values) + 10
    _min = min(values) - 10
    
    return render_template(
        'weight_view.html',
        title='{}\'s Weight Over Time'.format(username.capitalize()),
        weights = values,
        times = labels,
        maximum = _max,
        minimum = _min
    )


@app.route('/weight', methods=['POST'])
def weight():
    user = request.form.get('username')

    weight = request.form.get('weight')
    if not can_be_float(weight):
        return 'weight is the wrong type', 400

    timestamp = request.form.get('timestamp')
    if not can_be_float(timestamp):
        return 'timestamp was wrong type', 400
    
    get_container().upsert_item(
        {
            'id': random_id(),
            'username': user,
            'weight': float(weight),
            'timestamp': float(timestamp)
        }
    )

    return 'successfully created new entry', 200


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


if __name__ == '__main__':
    app.run()
