import datetime
from sqlalchemy import JSON
from winjhin import db

class Summoner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    summonerId = db.Column(db.String(63), unique=True, nullable=False)
    accountId = db.Column(db.String(56), unique=True, nullable=False)
    name = db.Column(db.String(16), unique=True, nullable=False)
    profileIconId = db.Column(db.Integer, nullable=False)
    summonerLevel = db.Column(db.Integer, nullable=False)
    rank = db.relationship('SummonerRank', backref='summoner', lazy=True)
    matches = db.relationship('Match', backref='summoner', lazy=True)
    match_data = db.relationship('MatchData', backref='summoner', lazy=True)

    def __repr__(self):
        return f"User('{self.accountId}', '{self.name}', '{self.profileIconId}')"

class SummonerRank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tier = db.Column(db.String(12), nullable=False)
    division = db.Column(db.String(4), nullable=False)
    wins = db.Column(db.Integer, nullable=False)
    losses = db.Column(db.Integer, nullable=False)
    leaguePoints = db.Column(db.Integer, nullable=False)
    summoner_id = db.Column(db.Integer, db.ForeignKey('summoner.id'), nullable=False)

    def __repr__(self):
        return f"SummonerRank('{self.summoner_id}', '{self.tier}', '{self.division}')"

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gameId = db.Column(db.BigInteger, nullable=False)
    champion = db.Column(db.String(16), nullable=False)
    timestamp = db.Column(db.BigInteger, nullable=False)
    date_saved = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    summoner_id = db.Column(db.Integer, db.ForeignKey('summoner.id'), nullable=False)
    match_data = db.relationship('MatchData', backref='matchlist', lazy=True)

    def __repr__(self):
        return f"Match('{self.gameId}', '{self.timestamp}', '{self.date_saved}')"

class MatchData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gameId = db.Column(db.BigInteger, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    date_saved = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    summoner_id = db.Column(db.Integer, db.ForeignKey('summoner.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)

    def __repr__(self):
        return f"MatchData('{self.id}', '{self.gameId}', '{self.date_saved}')"