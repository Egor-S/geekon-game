# -*- coding: utf8 -*-
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import DATABASE, SECRET_KEY

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
engine = create_engine(DATABASE, convert_unicode=True)
db_session = scoped_session(sessionmaker(bind=engine))

# load views
import game.views
