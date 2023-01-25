import os
from dotenv import load_dotenv

load_dotenv()


class Config(object):
    # flask secret key
    SECRET_KEY = os.environ.get('SECRET_KEY').encode('utf8') or 'any_key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # email settings
    MAIL_SERVER = os.environ['MAIL_SERVER']
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ['MAIL_USERNAME']
    MAIL_PASSWORD = os.environ['MAIL_PASSWORD']
    MAIL_DEFAULT_SENDER = 'notification@ji.com'
    ACTIVATION_EXPIRE_DAYS = 5
    TOKEN_EXPIRE_HOURS = 1


class DevConfig(Config):
    # SQLALCHEMY_DATABASE_URI = os.environ['SQLALCHEMY_DATABASE_URI']

    # for local tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'


