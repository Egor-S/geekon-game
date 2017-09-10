# -*- coding: utf8 -*-
import datetime
from hashlib import pbkdf2_hmac
from binascii import hexlify
from sqlalchemy import Column, Integer, String, Boolean, DateTime

PBKDF2_ROUNDS = 10000


def get_user_model(base, table='users'):
    class User(base):
        __tablename__ = table
        id = Column(Integer, primary_key=True)
        login = Column(String(80), unique=True)
        password = Column(String(128))  # PBKDF2(password, login)
        join_date = Column(DateTime, default=datetime.datetime.utcnow)
        active = Column(Boolean, default=True)

        def __init__(self, login, password):
            self.login = login
            self.set_password(password)

        def validate_password(self, password):
            pass_hash = hexlify(pbkdf2_hmac('sha256', password, self.login.lower(), PBKDF2_ROUNDS, 64))
            return pass_hash == self.password

        def set_password(self, password):
            self.password = hexlify(pbkdf2_hmac('sha256', password, self.login.lower(), PBKDF2_ROUNDS, 64))

        @staticmethod
        def register(form):
            u = User(form.login.data, form.password.data)
            return u

    return User
