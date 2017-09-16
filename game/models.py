# -*- coding: utf8 -*-
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from game.database import Base
from game.parameters import *
from auth.model import get_user_model
from faker import Faker

fake_generator = Faker('en_US')
User = get_user_model(Base)


class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    state = Column(Integer, default=0)  # 0 - open for join, 1 - running, 2 - ended
    step = Column(Integer, default=0)
    join_code = Column(String(10))
    rounds = Column(Integer, default=10)

    players = relationship("Player", backref="game")
    companies = relationship("Company", backref="game")
    transactions = relationship("Transaction", backref="game")
    parameters = relationship("Parameter", backref="game")

    def __init__(self, code, rounds=None):
        self.join_code = code
        if rounds:
            self.rounds = rounds
        for k, v in GAME_PARAMETERS.items():
            self.parameters.append(Parameter(k.lower(), float(v)))

    def new_round(self):
        for c in self.companies:
            c.new_round()
        for p in self.players:
            p.new_round()
        self.step += 1
        if self.step > self.rounds:
            for p in self.players:
                p.active = False
            for c in self.companies:
                c.owner.active = False
                c.owner.money = c.money
        for t in self.transactions:
            if t.state == 0:
                t.state = 3
            elif t.state == 1:
                t.state = 2

    def get_var(self, key):
        for p in self.parameters:
            if p.key == key.lower():
                return p.value
        return 0.0

    def set_var(self, key, value):
        for p in self.parameters:
            if p.key == key.lower():
                p.value = float(value)
                return True
        return False


class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), default="Bob")
    description = Column(String(144), default="~")
    money = Column(Integer, default=0)
    experience = Column(Integer, default=10)
    active = Column(Boolean, default=False)
    role = Column(Integer)  # Start-up, Programmer, SEO, Investor

    game_id = Column(Integer, ForeignKey('games.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    company = relationship("Company", uselist=False, backref="owner")
    transactions_in = relationship("Transaction", backref="receiver", foreign_keys='Transaction.receiver_id')
    transactions_out = relationship("Transaction", backref="sender", foreign_keys='Transaction.sender_id')

    def __init__(self):
        self.name = fake_generator.name()
        self.description = fake_generator.address()[:144]

    def hire(self, company, amount, part):
        if (self.role == ROLE_PROGRAMMER or self.role == ROLE_SEO) and self.active:
            if sum([t.amount for t in company.owner.transactions_out if t.state == 0]) + amount <= company.money:
                if sum([t.part for t in self.transactions_in if t.state <= 1]) + part <= self.experience:
                    if self.role == ROLE_PROGRAMMER:
                        t = Transaction(amount, part, TRANSACTION_HIRE_PROGRAMMER)
                    else:
                        t = Transaction(amount, part, TRANSACTION_HIRE_SEO)
                    self.game.transactions.append(t)
                    t.sender = company.owner
                    t.receiver = self
                    return True
        return False

    def new_round(self):
        self.active = True

    def study(self):
        if self.role == ROLE_PROGRAMMER or self.role == ROLE_SEO:
            if self.active and self.money >= self.game.get_var('study_price') and \
                    sum([1 for t in self.transactions_in if t.state <= 1]) == 0:
                self.active = False
                self.money -= self.game.get_var('study_price')
                self.experience += self.game.get_var('study_exp')
                return True
        return False


class Company(Base):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    money = Column(Integer, default=0)
    tech = Column(Integer, default=0)
    fame = Column(Integer, default=0)
    title = Column(String(100), default="Simple company")

    game_id = Column(Integer, ForeignKey('games.id'))
    owner_id = Column(Integer, ForeignKey('players.id'))

    def outsource(self, role):
        if self.owner.active:
            if role == ROLE_PROGRAMMER and self.money >= self.game.get_var('outsource_price'):
                self.money -= int(self.game.get_var('outsource_price'))
                self.tech += int(self.game.get_var('outsource_exp'))
                return True
            elif role == ROLE_SEO and self.money >= self.game.get_var('outsource_price'):
                self.money -= int(self.game.get_var('outsource_price'))
                self.fame += int(self.game.get_var('outsource_exp'))
                return True
        return False

    def invest(self, investor, amount, part):
        if investor.role == ROLE_INVESTOR:
            if investor.money >= amount + sum([t.amount for t in investor.transactions_out if t.state == 0]):
                if sum([t.part for t in self.owner.transactions_in if t.state <= 2]) + part <= 100:
                    t = Transaction(amount, part, TRANSACTION_INVEST)
                    self.game.transactions.append(t)
                    t.receiver = self.owner
                    t.sender = investor
                    return True
        return False

    def new_round(self):
        gain = int(self.game.get_var('fame_x') * self.fame - self.game.get_var('penalty_x') * max(0, self.fame - self.tech))
        total_payments = 0
        for t in self.owner.transactions_in:
            if t.type == TRANSACTION_INVEST and (t.state == 1 or t.state == 2):
                payment = int(t.part / 100.0 * gain)
                t.sender.money += payment
                total_payments += payment
        gain -= total_payments
        gain -= int(self.game.get_var('tax_x') * gain)
        self.money += gain


class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    state = Column(Integer, default=0)  # waiting, accepted, accepted in previous round, rejected
    type = Column(Integer, default=0)
    amount = Column(Integer, default=0)
    part = Column(Integer, default=0)  # part of company or experience

    game_id = Column(Integer, ForeignKey('games.id'))
    sender_id = Column(Integer, ForeignKey('players.id'))
    receiver_id = Column(Integer, ForeignKey('players.id'))

    def __init__(self, amount, part, t_type):
        self.amount = amount
        self.part = part
        self.type = t_type

    def reject(self):
        self.state = 3

    def accept(self):
        if self.type == TRANSACTION_INVEST:
            self.receiver.company.money += self.amount
            self.sender.money -= self.amount
        elif self.type == TRANSACTION_HIRE_PROGRAMMER:
            self.receiver.money += self.amount
            self.sender.company.money -= self.amount
            self.sender.company.tech += self.part
        elif self.type == TRANSACTION_HIRE_SEO:
            self.receiver.money += self.amount
            self.sender.company.money -= self.amount
            self.sender.company.fame += self.part
        self.state = 1

    def for_receiver(self):
        values = [self.sender.name, self.amount, self.part]
        if self.type == TRANSACTION_INVEST:
            return u'Инвестиция от {0}: {1} GC за {2}%'.format(*values)
        elif self.type == TRANSACTION_HIRE_SEO or self.type == TRANSACTION_HIRE_PROGRAMMER:
            return u'Приглашение на работу от {0}: {1} GC за {2} опыта'.format(*values)

    def for_sender(self):
        values = [self.receiver.name, self.amount, self.part]
        if self.type == TRANSACTION_INVEST:
            return u'Инвестиция в {0}: {1} GC за {2}%'.format(*values)
        elif self.type == TRANSACTION_HIRE_SEO or self.type == TRANSACTION_HIRE_PROGRAMMER:
            return u'Приглашение на работу {0}: {1} GC за {2} опыта'.format(*values)


class Parameter(Base):  # TODO
    __tablename__ = 'parameters'
    id = Column(Integer, primary_key=True)
    key = Column(Integer)
    value = Column(Float, default=0.0)

    game_id = Column(Integer, ForeignKey('games.id'))

    def __init__(self, key, value):
        self.key = key
        self.value = value


User.players = relationship("Player", backref="user")
