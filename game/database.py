# -*- coding: utf8 -*-
from sqlalchemy.ext.declarative import declarative_base
from game import db_session as app_session, engine

Base = declarative_base()
Base.query = app_session.query_property()


def init_db():
    import game.models
    Base.metadata.create_all(bind=engine)
