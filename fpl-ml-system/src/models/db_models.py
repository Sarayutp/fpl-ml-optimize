"""SQLAlchemy database models for FPL AI Optimizer."""

from datetime import datetime
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index, JSON

db = SQLAlchemy()


class Team(db.Model):
    """Premier League teams model."""
    
    __tablename__ = 'teams'
    
    team_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    short_name = db.Column(db.String(3), nullable=False)
    strength_overall_home = db.Column(db.Integer)
    strength_overall_away = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    players = db.relationship('Player', backref='team', lazy=True)
    home_fixtures = db.relationship('Fixture', foreign_keys='Fixture.home_team_id', backref='home_team', lazy=True)
    away_fixtures = db.relationship('Fixture', foreign_keys='Fixture.away_team_id', backref='away_team', lazy=True)
    
    def __repr__(self):
        return f'<Team {self.name}>'


class Player(db.Model):
    """FPL players model."""
    
    __tablename__ = 'players'
    
    player_id = db.Column(db.Integer, primary_key=True)
    web_name = db.Column(db.String(50), nullable=False, index=True)  # CRITICAL: Index for search performance
    first_name = db.Column(db.String(50))
    second_name = db.Column(db.String(50))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    position = db.Column(db.String(3), nullable=False)  # GKP, DEF, MID, FWD
    now_cost = db.Column(db.Integer, nullable=False)  # Price in tenths (e.g., 95 = £9.5M)
    
    # Performance metrics
    expected_goals = db.Column(db.Float, default=0.0)
    expected_assists = db.Column(db.Float, default=0.0)
    expected_goal_involvements = db.Column(db.Float, default=0.0)
    form = db.Column(db.Float, default=0.0)
    points_per_game = db.Column(db.Float, default=0.0)
    total_points = db.Column(db.Integer, default=0)
    
    # Playing time
    minutes = db.Column(db.Integer, default=0)
    starts = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(1), default='a')  # a=available, d=doubtful, i=injured, s=suspended, u=unavailable
    chance_of_playing_this_round = db.Column(db.Integer)
    chance_of_playing_next_round = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    past_stats = db.relationship('PlayerPastStats', backref='player', lazy=True)
    predictions = db.relationship('PlayerPrediction', backref='player', lazy=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_player_web_name', 'web_name'),
        Index('idx_player_team', 'team_id'),
        Index('idx_player_position', 'position'),
    )
    
    def __repr__(self):
        return f'<Player {self.web_name}>'
    
    @property
    def price_millions(self) -> float:
        """Convert now_cost from tenths to millions."""
        return self.now_cost / 10.0


class Fixture(db.Model):
    """FPL fixtures model."""
    
    __tablename__ = 'fixtures'
    
    fixture_id = db.Column(db.Integer, primary_key=True)
    gameweek = db.Column(db.Integer, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.team_id'), nullable=False)
    home_difficulty = db.Column(db.Integer)  # FDR - Fixture Difficulty Rating
    away_difficulty = db.Column(db.Integer)
    kickoff_time = db.Column(db.DateTime)
    finished = db.Column(db.Boolean, default=False)
    started = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    past_stats = db.relationship('PlayerPastStats', backref='fixture', lazy=True)
    predictions = db.relationship('PlayerPrediction', backref='fixture', lazy=True)
    
    def __repr__(self):
        return f'<Fixture GW{self.gameweek}: {self.home_team_id} vs {self.away_team_id}>'


class PlayerPastStats(db.Model):
    """Player historical performance statistics."""
    
    __tablename__ = 'player_past_stats'
    
    stat_id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.player_id'), nullable=False)
    fixture_id = db.Column(db.Integer, db.ForeignKey('fixtures.fixture_id'), nullable=False)
    
    # Performance metrics
    minutes = db.Column(db.Integer, default=0)
    goals_scored = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    clean_sheets = db.Column(db.Integer, default=0)
    goals_conceded = db.Column(db.Integer, default=0)
    own_goals = db.Column(db.Integer, default=0)
    penalties_saved = db.Column(db.Integer, default=0)
    penalties_missed = db.Column(db.Integer, default=0)
    yellow_cards = db.Column(db.Integer, default=0)
    red_cards = db.Column(db.Integer, default=0)
    saves = db.Column(db.Integer, default=0)
    bonus = db.Column(db.Integer, default=0)
    bps = db.Column(db.Integer, default=0)  # Bonus Points System
    
    # Context
    was_home = db.Column(db.Boolean, nullable=False)
    total_points = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PlayerPastStats {self.player_id} - Fixture {self.fixture_id}>'


class PlayerPrediction(db.Model):
    """ML predictions for player performance."""
    
    __tablename__ = 'player_predictions'
    
    prediction_id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.player_id'), nullable=False)
    fixture_id = db.Column(db.Integer, db.ForeignKey('fixtures.fixture_id'), nullable=True)  # None for general predictions
    
    # Predictions
    expected_points = db.Column(db.Float, nullable=False)
    expected_minutes = db.Column(db.Float)
    expected_goals = db.Column(db.Float)
    expected_assists = db.Column(db.Float)
    expected_clean_sheets = db.Column(db.Float)
    
    # Model metadata
    model_version = db.Column(db.String(50))
    confidence_score = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<PlayerPrediction {self.player_id}: {self.expected_points:.2f} pts>'


class User(db.Model):
    """User accounts for the application."""
    
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    fpl_team_id = db.Column(db.Integer, unique=True)  # Their FPL team ID
    
    # Profile
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    user_teams = db.relationship('UserTeam', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'


class UserTeam(db.Model):
    """User team selections for different gameweeks."""
    
    __tablename__ = 'user_teams'
    
    team_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    gameweek = db.Column(db.Integer, nullable=False)
    
    # Team composition (stored as JSON for flexibility)
    players_json = db.Column(JSON, nullable=False)  # List of player IDs
    captain_id = db.Column(db.Integer, db.ForeignKey('players.player_id'))
    vice_captain_id = db.Column(db.Integer, db.ForeignKey('players.player_id'))
    
    # Team metadata
    total_cost = db.Column(db.Float)
    expected_points = db.Column(db.Float)
    actual_points = db.Column(db.Integer)
    
    # Optimization metadata
    optimization_reasoning = db.Column(db.Text)
    created_with_ai = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    captain = db.relationship('Player', foreign_keys=[captain_id])
    vice_captain = db.relationship('Player', foreign_keys=[vice_captain_id])
    
    # Unique constraint to prevent duplicate teams for same gameweek
    __table_args__ = (
        db.UniqueConstraint('user_id', 'gameweek', name='unique_user_gameweek'),
    )
    
    def __repr__(self):
        return f'<UserTeam {self.user_id} - GW{self.gameweek}>'