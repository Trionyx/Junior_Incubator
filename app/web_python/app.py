
import requests
import functools

from flask import Flask, render_template, url_for, redirect, request, make_response, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import InputRequired, Length
from flask_bcrypt import Bcrypt  # to send password to API safely

from config import Config, API_URL

app = Flask(__name__)
bcrypt = Bcrypt(app)

app.config.from_object(Config)
api_url = API_URL


def api_session_check(token):
    """
    requesting session from restapi
    """
    response = requests.get(api_url + '/cookie', headers={
        'Authorization': f'Bearer {token}',
    })
    return response


def login_required(method):
    """
    Decorator for checking if user have token in cookies
    """
    @functools.wraps(method)
    def wrapper():
        print(f'url for: {url_for(f"{method.__name__}")}')  # TMP
        token = request.cookies.get('LOGIN_INFO')
        if not token:
            flash('Your session expired, login again please')
            return redirect(url_for('login'))

        print(f'@login_required passed with token: {token}')  # TMP

        response = api_session_check(token)
        print(f'api_session_check response: {response}')  # TMP
        if response.status_code != 200:
            flash('Your API session expired, login again please')
            return redirect(url_for('login'))

        return method(token)

    return wrapper


class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    email = EmailField(validators=[
                       InputRequired(), Length(min=4, max=50)], render_kw={"placeholder": "Email"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')


class ActivationForm(FlaskForm):
    activation_code = StringField(validators=[
                           InputRequired(), Length(min=4, max=160)], render_kw={"placeholder": "Activation code"})
    submit = SubmitField('Activate')


class LoginForm(FlaskForm):
    # if username will be needed
    # username = StringField(validators=[
    #                        InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    email = EmailField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={
                                                                            "placeholder": "mail@example.com"})
    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # first check if user already has token in cookies
    cookie_token = request.cookies.get('LOGIN_INFO')
    if cookie_token:
        # then check if session is active in restapi, redirect to dashboard
        response = api_session_check(cookie_token)
        if response.status_code == 200:
            return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        print(f'api_url: {api_url}/login')  # TMP
        response = requests.get(api_url+'/login', json={
                                                        'email': form.email.data,
                                                        'password': form.password.data,
                                                        })
        if response.status_code == 200:
            token = response.json()['token']
            print(f"token: {token}")  # TMP

            # setting up cookies
            response_with_cookie = make_response(redirect(url_for('dashboard')))

            # 30 days -> TODO set max_age using config variable same as TOKEN_EXPIRE_HOURS
            response_with_cookie.set_cookie('LOGIN_INFO', token, max_age=30*24*3600)

            return response_with_cookie
        else:  # TMP debug info
            flash(f'Login failed: {response.json()["message"]}')
            print(f'response.content: {response.content}')
            print(f'response.text: {response.text}')
            print(f'response.status_code: {response.status_code}')
            print(f'response.reason: {response.reason}')

    return render_template('login.html', form=form)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard(token):
    print(f'dashboard token: {token}')  # TMP
    return render_template('dashboard.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout(token):  # FIXME logout func doesn't not work without it (fix wrapper?)
    response_with_cookie = make_response(redirect(url_for('login')))
    response_with_cookie.set_cookie('LOGIN_INFO', '', max_age=0)  # delete cookie
    return response_with_cookie


@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        print(f'api_url: {api_url}/register')  # TMP
        # TODO encrypt password (now we're sending it as plain text)
        response = requests.post(api_url + '/register', json={
            'username': form.username.data,
            'email': form.email.data,
            'password': form.password.data,
        })
        if response.status_code == 200:
            flash(f'User registered. Check your email for activation code', 'success')
            return redirect(url_for('activate'))

        flash(f'Error while registering user, please try again: {response.json()["message"]}')

        return redirect(url_for('register'))

    return render_template('register.html', form=form)


@app.route('/activate', methods=['GET', 'POST'])
def activate():
    form = ActivationForm()
    if form.validate_on_submit():
        response = requests.put(api_url + '/activate', json={
            'activation_code': form.activation_code.data,

        })
        if response.status_code == 200:
            flash(f'User activated successfully, login please', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'Error while activating user, please try again: {response.json()["message"]}')
            return redirect(url_for('activate'))

    return render_template('activate.html', form=form)


@app.route('/admin', methods=['GET', 'POST'])
def admin():

    pass


if __name__ == "__main__":
    app.run(debug=True)


# based on: https://github.com/arpanneupane19/Python-Flask-Authentication-Tutorial/blob/main/app.py
