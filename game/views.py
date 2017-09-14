# -*- coding: utf8 -*-
import random
from flask import render_template, session, redirect, url_for, request, jsonify
from sqlalchemy import func
from game import app, db_session as db
from game.forms import LoginByCodeForm, GameForm, TransactionForm
from game.models import User, Player, Game, Company, Transaction
from game.decorators import login_required
from game.parameters import *


@app.route('/')
@login_required
def index():
    return render_template('index.html', **{'session': session})


@app.route('/login')
def login_page():
    if session.get('user_id'):
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/auth/login', methods=["POST"])
def login():
    form = LoginByCodeForm(request.form)
    if form.validate():
        u = User.query.filter(func.lower(User.login) == form.code.data.lower()).first()
        if not u:
            return redirect(url_for('login_page'))
        if not u.validate_password(form.code.data):
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
@login_required
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


@app.route('/games/<int:gid>')
@login_required
def game_view(gid):
    player = Player.query.filter_by(game_id=gid, user_id=session['user_id']).first()
    g = Game.query.get(gid)
    if session['user_id'] > 1 and (not player or not g):
        return redirect(url_for('index'))
    if not g:
        return redirect(url_for('index'))
    if g.state != 1 and player:
        return '{}, game is not active.'.format(player.name)
    # Fill context
    if player:
        context = {'money': player.money, 'id': player.id, 'name': player.name,
                   'description': player.description, 'round': g.step}
        if player.role == ROLE_PROGRAMMER:
            context['role'] = u'Программист'
            context['experience'] = player.experience
            context['free_exp'] = player.experience - sum([t.part for t in player.transactions_in if t.state <= 1])
            context['study_exp'] = int(g.get_var('study_exp'))
            context['study_price'] = int(g.get_var('study_price'))
            return render_template('employer.html', **context)
        elif player.role == ROLE_SEO:
            context['role'] = u'Специалист по продажам'
            context['experience'] = player.experience
            context['free_exp'] = player.experience - sum([t.part for t in player.transactions_in if t.state <= 1])
            context['study_exp'] = int(g.get_var('study_exp'))
            context['study_price'] = int(g.get_var('study_price'))
            return render_template('employer.html', **context)
        elif player.role == ROLE_STARTUP:
            context['investments'] = {}
            for t in player.transactions_in:
                if t.sender_id not in context['investments']:
                    context['investments'][t.sender_id] = {'name': t.sender.name, 'part': 0}
                context['investments'][t.sender_id]['part'] += t.part
            context['investments'] = sorted(context['investments'].values(), key=lambda x: x['part'])
            context['money'] = player.company.money
            context['tech'] = player.company.tech
            context['fame'] = player.company.fame
            context['independent_part'] = 100 - sum([t.part for t in player.transactions_in if t.state <= 2])
            context['outsource_price'] = int(g.get_var('outsource_price'))
            context['outsource_exp'] = int(g.get_var('outsource_exp'))
            context['skolkovo_money'] = int(g.get_var('skolkovo_money'))
            context['skolkovo_part'] = int(g.get_var('skolkovo_part'))
            context['employers'] = []
            for p in g.players:
                if p.role == ROLE_PROGRAMMER or p.role == ROLE_SEO:
                    context['employers'].append({
                        'id': p.id,
                        'available': p.experience - sum([t.part for t in p.transactions_in if t.state <= 1]),
                        'name': p.name,
                        'role': p.role
                    })
            context['employers'] = sorted(context['employers'], key=lambda x: (x['role'], x['available']))
            return render_template('company.html', **context)
        elif player.role == ROLE_INVESTOR:
            context['investments'] = {}
            for t in player.transactions_out:
                if t.receiver_id not in context['investments']:
                    context['investments'][t.receiver_id] = {'name': t.receiver.name, 'part': 0}
                context['investments'][t.receiver_id]['part'] += t.part
            context['investments'] = sorted(context['investments'].values(), key=lambda x: x['part'])
            context['companies'] = []
            for c in g.companies:
                context['companies'].append({
                    'id': c.owner.id,
                    'name': c.owner.name,
                    'available': 100 - sum([t.part for t in c.owner.transactions_in if t.state <= 2])
                })
            context['companies'] = sorted(context['companies'], key=lambda x: x['available'])
            return render_template('investor.html', **context)

    else:
        context = {'round': g.step, 'companies': [], 'workers': []}
        for c in g.companies:
            context['companies'].append({
                'name': c.owner.name,
                'tech': c.tech,
                'fame': c.fame
            })
        context['companies'] = list(enumerate(context['companies']))
        for p in g.players:
            if p.role == ROLE_PROGRAMMER or p.role == ROLE_SEO:
                context['workers'].append({
                    'name': p.name,
                    'experience': p.experience,
                    'role': p.role
                })
        context['workers'] = list(enumerate(context['workers']))
        return render_template('state.html', **context)
    return 'Hi!'


@app.route('/games/<int:gid>/state')
@login_required
def game_state(gid):
    player = Player.query.filter_by(game_id=gid, user_id=session['user_id']).first()
    if session['user_id'] > 1 and not player:
        return redirect(url_for('index'))
    g = Game.query.get(gid)
    if not g:
        return 'No such game', 404
    r = {'step': g.step, 'rounds': g.rounds, 'state': g.state}
    if g.state != 1:
        return jsonify(r)
    if player:
        r['money'] = player.money
        r['transactions'] = []
        if player.role == ROLE_PROGRAMMER or player.role == ROLE_SEO:
            r['experience'] = player.experience
            for t in player.transactions_in:
                r['transactions'].append({'id': t.id, 'state': t.state, 'text': t.for_receiver()})
        elif player.role == ROLE_INVESTOR:
            for t in player.transactions_out:
                r['transactions'].append({'id': t.id, 'state': t.state, 'text': t.for_sender(), 'out': True})
        elif player.role == ROLE_STARTUP:
            r['tech'] = player.company.tech
            r['fame'] = player.company.fame
            r['part'] = 100 - sum([t.part for t in player.transactions_in if t.state <= 2])
            r['money'] = player.company.money
            for t in player.transactions_in:
                r['transactions'].append({'id': t.id, 'state': t.state, 'text': t.for_receiver()})
            for t in player.transactions_out:
                r['transactions'].append({'id': t.id, 'state': t.state, 'text': t.for_sender(), 'out': True})
    else:
        r['players'] = ['TODO', 'players']
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
        p.money = g.get_var('investor_default_money')
    for i in players[companies + investors:companies + investors + seo]:
        p = g.players[i]
        p.role = ROLE_SEO
    for i in players[companies + investors + seo:]:
        p = g.players[i]
        p.role = ROLE_PROGRAMMER

    skolkovo = Player()
    skolkovo.role = ROLE_INVESTOR
    skolkovo.game = g
    skolkovo.name = u'Сколково'
    skolkovo.money = 1000000  # may be it's too much
    g.players.append(skolkovo)

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


@app.route('/games/<int:gid>/skolkovo')
@login_required
def skolkovo_game(gid):
    c = Company.query.join(Company.owner).filter(Company.game_id == gid, Player.user_id == session['user_id']).first()
    s = Player.query.filter(Player.game_id == gid, Player.name == u'Сколково').first()
    if c and c.invest(s, 300, 30):
        db.commit()
        return 'Requested'
    return 'No such company', 400


@app.route('/games/<int:gid>/vars/<key>/<value>')
@login_required
def set_var(gid, key, value):
    if session['user_id'] != 1:
        return 'Denied', 403
    g = Game.query.get(gid)
    if not g:
        return 'No such game', 400
    if g.set_var(key, float(value)):
        db.commit()
        return 'Var updated'
    return 'Can\'t update', 400
