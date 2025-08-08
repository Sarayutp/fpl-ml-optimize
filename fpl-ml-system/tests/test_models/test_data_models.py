"""Tests for Pydantic data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.data_models import (
    PlayerStats, TeamData, OptimizedTeam, TransferSuggestion, 
    CaptainSuggestion, OptimizationRequest, PlayerSearchRequest,
    FixtureData, PlayerPredictionData, APIResponse
)


class TestPlayerStats:
    """Test PlayerStats model validation."""
    
    def test_valid_player_stats(self):
        """Test creating valid PlayerStats."""
        player_data = {
            "player_id": 1,
            "web_name": "Salah",
            "position": "FWD",
            "team_id": 4,
            "now_cost": 13.0,
            "expected_points": 8.2,
            "form": 5.5,
            "total_points": 200,
            "points_per_game": 6.7
        }
        
        player = PlayerStats(**player_data)
        assert player.player_id == 1
        assert player.web_name == "Salah"
        assert player.position == "FWD"
        assert player.now_cost == 13.0
    
    def test_invalid_position(self):
        """Test invalid position validation."""
        player_data = {
            "player_id": 1,
            "web_name": "Salah",
            "position": "INVALID",  # Invalid position
            "team_id": 4,
            "now_cost": 13.0,
            "expected_points": 8.2,
            "form": 5.5,
            "total_points": 200,
            "points_per_game": 6.7
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PlayerStats(**player_data)
        
        assert "pattern" in str(exc_info.value)
    
    def test_negative_cost(self):
        """Test negative cost validation."""
        player_data = {
            "player_id": 1,
            "web_name": "Salah",
            "position": "FWD",
            "team_id": 4,
            "now_cost": -1.0,  # Negative cost
            "expected_points": 8.2,
            "form": 5.5,
            "total_points": 200,
            "points_per_game": 6.7
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PlayerStats(**player_data)
        
        assert "greater than 0" in str(exc_info.value)
    
    def test_optional_fields(self):
        """Test optional fields work correctly."""
        player_data = {
            "player_id": 1,
            "web_name": "Salah",
            "position": "FWD",
            "team_id": 4,
            "now_cost": 13.0,
            "expected_points": 8.2,
            "form": 5.5,
            "total_points": 200,
            "points_per_game": 6.7,
            "expected_goals": 0.8,
            "expected_assists": 0.3,
            "minutes": 1800
        }
        
        player = PlayerStats(**player_data)
        assert player.expected_goals == 0.8
        assert player.expected_assists == 0.3
        assert player.minutes == 1800


class TestTeamData:
    """Test TeamData model validation."""
    
    def test_valid_team_data(self):
        """Test creating valid TeamData."""
        team_data = {
            "team_id": 1,
            "name": "Arsenal",
            "short_name": "ARS",
            "strength_overall_home": 4,
            "strength_overall_away": 3
        }
        
        team = TeamData(**team_data)
        assert team.team_id == 1
        assert team.name == "Arsenal"
        assert team.short_name == "ARS"
        assert team.strength_overall_home == 4
    
    def test_short_name_too_long(self):
        """Test short name validation."""
        team_data = {
            "team_id": 1,
            "name": "Arsenal",
            "short_name": "ARSENAL",  # Too long
            "strength_overall_home": 4,
            "strength_overall_away": 3
        }
        
        with pytest.raises(ValidationError):
            TeamData(**team_data)
    
    def test_invalid_strength_range(self):
        """Test strength validation."""
        team_data = {
            "team_id": 1,
            "name": "Arsenal",
            "short_name": "ARS",
            "strength_overall_home": 6,  # Out of range
            "strength_overall_away": 3
        }
        
        with pytest.raises(ValidationError):
            TeamData(**team_data)


class TestOptimizedTeam:
    """Test OptimizedTeam model validation."""
    
    def test_valid_optimized_team(self):
        """Test creating valid OptimizedTeam."""
        team_data = {
            "players": list(range(1, 16)),  # 15 players
            "captain_id": 1,
            "vice_captain_id": 2,
            "total_cost": 99.5,
            "expected_points": 65.2,
            "reasoning": "This team offers excellent balance between attack and defense."
        }
        
        team = OptimizedTeam(**team_data)
        assert len(team.players) == 15
        assert team.captain_id == 1
        assert team.vice_captain_id == 2
        assert team.total_cost == 99.5
    
    def test_wrong_number_of_players(self):
        """Test player count validation."""
        team_data = {
            "players": [1, 2, 3],  # Only 3 players
            "captain_id": 1,
            "vice_captain_id": 2,
            "total_cost": 99.5,
            "expected_points": 65.2,
            "reasoning": "This team offers excellent balance."
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OptimizedTeam(**team_data)
        
        assert "at least 15 items" in str(exc_info.value)
    
    def test_captain_not_in_players(self):
        """Test captain validation."""
        team_data = {
            "players": list(range(1, 16)),  # Players 1-15
            "captain_id": 20,  # Not in players list
            "vice_captain_id": 2,
            "total_cost": 99.5,
            "expected_points": 65.2,
            "reasoning": "This team offers excellent balance."
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OptimizedTeam(**team_data)
        
        assert "Captain must be one of the selected players" in str(exc_info.value)
    
    def test_same_captain_and_vice_captain(self):
        """Test captain and vice captain are different."""
        team_data = {
            "players": list(range(1, 16)),
            "captain_id": 1,
            "vice_captain_id": 1,  # Same as captain
            "total_cost": 99.5,
            "expected_points": 65.2,
            "reasoning": "This team offers excellent balance."
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OptimizedTeam(**team_data)
        
        assert "Vice captain must be different from captain" in str(exc_info.value)
    
    def test_over_budget(self):
        """Test budget validation."""
        team_data = {
            "players": list(range(1, 16)),
            "captain_id": 1,
            "vice_captain_id": 2,
            "total_cost": 101.0,  # Over budget
            "expected_points": 65.2,
            "reasoning": "This team offers excellent balance."
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OptimizedTeam(**team_data)
        
        assert "less than or equal to 100" in str(exc_info.value)


class TestOptimizationRequest:
    """Test OptimizationRequest model validation."""
    
    def test_valid_request(self):
        """Test creating valid OptimizationRequest."""
        request_data = {
            "budget": 95.0,
            "formation": "4-4-2",
            "preferred_players": [1, 2, 3],
            "excluded_players": [10, 11],
            "max_players_per_team": 3
        }
        
        request = OptimizationRequest(**request_data)
        assert request.budget == 95.0
        assert request.formation == "4-4-2"
        assert request.max_players_per_team == 3
    
    def test_invalid_formation_format(self):
        """Test formation format validation."""
        request_data = {
            "budget": 95.0,
            "formation": "442",  # Invalid format
            "max_players_per_team": 3
        }
        
        with pytest.raises(ValidationError):
            OptimizationRequest(**request_data)
    
    def test_invalid_formation_total(self):
        """Test formation total validation."""
        request_data = {
            "budget": 95.0,
            "formation": "4-4-3",  # Adds up to 11 instead of 10
            "max_players_per_team": 3
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OptimizationRequest(**request_data)
        
        assert "add up to 10 outfield players" in str(exc_info.value)
    
    def test_budget_range_validation(self):
        """Test budget range validation."""
        # Too low
        with pytest.raises(ValidationError):
            OptimizationRequest(budget=40.0)
        
        # Too high
        with pytest.raises(ValidationError):
            OptimizationRequest(budget=110.0)
    
    def test_default_values(self):
        """Test default values are set correctly."""
        request = OptimizationRequest()
        assert request.budget == 100.0
        assert request.max_players_per_team == 3
        assert request.include_reasoning is True


class TestPlayerSearchRequest:
    """Test PlayerSearchRequest model validation."""
    
    def test_valid_search_request(self):
        """Test creating valid PlayerSearchRequest."""
        search_data = {
            "name": "Salah",
            "position": "FWD",
            "team_id": 4,
            "min_cost": 10.0,
            "max_cost": 15.0,
            "min_points": 100,
            "sort_by": "expected_points",
            "sort_order": "desc",
            "limit": 50
        }
        
        search = PlayerSearchRequest(**search_data)
        assert search.name == "Salah"
        assert search.position == "FWD"
        assert search.limit == 50
    
    def test_invalid_position(self):
        """Test invalid position validation."""
        with pytest.raises(ValidationError):
            PlayerSearchRequest(position="INVALID")
    
    def test_invalid_sort_by(self):
        """Test invalid sort_by validation."""
        with pytest.raises(ValidationError):
            PlayerSearchRequest(sort_by="invalid_field")
    
    def test_invalid_sort_order(self):
        """Test invalid sort_order validation."""
        with pytest.raises(ValidationError):
            PlayerSearchRequest(sort_order="invalid_order")
    
    def test_limit_validation(self):
        """Test limit validation."""
        # Too high
        with pytest.raises(ValidationError):
            PlayerSearchRequest(limit=200)
        
        # Too low
        with pytest.raises(ValidationError):
            PlayerSearchRequest(limit=0)
    
    def test_default_values(self):
        """Test default values."""
        search = PlayerSearchRequest()
        assert search.sort_by == "expected_points"
        assert search.sort_order == "desc"
        assert search.limit == 20


class TestFixtureData:
    """Test FixtureData model validation."""
    
    def test_valid_fixture(self):
        """Test creating valid FixtureData."""
        fixture_data = {
            "fixture_id": 1,
            "gameweek": 15,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_difficulty": 3,
            "away_difficulty": 4,
            "kickoff_time": datetime.now(),
            "finished": False
        }
        
        fixture = FixtureData(**fixture_data)
        assert fixture.fixture_id == 1
        assert fixture.gameweek == 15
        assert fixture.home_difficulty == 3
    
    def test_gameweek_validation(self):
        """Test gameweek validation."""
        # Too low
        with pytest.raises(ValidationError):
            FixtureData(
                fixture_id=1, gameweek=0, home_team_id=1, away_team_id=2
            )
        
        # Too high
        with pytest.raises(ValidationError):
            FixtureData(
                fixture_id=1, gameweek=39, home_team_id=1, away_team_id=2
            )
    
    def test_difficulty_validation(self):
        """Test difficulty validation."""
        # Invalid home difficulty
        with pytest.raises(ValidationError):
            FixtureData(
                fixture_id=1, gameweek=1, home_team_id=1, away_team_id=2,
                home_difficulty=6  # Out of range
            )


class TestAPIResponse:
    """Test APIResponse model."""
    
    def test_success_response(self):
        """Test successful API response."""
        response = APIResponse(
            success=True,
            data={"players": []},
            message="Successfully retrieved players"
        )
        
        assert response.success is True
        assert response.data == {"players": []}
        assert response.message == "Successfully retrieved players"
        assert response.error is None
        assert isinstance(response.timestamp, datetime)
    
    def test_error_response(self):
        """Test error API response."""
        response = APIResponse(
            success=False,
            error="Player not found",
            message="Failed to retrieve player"
        )
        
        assert response.success is False
        assert response.error == "Player not found"
        assert response.data is None
    
    def test_different_data_types(self):
        """Test different data types in response."""
        # List data
        response1 = APIResponse(success=True, data=[1, 2, 3])
        assert response1.data == [1, 2, 3]
        
        # String data
        response2 = APIResponse(success=True, data="success")
        assert response2.data == "success"
        
        # Integer data
        response3 = APIResponse(success=True, data=42)
        assert response3.data == 42
        
        # Float data
        response4 = APIResponse(success=True, data=3.14)
        assert response4.data == 3.14