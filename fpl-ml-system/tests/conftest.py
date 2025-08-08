"""PyTest configuration and fixtures for FPL AI Optimizer tests."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from flask import Flask

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src import create_app
from src.models.db_models import db, Team, Player, Fixture, PlayerPastStats
from src.config import TestingConfig


@pytest.fixture(scope="session")
def app():
    """Create application for the tests."""
    app = create_app('testing')
    
    # Create a temporary database file
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{app.config['DATABASE']}"
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


@pytest.fixture(scope="function")
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    """Create database session for tests."""
    with app.app_context():
        # Start transaction
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Configure session to use transaction
        db.session.configure(bind=connection)
        
        yield db.session
        
        # Rollback transaction
        transaction.rollback()
        connection.close()
        db.session.remove()


@pytest.fixture
def sample_teams(db_session):
    """Create sample teams for testing."""
    teams_data = [
        {"team_id": 1, "name": "Arsenal", "short_name": "ARS"},
        {"team_id": 2, "name": "Chelsea", "short_name": "CHE"},
        {"team_id": 3, "name": "Manchester City", "short_name": "MCI"},
        {"team_id": 4, "name": "Liverpool", "short_name": "LIV"},
        {"team_id": 5, "name": "Manchester United", "short_name": "MUN"}
    ]
    
    teams = []
    for team_data in teams_data:
        team = Team(**team_data)
        db_session.add(team)
        teams.append(team)
    
    db_session.commit()
    return teams


@pytest.fixture
def sample_players(db_session, sample_teams):
    """Create sample players for testing."""
    players_data = [
        {
            "player_id": 1,
            "web_name": "Salah",
            "team_id": 4,  # Liverpool
            "position": "FWD",
            "now_cost": 130,
            "total_points": 200,
            "form": 5.5,
            "expected_points": 8.2
        },
        {
            "player_id": 2,
            "web_name": "De Bruyne",
            "team_id": 3,  # Manchester City
            "position": "MID",
            "now_cost": 125,
            "total_points": 180,
            "form": 6.0,
            "expected_points": 7.8
        },
        {
            "player_id": 3,
            "web_name": "Kane",
            "team_id": 5,  # Manchester United
            "position": "FWD",
            "now_cost": 120,
            "total_points": 175,
            "form": 5.8,
            "expected_points": 7.5
        },
        {
            "player_id": 4,
            "web_name": "Van Dijk",
            "team_id": 4,  # Liverpool
            "position": "DEF",
            "now_cost": 65,
            "total_points": 120,
            "form": 4.5,
            "expected_points": 5.2
        },
        {
            "player_id": 5,
            "web_name": "Alisson",
            "team_id": 4,  # Liverpool
            "position": "GKP",
            "now_cost": 55,
            "total_points": 140,
            "form": 4.8,
            "expected_points": 4.5
        }
    ]
    
    players = []
    for player_data in players_data:
        player = Player(**player_data)
        db_session.add(player)
        players.append(player)
    
    db_session.commit()
    return players


@pytest.fixture
def sample_fixtures(db_session, sample_teams):
    """Create sample fixtures for testing."""
    fixtures_data = [
        {
            "fixture_id": 1,
            "gameweek": 1,
            "home_team_id": 1,  # Arsenal
            "away_team_id": 2,  # Chelsea
            "home_difficulty": 3,
            "away_difficulty": 4,
            "finished": False
        },
        {
            "fixture_id": 2,
            "gameweek": 1,
            "home_team_id": 3,  # Manchester City
            "away_team_id": 4,  # Liverpool
            "home_difficulty": 5,
            "away_difficulty": 5,
            "finished": False
        },
        {
            "fixture_id": 3,
            "gameweek": 2,
            "home_team_id": 2,  # Chelsea
            "away_team_id": 3,  # Manchester City
            "home_difficulty": 4,
            "away_difficulty": 3,
            "finished": True
        }
    ]
    
    fixtures = []
    for fixture_data in fixtures_data:
        fixture = Fixture(**fixture_data)
        db_session.add(fixture)
        fixtures.append(fixture)
    
    db_session.commit()
    return fixtures


@pytest.fixture
def sample_player_stats(db_session, sample_players):
    """Create sample player past stats for testing."""
    stats_data = [
        {
            "player_id": 1,  # Salah
            "season": "2023-24",
            "gameweek": 1,
            "minutes": 90,
            "goals_scored": 1,
            "assists": 0,
            "clean_sheets": 0,
            "goals_conceded": 0,
            "own_goals": 0,
            "penalties_saved": 0,
            "penalties_missed": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "saves": 0,
            "bonus": 3,
            "bps": 32,
            "total_points": 8
        },
        {
            "player_id": 2,  # De Bruyne
            "season": "2023-24",
            "gameweek": 1,
            "minutes": 85,
            "goals_scored": 0,
            "assists": 2,
            "clean_sheets": 1,
            "goals_conceded": 0,
            "own_goals": 0,
            "penalties_saved": 0,
            "penalties_missed": 0,
            "yellow_cards": 1,
            "red_cards": 0,
            "saves": 0,
            "bonus": 2,
            "bps": 28,
            "total_points": 9
        }
    ]
    
    stats = []
    for stat_data in stats_data:
        stat = PlayerPastStats(**stat_data)
        db_session.add(stat)
        stats.append(stat)
    
    db_session.commit()
    return stats


@pytest.fixture
def optimization_request_data():
    """Sample optimization request data."""
    return {
        "budget": 100.0,
        "formation": "4-4-2",
        "preferred_players": [],
        "excluded_players": [],
        "max_players_per_team": 3,
        "include_reasoning": True
    }


@pytest.fixture
def player_search_data():
    """Sample player search request data."""
    return {
        "name": "",
        "position": "FWD",
        "team_id": None,
        "min_cost": 5.0,
        "max_cost": 15.0,
        "min_points": 50,
        "sort_by": "expected_points",
        "sort_order": "desc",
        "limit": 20
    }


@pytest.fixture
def mock_fpl_api_response():
    """Mock FPL API response data."""
    return {
        "events": [
            {"id": 1, "name": "Gameweek 1", "is_current": True, "is_next": False, "finished": False}
        ],
        "teams": [
            {"id": 1, "name": "Arsenal", "short_name": "ARS", "strength_overall_home": 4, "strength_overall_away": 4},
            {"id": 2, "name": "Chelsea", "short_name": "CHE", "strength_overall_home": 4, "strength_overall_away": 3}
        ],
        "elements": [
            {
                "id": 1,
                "web_name": "Salah",
                "team": 1,
                "element_type": 4,  # FWD
                "now_cost": 130,
                "total_points": 200,
                "form": "5.5",
                "expected_points": 8.2,
                "expected_goals": 0.8,
                "expected_assists": 0.3,
                "minutes": 1800,
                "goals_scored": 20,
                "assists": 8
            }
        ],
        "fixtures": [
            {
                "id": 1,
                "event": 1,
                "team_h": 1,
                "team_a": 2,
                "team_h_difficulty": 3,
                "team_a_difficulty": 4,
                "finished": False
            }
        ]
    }


@pytest.fixture
def mock_prediction_data():
    """Mock prediction data for testing."""
    return {
        1: {"expected_points": 8.2, "confidence": 0.85},
        2: {"expected_points": 7.8, "confidence": 0.82},
        3: {"expected_points": 7.5, "confidence": 0.78},
        4: {"expected_points": 5.2, "confidence": 0.75},
        5: {"expected_points": 4.5, "confidence": 0.88}
    }


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.ok = status_code < 400
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if not self.ok:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_requests_get(monkeypatch, mock_fpl_api_response):
    """Mock requests.get for FPL API calls."""
    def mock_get(url, *args, **kwargs):
        return MockResponse(mock_fpl_api_response)
    
    import requests
    monkeypatch.setattr(requests, "get", mock_get)
    return mock_get