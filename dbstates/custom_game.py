# -*- coding: utf8 -*-
import string
import random
from game import db_session as db, engine as db_engine
from game.models import User, Player, Game, Company
from game.database import init_db, Base


def random_token(length):
    return "".join([random.choice(string.digits + string.ascii_lowercase) for _ in xrange(length)])


def load_credentials(filename):
    credentials = {}
    with open(unicode(filename), "r") as f:
        for line in f.readlines():
            group, name, description = line.decode('utf8').split(";")
            if int(group) not in credentials:
                credentials[int(group)] = []
            credentials[int(group)].append([name, description])
    return credentials


def main():
    print 'Drop all tables...'
    Base.metadata.drop_all(bind=db_engine)
    print 'Create all tables...'
    init_db()

    f = open('players_info.txt', 'w')
    print 'Fill all tables...'
    token = random_token(16)
    db.add(User(token, token))  # id == 1
    print >>f, 'admin:', token, '\n'
    g = Game(random_token(8))
    db.add(g)

    credentials = load_credentials('dbstates/credentials.csv')
    print >>f, 'programmers:'
    for p in credentials[1]:  # programmers
        token = random_token(8)
        u = User(token, token)
        db.add(u)
        player = Player()
        player.user = u
        player.game = g
        player.name = p[0]
        player.description = p[1]
        player.role = 1
        print >>f, player.name.encode('utf-8'), '-', token
    print >>f, '\n', 'seo:'
    for p in credentials[2]:  # seo
        token = random_token(8)
        u = User(token, token)
        db.add(u)
        player = Player()
        player.user = u
        player.game = g
        player.name = p[0]
        player.description = p[1]
        player.role = 2
        print >>f, player.name.encode('utf-8'), '-', token
    print >>f, '\n', 'companies:'
    for p in credentials[0]:  # companies
        token = random_token(8)
        u = User(token, token)
        db.add(u)
        player = Player()
        player.user = u
        player.game = g
        player.name = p[0]
        player.description = p[1]
        player.role = 0
        comp = Company()
        comp.owner = player
        comp.game = g
        print >>f, player.name.encode('utf-8'), '-', token
    print >>f, '\n', 'investors:'
    for p in credentials[1]:  # investors
        token = random_token(8)
        u = User(token, token)
        db.add(u)
        player = Player()
        player.user = u
        player.game = g
        player.name = p[0]
        player.description = p[1]
        player.role = 3
        player.money = g.get_var('investor_default_money')
        print >>f, player.name.encode('utf-8'), '-', token
    f.close()
    skolkovo = Player()
    skolkovo.role = 3
    skolkovo.game = g
    skolkovo.name = u'Сколково'
    skolkovo.money = 1000000  # may be it's too much
    g.players.append(skolkovo)
    db.commit()

    g.state = 1
    g.new_round()
    db.commit()
    print 'Done!'


if __name__ == '__main__':
    main()
