
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import functools
import jwt  # here you need PyJWT, no just jwt
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


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=False)
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

    def __init__(self, username, email, password, active):
        self.username = username
        self.email = email
        self.password = password
        self.active = active


def login_required(method):
    """
    Decorator for checking if user is logged in
    Here you have to send token in http header using Bearer token, created on login
    """

    @functools.wraps(method)
    def wrapper(self):
        header = request.headers.get('Authorization')
        _, token = header.split()  # non-token header part ignoring
        try:
            decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms='HS256')
        except jwt.DecodeError:
            abort(400, message='Token is not valid.')
        except jwt.ExpiredSignatureError:
            abort(400, message='Token is expired.')
        email = decoded['email']
        if not Users.query.filter_by(email=email).first():
            abort(400, message='User is not found.')
        user = Users.query.filter_by(email=email).first()
        return method(self, user)

    return wrapper


class Register(Resource):
    def post(self):
        username = request.json['username']
        email = request.json['email']
        password = request.json['password']
        if not re.match(r'^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$', email):
            abort(400, message='email is not valid.')
        if len(password) < 8:
            abort(400, message='password is too short.')
        print(f"email: {email}")  # TEMP
        if Users.query.filter_by(email=email).first():
            print(f'user has been found: {Users.query.filter_by(email=email).first()}')
            if Users.query.filter_by(email=email, active=True):  # Check only active user email existence
                abort(400, message='email is already used.')
        else:
            db.session.add(Users(
                username=username,
                email=email,
                password=generate_password_hash(password),
                active=False,
            ))
            db.session.commit()
        exp = datetime.utcnow() + timedelta(days=app.config['ACTIVATION_EXPIRE_DAYS'])
        encoded = jwt.encode({'email': email, 'exp': exp},
                             app.config['SECRET_KEY'], algorithm='HS256')
        message = f'Hello\nactivation_code = \n{encoded}'
        msg = Message(recipients=[email],
                      body=message,
                      subject='Junior Incubator Activation')
        # FIXME don't save user in DB if can't send email or make method for resend
        # main problem is that Mailgunt can't send emails to unverified emails
        # TODO also need async code here
        mail.send(msg)
        return {'email': email}


class Activate(Resource):
    def put(self):
        activation_code = request.json['activation_code']
        try:
            decoded = jwt.decode(activation_code, app.config['SECRET_KEY'], algorithms='HS256')
        except jwt.DecodeError:
            abort(400, message='Activation code is not valid.')
        except jwt.ExpiredSignatureError:
            abort(400, message='Activation code is expired.')
        email = decoded['email']
        user_activation = Users.query.filter_by(email=email).first()
        user_activation.active = True
        db.session.commit()
        return {'email': email}


class Login(Resource):
    def get(self):
        email = request.json['email']
        login_password = request.json['password']
        if not Users.query.filter_by(email=email).first():
            abort(400, message='User is not found.')
        db_user = Users.query.filter_by(email=email).first()
        if not check_password_hash(db_user.password, login_password):
            abort(400, message='Password is incorrect.')
        exp = datetime.utcnow() + timedelta(hours=app.config['TOKEN_EXPIRE_HOURS'])
        encoded_token = jwt.encode({'email': email, 'exp': exp},
                                   app.config['SECRET_KEY'], algorithm='HS256')
        return {'email': email, 'token': encoded_token}


# Check cookies and session
class Cookie(Resource):
    @login_required
    def get(self, user):
        print(f"{user} is logged in")  # TEMP
        return {'email': user.email}


# dashboard starts here
class Dashboard(Resource):
    @login_required  # Only work with http authorization header with Bearer token
    def get(self, user):

        return {'email': user.email}


class Todo(Resource):
    @login_required  # Only work with http authorization header with Bearer token
    def get(self, user):
        task_name = request.json['name']
        task_description = request.json['description']
        print(f"task_name: {task_name}")
        print(f"task_description: {task_description}")
        return {'email': user.email}


api.add_resource(Register, '/v1/register')
api.add_resource(Activate, '/v1/activate')
api.add_resource(Login, '/v1/login')
api.add_resource(Todo, '/v1/todo')
api.add_resource(Dashboard, '/v1/dashboard')
api.add_resource(Cookie, '/v1/cookie')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000)


# based on: https://github.com/oliverSI/flask-restful-authentication/blob/master/app/api.py
