import string
import random
from game import db_session as db, engine as db_engine
from game.models import User, Player, Game
from game.database import init_db, Base

strong_admin = 'GasdyYASD'

print 'Drop all tables...'
Base.metadata.drop_all(bind=db_engine)
print 'Create all tables...'
init_db()

print 'Fill all tables...'
db.add(User(strong_admin, strong_admin))  # id1
g = Game('token')
db.add(g)
for i in xrange(16):
    code = "".join([random.choice(string.digits + string.ascii_lowercase) for _ in xrange(8)])
    u = User(code, code)
    db.add(u)
    p = Player()
    p.user = u
    p.game = g
db.commit()
print 'Done!'
