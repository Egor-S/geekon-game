# -*- coding: utf8 -*-
from flask import render_template, session, redirect, url_for, request, jsonify
from sqlalchemy import func
from game import app, db_session as db
from game.forms import LoginForm, RegistrationForm, GameForm
from game.models import User, Player, Game, Company
from game.decorators import login_required


@app.route('/')
def index():
    return render_template('index.html', **{'session': session})


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


@app.route('/games/join')
@login_required
def join_game():
    code = request.args.get('code', None)
    g = Game.query.filter_by(join_code=code, state=0).first()
    if g:
        if not Player.query.filter_by(user_id=session['user_id'], game_id=g.id).first():
            p = Player()
            p.user_id = session['user_id']
            g.players.append(p)
            db.commit()
        return redirect(url_for('game_view', gid=g.id))
    return redirect(url_for('index'))


@app.route('/games/<gid>')
@login_required
def game_view(gid):
    if session['user_id'] > 1 and not Player.query.filter_by(game_id=gid, user_id=session['user_id']).first():
        return redirect(url_for('index'))
    g = Game.query.get(gid)
    if not g:
        return redirect(url_for('index'))
    players = [{'login': p.user.login, 'money': p.money} for p in g.players]
    return jsonify(players)


@app.route('/games/<gid>/state')
@login_required
def game_state(gid):
    if session['user_id'] > 1 and not Player.query.filter_by(game_id=gid, user_id=session['user_id']).first():
        return redirect(url_for('index'))
    g = Game.query.get(gid)
    if not g:
        return 'No such game', 404
    r = {'step': g.step, 'rounds': g.rounds, 'state': g.state}
    if g.state == 0:
        r['players'] = [p.user.login for p in g.players]
    return jsonify(r)


@app.route('/games/new')
@login_required
def new_game():
    form = GameForm(request.args)
    if form.validate():
        g = Game(form.code.data, form.rounds.data)
        db.add(g)
        db.commit()
        return redirect(url_for('game_view', gid=g.id))
    return redirect('index')
