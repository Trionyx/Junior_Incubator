import os


class Config(object):
    # flask secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'any_key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:nWRbi0HR0xYSXQxW60tH@containers-us-west-91.railway.app:7328/railway'

