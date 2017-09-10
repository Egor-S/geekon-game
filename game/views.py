# -*- coding: utf8 -*-
from flask import render_template, session, redirect, url_for, request
from game import app, db_session as db
from game.models import User
from sqlalchemy import func
from forms import LoginForm, RegistrationForm

@app.route('/')
def index():
    return 'Hello!'


@app.route('/login')
def login_page():
    if session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/registration')
def registration_page():
    if session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('registration.html')


@app.route('/auth/login', methods=["POST"])
def login():
    form = LoginForm(request.form)
    if form.validate():
        u = User.query.filter(func.lower(User.login) == form.login.data).first()
        if not u:
            return redirect(url_for('login_page'))
        if not u.validate_password(form.password.data):
            return redirect(url_for('login_page'))
        session['user_id'] = u.id
        return redirect(url_for('index'))
    return redirect(url_for('login_page'))


@app.route('/auth/registration', methods=["POST"])
def registration():
    form = RegistrationForm(request.form)
    if form.validate():
        u = User.register(form)
        db.add(u)
        db.commit()
        session['user_id'] = u.id
        return redirect(url_for('index'))
    return redirect(url_for('registration_page'))


@app.route('/logout')
def logout():
    del session['user_id']
    return redirect(url_for('login_page'))
