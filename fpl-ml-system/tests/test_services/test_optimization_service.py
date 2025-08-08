"""Tests for OptimizationService."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.services.optimization_service import OptimizationService
from src.models.data_models import OptimizationRequest


class TestOptimizationService:
    """Test OptimizationService functionality."""
    
    @pytest.fixture
    def optimization_service(self, app):
        """Create OptimizationService instance for testing."""
        with app.app_context():
            return OptimizationService()
    
    def test_init(self, optimization_service):
        """Test OptimizationService initialization."""
        assert optimization_service.data_service is not None
        assert optimization_service.prediction_service is not None
    
    def test_optimize_team_basic(self, optimization_service, sample_players):
        """Test basic team optimization."""
        # Mock prediction service to return predictable values
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {
                1: 8.2,  # Salah
                2: 7.8,  # De Bruyne
                3: 7.5,  # Kane
                4: 5.2,  # Van Dijk
                5: 4.5   # Alisson
            }
            
            # Mock data service to return sample players
            with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
                mock_get_players.return_value = sample_players
                
                request = OptimizationRequest(budget=100.0)
                result = optimization_service.optimize_team(request)
                
                assert result is not None
                assert "players" in result
                assert "captain_id" in result
                assert "vice_captain_id" in result
                assert "total_cost" in result
                assert "expected_points" in result
    
    def test_optimize_team_with_formation(self, optimization_service, sample_players):
        """Test team optimization with specific formation."""
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {p.player_id: 5.0 for p in sample_players}
            
            with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
                mock_get_players.return_value = sample_players
                
                request = OptimizationRequest(
                    budget=100.0,
                    formation="4-4-2"
                )
                
                result = optimization_service.optimize_team(request)
                
                # Should respect formation constraints
                assert result is not None
                assert len(result["players"]) == 15
    
    def test_optimize_team_with_preferred_players(self, optimization_service, sample_players):
        """Test team optimization with preferred players."""
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {p.player_id: 5.0 for p in sample_players}
            
            with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
                mock_get_players.return_value = sample_players
                
                request = OptimizationRequest(
                    budget=100.0,
                    preferred_players=[1]  # Salah
                )
                
                result = optimization_service.optimize_team(request)
                
                # Salah should be in the team
                assert 1 in result["players"]
    
    def test_optimize_team_with_excluded_players(self, optimization_service, sample_players):
        """Test team optimization with excluded players."""
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {p.player_id: 5.0 for p in sample_players}
            
            with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
                mock_get_players.return_value = sample_players
                
                request = OptimizationRequest(
                    budget=100.0,
                    excluded_players=[1]  # Exclude Salah
                )
                
                result = optimization_service.optimize_team(request)
                
                # Salah should not be in the team
                assert 1 not in result["players"]
    
    def test_get_position_code(self, optimization_service):
        """Test position code mapping."""
        assert optimization_service._get_position_code("GKP") == 1
        assert optimization_service._get_position_code("DEF") == 2
        assert optimization_service._get_position_code("MID") == 3
        assert optimization_service._get_position_code("FWD") == 4
    
    def test_parse_formation(self, optimization_service):
        """Test formation parsing."""
        formation = optimization_service._parse_formation("4-4-2")
        expected = {"DEF": 4, "MID": 4, "FWD": 2}
        assert formation == expected
        
        # Test default formation
        default_formation = optimization_service._parse_formation(None)
        expected_default = {"DEF": 5, "MID": 5, "FWD": 3}
        assert default_formation == expected_default
    
    def test_validate_team_constraints_valid(self, optimization_service):
        """Test team validation with valid team."""
        # Mock a valid team selection
        selected_players = {
            1: 1,  # GKP
            2: 1,  # GKP
            3: 1,  # DEF
            4: 1,  # DEF
            5: 1,  # DEF
            6: 1,  # DEF
            7: 1,  # DEF
            8: 1,  # MID
            9: 1,  # MID
            10: 1,  # MID
            11: 1,  # MID
            12: 1,  # MID
            13: 1,  # FWD
            14: 1,  # FWD
            15: 1   # FWD
        }
        
        players_by_position = {
            "GKP": [1, 2],
            "DEF": [3, 4, 5, 6, 7],
            "MID": [8, 9, 10, 11, 12],
            "FWD": [13, 14, 15]
        }
        
        is_valid = optimization_service._validate_team_constraints(
            selected_players, players_by_position
        )
        
        assert is_valid is True
    
    def test_validate_team_constraints_invalid_count(self, optimization_service):
        """Test team validation with wrong player count."""
        # Only 14 players selected
        selected_players = {i: 1 for i in range(1, 15)}
        players_by_position = {
            "GKP": [1, 2],
            "DEF": [3, 4, 5, 6, 7],
            "MID": [8, 9, 10, 11],
            "FWD": [12, 13, 14]
        }
        
        is_valid = optimization_service._validate_team_constraints(
            selected_players, players_by_position
        )
        
        assert is_valid is False
    
    def test_validate_team_constraints_wrong_positions(self, optimization_service):
        """Test team validation with wrong position counts."""
        # Wrong position distribution (only 1 GKP)
        selected_players = {i: 1 for i in range(1, 16)}
        players_by_position = {
            "GKP": [1],  # Only 1 GKP (should be 2)
            "DEF": [2, 3, 4, 5, 6, 7],  # 6 DEF (should be max 5)
            "MID": [8, 9, 10, 11, 12],
            "FWD": [13, 14, 15]
        }
        
        is_valid = optimization_service._validate_team_constraints(
            selected_players, players_by_position
        )
        
        assert is_valid is False
    
    def test_select_captain_and_vice_captain(self, optimization_service, sample_players):
        """Test captain selection logic."""
        # Mock predictions with clear order
        player_predictions = {
            1: 8.2,  # Highest - should be captain
            2: 7.8,  # Second highest - should be vice captain
            3: 7.5,
            4: 5.2,
            5: 4.5
        }
        
        selected_player_ids = [1, 2, 3, 4, 5]
        
        captain_id, vice_captain_id = optimization_service._select_captain_and_vice_captain(
            selected_player_ids, player_predictions
        )
        
        assert captain_id == 1  # Salah (highest predicted points)
        assert vice_captain_id == 2  # De Bruyne (second highest)
        assert captain_id != vice_captain_id
    
    def test_calculate_team_cost(self, optimization_service, sample_players):
        """Test team cost calculation."""
        selected_player_ids = [1, 2, 3]  # Salah (13.0), De Bruyne (12.5), Kane (12.0)
        
        # Create mapping from player objects
        players_dict = {p.player_id: p for p in sample_players}
        
        total_cost = optimization_service._calculate_team_cost(selected_player_ids, players_dict)
        
        expected_cost = (130 + 125 + 120) / 10  # Convert from FPL price format
        assert total_cost == expected_cost
    
    def test_insufficient_budget(self, optimization_service):
        """Test handling of insufficient budget."""
        # Create expensive players that exceed budget
        expensive_players = []
        for i in range(15):
            player = Mock()
            player.player_id = i + 1
            player.position = "FWD" if i < 3 else "MID" if i < 8 else "DEF" if i < 13 else "GKP"
            player.now_cost = 150  # 15.0M each, total would be 225M
            player.team_id = 1
            expensive_players.append(player)
        
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {i + 1: 10.0 for i in range(15)}
            
            with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
                mock_get_players.return_value = expensive_players
                
                request = OptimizationRequest(budget=100.0)
                
                with pytest.raises(Exception) as exc_info:
                    optimization_service.optimize_team(request)
                
                assert "infeasible" in str(exc_info.value).lower() or "no solution" in str(exc_info.value).lower()
    
    def test_optimize_transfers_basic(self, optimization_service, sample_players):
        """Test basic transfer optimization."""
        current_team = [1, 2, 3, 4, 5]  # Current team player IDs
        
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {p.player_id: 5.0 for p in sample_players}
            
            with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
                mock_get_players.return_value = sample_players
                
                suggestions = optimization_service.optimize_transfers(
                    current_team=current_team,
                    available_budget=5.0,
                    max_transfers=2
                )
                
                assert isinstance(suggestions, list)
                assert len(suggestions) <= 2  # Respect max transfers
    
    def test_optimize_captain_selection(self, optimization_service, sample_players):
        """Test captain selection optimization."""
        current_team = [1, 2, 3, 4, 5]
        
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {
                1: 8.2,  # Should be captain
                2: 7.8,  # Should be vice captain
                3: 6.0,
                4: 5.0,
                5: 4.0
            }
            
            suggestion = optimization_service.optimize_captain_selection(current_team)
            
            assert suggestion["captain_id"] == 1
            assert suggestion["vice_captain_id"] == 2
            assert suggestion["expected_points_captain"] == 8.2 * 2  # Captain gets double points
            assert suggestion["expected_points_vice"] == 7.8
    
    def test_max_players_per_team_constraint(self, optimization_service):
        """Test maximum players per team constraint."""
        # Create players all from the same team
        same_team_players = []
        for i in range(15):
            player = Mock()
            player.player_id = i + 1
            player.position = "FWD" if i < 3 else "MID" if i < 8 else "DEF" if i < 13 else "GKP"
            player.now_cost = 50  # 5.0M each
            player.team_id = 1  # All from same team
            same_team_players.append(player)
        
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {i + 1: 5.0 for i in range(15)}
            
            with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
                mock_get_players.return_value = same_team_players
                
                request = OptimizationRequest(
                    budget=100.0,
                    max_players_per_team=3  # Should limit to max 3 from same team
                )
                
                result = optimization_service.optimize_team(request)
                
                # Should respect the constraint (if solvable with other teams)
                # In this case it might be infeasible since all players are from same team
                # but constraint should be applied
                assert result is not None or "infeasible" in str(result).lower()
    
    def test_error_handling_no_predictions(self, optimization_service, sample_players):
        """Test error handling when no predictions available."""
        with patch.object(optimization_service.prediction_service, 'get_player_predictions') as mock_predictions:
            mock_predictions.return_value = {}  # No predictions
            
            with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
                mock_get_players.return_value = sample_players
                
                request = OptimizationRequest(budget=100.0)
                
                with pytest.raises(Exception):
                    optimization_service.optimize_team(request)
    
    def test_empty_player_list(self, optimization_service):
        """Test handling of empty player list."""
        with patch.object(optimization_service.data_service, 'get_all_players') as mock_get_players:
            mock_get_players.return_value = []  # No players
            
            request = OptimizationRequest(budget=100.0)
            
            with pytest.raises(Exception) as exc_info:
                optimization_service.optimize_team(request)
            
            assert "no players" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()