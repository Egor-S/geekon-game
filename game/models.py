# -*- coding: utf8 -*-
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from game.database import Base
from auth.model import get_user_model

User = get_user_model(Base)


# class Game(Base):
#     __tablename__ = 'games'
