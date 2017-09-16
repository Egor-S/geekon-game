# -*- coding: utf8 -*-
from game import app
from config import PORT, DEBUG

app.run('0.0.0.0', PORT, DEBUG, threaded=True)
