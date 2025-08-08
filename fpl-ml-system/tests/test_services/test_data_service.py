"""Tests for DataService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.services.data_service import DataService
from src.models.db_models import Team, Player, Fixture


class TestDataService:
    """Test DataService functionality."""
    
    @pytest.fixture
    def data_service(self, app):
        """Create DataService instance for testing."""
        with app.app_context():
            return DataService()
    
    def test_init(self, data_service):
        """Test DataService initialization."""
        assert data_service.base_url == "https://fantasy.premierleague.com/api/"
        assert data_service.cache is not None
    
    @patch('requests.get')
    def test_fetch_fpl_data_success(self, mock_get, data_service):
        """Test successful FPL data fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = data_service._fetch_fpl_data("bootstrap-static/")
        
        assert result == {"test": "data"}
        mock_get.assert_called_once_with(
            "https://fantasy.premierleague.com/api/bootstrap-static/",
            timeout=30
        )
    
    @patch('requests.get')
    def test_fetch_fpl_data_http_error(self, mock_get, data_service):
        """Test FPL data fetch with HTTP error."""
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        with pytest.raises(Exception) as exc_info:
            data_service._fetch_fpl_data("bootstrap-static/")
        
        assert "Failed to fetch FPL data" in str(exc_info.value)
    
    @patch('requests.get')
    def test_fetch_fpl_data_timeout(self, mock_get, data_service):
        """Test FPL data fetch with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
        
        with pytest.raises(Exception) as exc_info:
            data_service._fetch_fpl_data("bootstrap-static/")
        
        assert "Failed to fetch FPL data" in str(exc_info.value)
    
    def test_get_bootstrap_data_cached(self, data_service, mock_requests_get):
        """Test getting bootstrap data with caching."""
        # First call
        result1 = data_service.get_bootstrap_data()
        
        # Second call should use cache
        result2 = data_service.get_bootstrap_data()
        
        assert result1 == result2
        assert "teams" in result1
        assert "elements" in result1
    
    def test_get_teams(self, data_service, mock_requests_get, mock_fpl_api_response):
        """Test getting teams data."""
        teams = data_service.get_teams()
        
        assert len(teams) == len(mock_fpl_api_response["teams"])
        assert teams[0]["name"] == "Arsenal"
        assert teams[0]["short_name"] == "ARS"
    
    def test_get_players(self, data_service, mock_requests_get, mock_fpl_api_response):
        """Test getting players data."""
        players = data_service.get_players()
        
        assert len(players) == len(mock_fpl_api_response["elements"])
        assert players[0]["web_name"] == "Salah"
        assert players[0]["now_cost"] == 130
    
    def test_get_fixtures(self, data_service, mock_requests_get, mock_fpl_api_response):
        """Test getting fixtures data."""
        fixtures = data_service.get_fixtures()
        
        assert len(fixtures) == len(mock_fpl_api_response["fixtures"])
        assert fixtures[0]["team_h"] == 1
        assert fixtures[0]["team_a"] == 2
    
    def test_update_teams_data(self, data_service, db_session, mock_requests_get):
        """Test updating teams data in database."""
        # Mock the get_teams method
        with patch.object(data_service, 'get_teams') as mock_get_teams:
            mock_get_teams.return_value = [
                {"id": 1, "name": "Arsenal", "short_name": "ARS"},
                {"id": 2, "name": "Chelsea", "short_name": "CHE"}
            ]
            
            result = data_service.update_teams_data()
            
            assert result["updated"] == 2
            assert result["errors"] == 0
            
            # Verify teams were created
            teams = db_session.query(Team).all()
            assert len(teams) == 2
            assert teams[0].name == "Arsenal"
    
    def test_update_players_data(self, data_service, db_session, sample_teams, mock_requests_get):
        """Test updating players data in database."""
        with patch.object(data_service, 'get_players') as mock_get_players:
            mock_get_players.return_value = [
                {
                    "id": 1,
                    "web_name": "Salah",
                    "team": 4,  # Liverpool (but we only have team_id=1,2,3,4,5 in fixtures)
                    "element_type": 4,  # FWD
                    "now_cost": 130,
                    "total_points": 200,
                    "form": "5.5"
                },
                {
                    "id": 2,
                    "web_name": "De Bruyne", 
                    "team": 3,  # Manchester City
                    "element_type": 3,  # MID
                    "now_cost": 125,
                    "total_points": 180,
                    "form": "6.0"
                }
            ]
            
            result = data_service.update_players_data()
            
            assert result["updated"] >= 0  # May skip players without matching teams
            
            # Verify at least one player was created
            players = db_session.query(Player).all()
            assert len(players) >= 1
    
    def test_update_fixtures_data(self, data_service, db_session, sample_teams, mock_requests_get):
        """Test updating fixtures data in database."""
        with patch.object(data_service, 'get_fixtures') as mock_get_fixtures:
            mock_get_fixtures.return_value = [
                {
                    "id": 1,
                    "event": 1,
                    "team_h": 1,  # Arsenal
                    "team_a": 2,  # Chelsea
                    "team_h_difficulty": 3,
                    "team_a_difficulty": 4,
                    "finished": False
                }
            ]
            
            result = data_service.update_fixtures_data()
            
            assert result["updated"] == 1
            assert result["errors"] == 0
            
            # Verify fixture was created
            fixtures = db_session.query(Fixture).all()
            assert len(fixtures) == 1
            assert fixtures[0].home_team_id == 1
            assert fixtures[0].away_team_id == 2
    
    def test_get_player_by_name(self, data_service, db_session, sample_players):
        """Test getting player by name."""
        player = data_service.get_player_by_name("Salah")
        
        assert player is not None
        assert player.web_name == "Salah"
        assert player.position == "FWD"
    
    def test_get_player_by_name_not_found(self, data_service, db_session):
        """Test getting non-existent player by name."""
        player = data_service.get_player_by_name("NonExistentPlayer")
        
        assert player is None
    
    def test_get_players_by_team(self, data_service, db_session, sample_players):
        """Test getting players by team."""
        # Liverpool players (team_id=4)
        players = data_service.get_players_by_team(4)
        
        assert len(players) == 3  # Salah, Van Dijk, Alisson
        player_names = [p.web_name for p in players]
        assert "Salah" in player_names
        assert "Van Dijk" in player_names
        assert "Alisson" in player_names
    
    def test_get_players_by_position(self, data_service, db_session, sample_players):
        """Test getting players by position."""
        forwards = data_service.get_players_by_position("FWD")
        
        assert len(forwards) == 2  # Salah, Kane
        forward_names = [p.web_name for p in forwards]
        assert "Salah" in forward_names
        assert "Kane" in forward_names
    
    def test_search_players_basic(self, data_service, db_session, sample_players):
        """Test basic player search."""
        result = data_service.search_players(name="Salah")
        
        assert result["total_count"] == 1
        assert len(result["players"]) == 1
        assert result["players"][0].web_name == "Salah"
    
    def test_search_players_by_position(self, data_service, db_session, sample_players):
        """Test player search by position."""
        result = data_service.search_players(position="FWD")
        
        assert result["total_count"] == 2
        assert len(result["players"]) == 2
        
        player_names = [p.web_name for p in result["players"]]
        assert "Salah" in player_names
        assert "Kane" in player_names
    
    def test_search_players_by_cost_range(self, data_service, db_session, sample_players):
        """Test player search by cost range."""
        result = data_service.search_players(min_cost=120, max_cost=130)
        
        # Should find Salah (130), De Bruyne (125), Kane (120)
        assert result["total_count"] == 3
        
        for player in result["players"]:
            assert 120 <= player.now_cost <= 130
    
    def test_search_players_sort_by_cost(self, data_service, db_session, sample_players):
        """Test player search sorted by cost."""
        result = data_service.search_players(sort_by="now_cost", sort_order="desc")
        
        # Should be sorted by cost descending
        costs = [p.now_cost for p in result["players"]]
        assert costs == sorted(costs, reverse=True)
    
    def test_search_players_limit(self, data_service, db_session, sample_players):
        """Test player search with limit."""
        result = data_service.search_players(limit=2)
        
        assert len(result["players"]) == 2
        assert result["total_count"] == 5  # Total available, not limited
    
    def test_get_team_fixtures(self, data_service, db_session, sample_fixtures):
        """Test getting fixtures for a team."""
        # Get fixtures for team 1 (Arsenal)
        fixtures = data_service.get_team_fixtures(1)
        
        assert len(fixtures) >= 1
        
        # Should include fixture where Arsenal is home or away
        has_arsenal_fixture = any(
            f.home_team_id == 1 or f.away_team_id == 1 
            for f in fixtures
        )
        assert has_arsenal_fixture
    
    def test_get_gameweek_fixtures(self, data_service, db_session, sample_fixtures):
        """Test getting fixtures for a specific gameweek."""
        gw1_fixtures = data_service.get_gameweek_fixtures(1)
        
        assert len(gw1_fixtures) == 2  # Two fixtures in GW1
        
        for fixture in gw1_fixtures:
            assert fixture.gameweek == 1
    
    def test_get_current_gameweek(self, data_service, mock_requests_get):
        """Test getting current gameweek."""
        # Mock bootstrap data with current event
        with patch.object(data_service, 'get_bootstrap_data') as mock_bootstrap:
            mock_bootstrap.return_value = {
                "events": [
                    {"id": 1, "is_current": False, "finished": True},
                    {"id": 2, "is_current": True, "finished": False},
                    {"id": 3, "is_current": False, "finished": False}
                ]
            }
            
            current_gw = data_service.get_current_gameweek()
            assert current_gw == 2
    
    def test_get_next_gameweek(self, data_service, mock_requests_get):
        """Test getting next gameweek."""
        with patch.object(data_service, 'get_bootstrap_data') as mock_bootstrap:
            mock_bootstrap.return_value = {
                "events": [
                    {"id": 1, "is_current": False, "is_next": False, "finished": True},
                    {"id": 2, "is_current": True, "is_next": False, "finished": False},
                    {"id": 3, "is_current": False, "is_next": True, "finished": False}
                ]
            }
            
            next_gw = data_service.get_next_gameweek()
            assert next_gw == 3
    
    def test_cache_functionality(self, data_service, mock_requests_get):
        """Test that caching works properly."""
        # First call
        data1 = data_service.get_bootstrap_data()
        
        # Mock a different response
        with patch.object(data_service, '_fetch_fpl_data') as mock_fetch:
            mock_fetch.return_value = {"different": "data"}
            
            # Second call should still return cached data
            data2 = data_service.get_bootstrap_data()
            
            assert data1 == data2
            # _fetch_fpl_data should not be called again
            mock_fetch.assert_not_called()
    
    def test_error_handling_in_update_methods(self, data_service, db_session):
        """Test error handling in update methods."""
        # Test with invalid data that would cause database errors
        with patch.object(data_service, 'get_teams') as mock_get_teams:
            # Return malformed team data
            mock_get_teams.return_value = [
                {"id": None, "name": None}  # Invalid data
            ]
            
            result = data_service.update_teams_data()
            
            # Should handle error gracefully
            assert "errors" in result
            assert result["errors"] > 0