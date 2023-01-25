import os

API_URL = 'http://127.0.0.1:3000/v1'  # for local version


class Config(object):
    # flask secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'any_key'

