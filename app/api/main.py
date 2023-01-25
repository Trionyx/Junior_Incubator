from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_mail import Mail, Message
from datetime import datetime
import functools
import jwt
import re
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config, DevConfig


app = Flask(__name__)
app.config.from_object(DevConfig)
app.config.from_object(Config)  # TODO check if it's necessary
db = SQLAlchemy(app)
mail = Mail(app)
api = Api(app)

# for DB table creation in db_create.py
context = app.app_context()


# Old db.model
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())

    def __repr__(self):
        return f'Event: {self.description}'

    def __init__(self, description):
        self.description = description


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    date_joined = db.Column(db.DateTime, nullable=False, default=datetime.utcnow())
    user_language = db.Column(db.String(2), nullable=False, default="EN")  # ISO 639-1 format
    speciality_main = db.Column(db.String(128), nullable=True)
    speciality_secondary = db.Column(db.String(128), nullable=True)
    about_short = db.Column(db.String(280), nullable=True)  # Should be JSON here
    about_full = db.Column(db.String(500), nullable=True)  # Should be JSON here
    shares_total = db.Column(db.Integer, nullable=False, default=0)
    tech_stack = db.Column(db.String(500), nullable=True)  # TODO make list here
    avg_team_mark = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'User: {self.username}'

    def __init__(self, username):
        self.username = username


def login_required(method):
    @functools.wraps(method)
    def wrapper(self):
        header = request.headers.get('Authorization')
        token = header.split()
        try:
            decoded = jwt.decode(token, app.config['SECRET_KEY '], algorithms='HS256')
        except jwt.DecodeError:
            abort(400, message='Token is not valid.')
        except jwt.ExpiredSignatureError:
            abort(400, message='Token is expired.')
        email = decoded['email']
        if db.users.find({'email': email}).count() == 0:
            abort(400, message='User is not found.')
        user = db.users.find_one({'email': email})
        return method(self, user)
    return wrapper


class Register(Resource):
    def post(self):
        email = request.json['email']
        password = request.json['password']
        if not re.match(r'^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$', email):
            abort(400, message='email is not valid.')
        if len(password) < 6:
            abort(400, message='password is too short.')
        if db.users.find({'email': email}).count() != 0:
            if db.users.find_one({'email': email})['active']:
                abort(400, message='email is already used.')
        else:
            db.users.insert_one({'email': email, 'password': generate_password_hash(password), 'active': False})
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=app.config['ACTIVATION_EXPIRE_DAYS'])
        encoded = jwt.encode({'email': email, 'exp': exp},
                             app.config['SECRET_KEY '], algorithm='HS256')
        message = 'Hello\nactivation_code={}'.format(encoded.decode('utf-8'))
        msg = Message(recipients=[email],
                      body=message,
                      subject='Activation Code')
        mail.send(msg)
        return {'email': email}


class Activate(Resource):
    def put(self):
        activation_code = request.json['activation_code']
        try:
            decoded = jwt.decode(activation_code, app.config['SECRET_KEY '], algorithms='HS256')
        except jwt.DecodeError:
            abort(400, message='Activation code is not valid.')
        except jwt.ExpiredSignatureError:
            abort(400, message='Activation code is expired.')
        email = decoded['email']
        db.users.update({'email': email}, {'$set': {'active': True}})
        return {'email': email}


class Login(Resource):
    def get(self):
        email = request.json['email']
        password = request.json['password']
        if db.users.find({'email': email}).count() == 0:
            abort(400, message='User is not found.')
        user = db.users.find_one({'email': email})
        if not check_password_hash(user['password'], password):
            abort(400, message='Password is incorrect.')
        exp = datetime.datetime.utcnow() + datetime.timedelta(hours=app.config['TOKEN_EXPIRE_HOURS'])
        encoded = jwt.encode({'email': email, 'exp': exp},
                             app.config['SECRET_KEY '], algorithm='HS256')
        return {'email': email, 'token': encoded.decode('utf-8')}


# dashboard starts here
class Todo(Resource):
    @login_required
    def get(self, user):
        return {'email': user['email']}


api.add_resource(Register, '/v1/register')
api.add_resource(Activate, '/v1/activate')
api.add_resource(Login, '/v1/login')
api.add_resource(Todo, '/v1/todo')


"""
Old API on requests TODO remove when finish Restful
"""


def format_event(event):
    return {
        "description": event.description,
        "id": event.id,
        "created_at": event.created_at,
    }


@app.route('/')
def hello():
    return 'Hey!'


# create an event
@app.route('/events', methods=['POST'])
def create_event():
    description = request.json['description']
    event = Event(description)
    db.session.add(event)
    db.session.commit()
    return format_event(event)


# get all events
@app.route('/events', methods=['GET'])  # TODO BUG - operation successfully, but showing "Bad request syntax ('{')"
def get_events():
    events = Event.query.order_by(Event.id.asc()).all()
    event_list = []
    for event in events:
        event_list.append(format_event(event))
    return {'events': event_list}


# get single event
@app.route('/events/<event_id>', methods=['GET'])
def get_event(event_id):  # event_id here == id from tutorial  # TODO remove comment here at the end
    event = Event.query.filter_by(id=event_id).one()
    formatted_event = format_event(event)
    return {'event': formatted_event}


# delete an event
@app.route('/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    event = Event.query.filter_by(id=event_id).one()
    db.session.delete(event)
    db.session.commit()
    return f'Event (event_id: {event_id}) deleted '


# edit an event
@app.route('/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    event = Event.query.filter_by(id=event_id)
    description = request.json['description']
    event.update(dict(description=description, created_at=datetime.utcnow()))
    db.session.commit()
    return {'event': format_event(event.one())}


if __name__ == '__main__':
    app.run()
