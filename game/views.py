# -*- coding: utf8 -*-
import random
from flask import render_template, session, redirect, url_for, request, jsonify
from sqlalchemy import func
from game import app, db_session as db
from game.forms import LoginForm, RegistrationForm, GameForm, TransactionForm
from game.models import User, Player, Game, Company, Transaction
from game.decorators import login_required
from game.parameters import *


@app.route('/')
def index():
    return render_template('index.html', **{'session': session})


@app.route('/login')
def login_page():
    if session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('login.html')


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


# @app.route('/registration')
# def registration_page():
#     if session.get('user_id'):
#         return redirect(url_for('index'))
#     return render_template('registration.html')


# @app.route('/auth/registration', methods=["POST"])
# def registration():
#     form = RegistrationForm(request.form)
#     if form.validate():
#         u = User.register(form)
#         db.add(u)
#         db.commit()
#         session['user_id'] = u.id
#         return redirect(url_for('index'))
#     return redirect(url_for('registration_page'))


@app.route('/logout')
def logout():
    if session.get('user_id', None):
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


@app.route('/games/<int:gid>')
@login_required
def game_view(gid):
    # TODO
    if session['user_id'] > 1 and not Player.query.filter_by(game_id=gid, user_id=session['user_id']).first():
        return redirect(url_for('index'))
    g = Game.query.get(gid)
    if not g:
        return redirect(url_for('index'))
    players = [{'login': p.name, 'money': p.money} for p in g.players]
    return jsonify(players)


@app.route('/games/<int:gid>/state')
@login_required
def game_state(gid):
    # TODO refactor
    player = Player.query.filter_by(game_id=gid, user_id=session['user_id']).first()
    if session['user_id'] > 1 and not player:
        return redirect(url_for('index'))
    g = Game.query.get(gid)
    if not g:
        return 'No such game', 404
    r = {'step': g.step, 'rounds': g.rounds, 'state': g.state}
    if g.state == 0:
        r['players'] = [p.user.login for p in g.players]
    else:
        r['companies'] = []
        r['investors'] = []
        r['seo'] = []
        r['programmers'] = []
        for p in g.players:
            if p.role == ROLE_STARTUP:
                r['companies'].append({'name': p.name, 'money': p.company.money, 'active': p.active, 'id': p.company.id})
            elif p.role == ROLE_SEO:
                r['seo'].append({'name': p.name, 'money': p.money, 'active': p.active,
                                 'experience': p.experience, 'id': p.id})
            elif p.role == ROLE_PROGRAMMER:
                r['programmers'].append({'name': p.name, 'money': p.money, 'active': p.active,
                                         'experience': p.experience, 'id': p.id})
            elif p.role == ROLE_INVESTOR:
                r['investors'].append({'name': p.name, 'money': p.money, 'active': p.active, 'id': p.id})
        if player:
            r['transactions'] = [{'amount': t.amount, 'part': t.part, 'id': t.id, 'state': t.state}
                                 for t in player.transactions_in]
        r['investments'] = []  # TODO

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


@app.route('/games/<int:gid>/start')
@login_required
def start_game(gid):
    if session['user_id'] > 1:
        return 'Denied', 403
    g = Game.query.get(gid)
    if not g:
        return 'No such game', 404
    if g.state != 0 or len(g.players) <= 4:
        return 'Game can\'t be started', 400
    g.state = 1
    # Count of roles
    companies = len(g.players) / 4
    investors = companies
    seo = (len(g.players) - (companies + investors)) / 2
    # Create companies and set roles
    players = range(len(g.players))
    random.shuffle(players)
    for i in players[:companies]:
        p = g.players[i]
        p.role = ROLE_STARTUP
        c = Company()
        c.owner = p
        c.game = g
    for i in players[companies:companies + investors]:
        p = g.players[i]
        p.role = ROLE_INVESTOR
        p.money = INVESTOR_DEFAULT_MONEY
    for i in players[companies + investors:companies + investors + seo]:
        p = g.players[i]
        p.role = ROLE_SEO
    for i in players[companies + investors + seo:]:
        p = g.players[i]
        p.role = ROLE_PROGRAMMER

    g.new_round()
    db.commit()
    return 'Game started'


@app.route('/games/<int:gid>/study')
@login_required
def study_game(gid):
    p = Player.query.filter_by(game_id=gid, user_id=session['user_id']).first()
    if p and p.game.state == 1:
        if p.study():
            db.commit()
            return 'Level up!'
    return 'Error occurred', 400


@app.route('/games/<int:gid>/hire')
@login_required
def hire_game(gid):
    c = Company.query.join(Company.owner).filter(Company.game_id == gid, Player.user_id == session['user_id']).first()
    form = TransactionForm(request.args)
    if c and c.game.state == 1 and form.validate():
        employer = Player.query.filter_by(game_id=gid, id=form.receiver.data).first()
        if form.amount.data < 0 or form.part.data < 0:
            return 'Wrong values', 400
        if employer and employer.hire(c, form.amount.data, form.part.data):
            db.commit()
            return 'Hire request created'
    return 'Error occurred', 400


@app.route('/games/<int:gid>/outsource')
@login_required
def outsource_game(gid):
    c = Company.query.join(Company.owner).filter(Company.game_id == gid, Player.user_id == session['user_id']).first()
    if c and c.game.state == 1:
        if c.outsource(int(request.args.get('type', ROLE_PROGRAMMER))):
            db.commit()
            return 'Outsourced'
    return 'Error occurred', 400


@app.route('/games/<int:gid>/invest')
@login_required
def invest_game(gid):
    form = TransactionForm(request.args)
    if form.validate():
        c = Company.query.filter(Company.game_id == gid, Company.owner_id == form.receiver.data).first()
        i = Player.query.filter_by(user_id=session['user_id'], game_id=gid).first()
        if c and i:
            if form.amount.data < 0 or form.part.data < 0:
                return 'Wrong values', 400
            if c.invest(i, form.amount.data, form.part.data):
                db.commit()
                return 'Invest request created'
        else:
            return 'Can\'t find user or company', 400
    return 'Error occurred', 400


@app.route('/games/<int:gid>/round')
@login_required
def round_game(gid):
    if session['user_id'] > 1:
        return 'Denied', 403
    g = Game.query.get(gid)
    if not g:
        return 'No such game', 404
    g.new_round()
    db.commit()
    return 'New round'


@app.route('/games/<int:gid>/transactions/<int:tid>/accept')
@login_required
def accept_game(gid, tid):
    t = Transaction.query.join(Transaction.receiver).filter(Transaction.id == tid, Transaction.game_id == gid,
                                                            Player.user_id == session['user_id']).first()
    if t and t.state == 0:
        t.accept()
        db.commit()
        return 'Accepted'
    return 'Error occurred', 400


@app.route('/games/<int:gid>/transactions/<int:tid>/reject')
@login_required
def reject_game(gid, tid):
    t = Transaction.query.join(Transaction.receiver).filter(Transaction.id == tid, Transaction.game_id == gid,
                                                            Player.user_id == session['user_id']).first()
    if t and t.state == 0:
        t.reject()
        db.commit()
        return 'Rejected'
    return 'Error occurred', 400
