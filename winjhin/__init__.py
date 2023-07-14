import asyncio
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder='static')
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///summoner.db'
app.config['SECRET_KEY'] = 'VbJjCIF4DGsE0KrXNgWASpQcYyNrQeR6'
db = SQLAlchemy(app)

from winjhin import routes