# -*- coding: utf8 -*-
from functools import wraps
from flask import session, redirect, url_for


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('user_id') is None:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return wrapper
