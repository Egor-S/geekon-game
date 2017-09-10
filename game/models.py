# -*- coding: utf8 -*-
import string
import random
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from game.database import Base
from game.config import *
from auth.model import get_user_model

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
    investments = relationship("Investment", backref="game")

    def __init__(self, code, rounds=None):
        self.join_code = code
        if rounds:
            self.rounds = rounds

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


class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    money = Column(Integer, default=0)
    experience = Column(Integer, default=10)
    active = Column(Boolean, default=False)
    role = Column(Integer)  # Start-up, Programmer, SEO, Investor
    token = Column(String(10))

    game_id = Column(Integer, ForeignKey('games.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="player", uselist=False)
    company = relationship("Company", uselist=False, backref="owner")
    investments = relationship("Investment", backref="investor")

    def new_round(self):
        self.active = True
        self.token = "".join([random.choice(string.digits + string.ascii_lowercase) for _ in xrange(6)])

    def study(self):
        if self.role == ROLE_PROGRAMMER or self.role == ROLE_SEO:
            if self.active and self.money > STUDY_PRICE:
                self.active = False
                self.money -= STUDY_PRICE
                self.experience += STUDY_EXPERIENCE
                return True
        return False


class Company(Base):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    money = Column(Integer, default=0)
    tech = Column(Integer, default=0)
    fame = Column(Integer, default=0)

    game_id = Column(Integer, ForeignKey('games.id'))
    owner_id = Column(Integer, ForeignKey('players.id'))
    investments = relationship("Investment", backref="company")
    
    def hire(self, employer):
        if employer.role == ROLE_PROGRAMMER or employer.role == ROLE_SEO:
            if employer.active and self.money >= employer.experience * JOB_MULTIPLIER and self.owner.active:
                employer.active = False
                self.money -= int(employer.experience * JOB_MULTIPLIER)
                employer.money += int(employer.experience * JOB_MULTIPLIER)
                if employer.role == ROLE_PROGRAMMER:
                    self.tech += employer.experience
                else:
                    self.fame += employer.experience
                return True
        return False

    def outsource(self, role):
        if self.owner.active:
            if role == ROLE_PROGRAMMER and self.money >= OUTSOURCE_PRICE:
                self.money -= OUTSOURCE_PRICE
                self.tech += OUTSOURCE_EXPERIENCE
                return True
            elif role == ROLE_SEO and self.money >= OUTSOURCE_PRICE:
                self.money -= OUTSOURCE_PRICE
                self.fame += OUTSOURCE_EXPERIENCE
                return True
        return False

    def invest(self, investor, amount, part):
        if investor.role == ROLE_INVESTOR:
            if investor.active and investor.money >= amount and self.owner.active:
                investor.active = False
                investor.money -= amount
                self.money += amount
                i = Investment(amount, part)
                i.company = self
                investor.investments.append(i)
                return True
        return False

    def new_round(self):
        self.owner.active = True
        gain = int(FAME_MULTIPLIER * self.fame - PENALTY_MULTIPLIER * max(0, self.fame - self.tech))
        total_payments = 0
        for i in self.investments:
            payment = int(i.part / 100.0 * gain)
            i.investor.money += payment
            total_payments += payment
        gain -= total_payments
        gain -= int(TAX_MULTIPLIER * gain)
        self.money += gain


class Investment(Base):
    __tablename__ = 'investments'
    id = Column(Integer, primary_key=True)
    amount = Column(Integer)  # money
    part = Column(Integer)  # percents (<100)

    game_id = Column(Integer, ForeignKey('games.id'))
    investor_id = Column(Integer, ForeignKey('users.id'))
    company_id = Column(Integer, ForeignKey('companies.id'))

    def __init__(self, amount, part):
        self.amount = amount
        self.part = part

User.players = relationship("Player", back_populates="user")
