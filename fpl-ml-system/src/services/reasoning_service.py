"""Reasoning service for generating natural language explanations of FPL decisions."""

import logging
from typing import Dict, List, Optional, Tuple, Any
import random

from flask import current_app

from ..models.db_models import db, Player, Team, Fixture
from ..models.data_models import OptimizedTeam, TransferSuggestion, CaptainSuggestion


logger = logging.getLogger(__name__)


class ReasoningService:
    """Service for generating natural language explanations for FPL decisions."""
    
    def __init__(self, app=None):
        """Initialize reasoning service."""
        self.app = app
        
        # Thai language templates for authentic FPL experience
        self.templates = {
            'team_optimization': [
                "ทีมที่แนะนำมีประสิทธิภาพสูง ({efficiency:.2f} แต้มต่อล้าน) ด้วยงบประมาณ £{total_cost:.1f}M",
                "การจัดทีมนี้เน้นความคุ้มค่า โดยใช้งบ £{total_cost:.1f}M คาดหวังได้ {expected_points:.1f} แต้ม",
                "ทีมที่ปรับให้เหมาะสมแล้ว งบประมาณ £{total_cost:.1f}M ประสิทธิภาพ {efficiency:.2f} แต้ม/ล้าน"
            ],
            
            'top_player_reasoning': [
                "{player_name} คาดหวังได้ {expected_points:.1f} แต้ม จากฟอร์มที่ดีเยี่ยม ({form:.1f}) และราคาคุ้มค่า",
                "{player_name} เป็นตัวเลือกที่น่าสนใจด้วยคะแนนคาดหวัง {expected_points:.1f} และฟอร์มปัจจุบัน {form:.1f}",
                "แนะนำ {player_name} ที่คาดหวังได้ {expected_points:.1f} แต้ม เนื่องจากฟอร์มดีต่อเนื่อง"
            ],
            
            'transfer_reasoning': [
                "เปลี่ยน {player_out} ออกมาเป็น {player_in} เพื่อเพิ่มคะแนนคาดหวัง +{points_gain:.1f} แต้ม",
                "แนะนำโอน {player_in} แทน {player_out} ได้คะแนนเพิ่ม {points_gain:.1f} แต้ม ค่าใช้จ่าย {cost_change:+.1f}M",
                "การเปลี่ยนแปลงจาก {player_out} เป็น {player_in} จะให้ผลตอบแทนที่ดีขึ้น +{points_gain:.1f} แต้ม"
            ],
            
            'captain_reasoning': [
                "แนะนำให้เลือก {captain_name} เป็นกัปตัน เพราะมีโอกาสได้คะแนนสูง {expected_points:.1f} แต้ม",
                "{captain_name} เหมาะสมเป็นกัปตัน ด้วยฟอร์มที่ดีและคู่แข่งที่ไม่แข็ง คาดหวัง {expected_points:.1f} แต้ม",
                "กัปตันที่แนะนำคือ {captain_name} จากการวิเคราะห์ความน่าจะเป็นในการทำคะแนน"
            ],
            
            'formation_reasoning': [
                "โครงสร้าง {def_count}-{mid_count}-{fwd_count} เหมาะสมกับสถานการณ์ปัจจุบัน",
                "เลือกใช้แผน {def_count}-{mid_count}-{fwd_count} เพื่อสร้างสมดุลระหว่างการรุกและรับ",
                "การจัดวาง {def_count}-{mid_count}-{fwd_count} จะให้ความยืดหยุ่นในการเก็บคะแนน"
            ],
            
            'fixture_difficulty': [
                "คู่แข่งง่ายเฉลี่ย {avg_difficulty:.1f}/5 ทำให้มีโอกาสทำคะแนนได้ดี",
                "ความยากง่ายของเกมส์อยู่ในระดับ {avg_difficulty:.1f}/5 เหมาะสำหรับการทำคะแนน",
                "ฟิกเจอร์ที่เอื้ออำนวยกับระดับความยาก {avg_difficulty:.1f}/5"
            ],
            
            'budget_efficiency': [
                "เหลือเงิน £{remaining:.1f}M สำหรับการปรับแต่งในอนาคต",
                "งบประมาณถูกใช้อย่างมีประสิทธิภาพ เหลือ £{remaining:.1f}M",
                "การจัดการงบประมาณดี เหลือเงินสำรอง £{remaining:.1f}M"
            ],
            
            'position_analysis': [
                "แนวรุก ({fwd_count} คน) มีศักยภาพทำประตูสูง",
                "กองกลาง ({mid_count} คน) ช่วยสร้างจุดได้เปรียบในการเก็บพ้อยต์",
                "แนวรับ ({def_count} คน) มีโอกาสได้คลีนชีทจากคู่แข่งที่ไม่แข็ง"
            ]
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the reasoning service with Flask app."""
        self.app = app
    
    def generate_team_reasoning(self, optimization_result: Dict, 
                              player_data: Optional[Dict] = None) -> str:
        """
        Generate comprehensive natural language explanation for team optimization.
        
        Args:
            optimization_result: Result from OptimizationService
            player_data: Optional player data for enhanced reasoning
            
        Returns:
            Natural language explanation string
        """
        try:
            # Extract key information
            selected_players = optimization_result.get('players', [])
            total_cost = optimization_result.get('total_cost', 0)
            expected_points = optimization_result.get('expected_points', 0)
            budget_remaining = optimization_result.get('budget_remaining', 0)
            formation = optimization_result.get('formation', {})
            
            reasoning_parts = []
            
            # Calculate efficiency
            efficiency = expected_points / total_cost if total_cost > 0 else 0
            
            # Main team efficiency reasoning
            main_template = random.choice(self.templates['team_optimization'])
            main_reasoning = main_template.format(
                efficiency=efficiency,
                total_cost=total_cost,
                expected_points=expected_points
            )
            reasoning_parts.append(main_reasoning)
            
            # Get detailed player information if available
            if player_data is None and selected_players:
                player_data = self._get_player_reasoning_data(selected_players)
            
            # Top players reasoning
            if player_data:
                top_players = self._get_top_players(selected_players, player_data, limit=2)
                
                for player_id, player_info in top_players:
                    player_template = random.choice(self.templates['top_player_reasoning'])
                    player_reasoning = player_template.format(
                        player_name=player_info['web_name'],
                        expected_points=player_info['expected_points'],
                        form=player_info.get('form', 0)
                    )
                    reasoning_parts.append(player_reasoning)
            
            # Formation reasoning
            if formation:
                def_count = formation.get('DEF', 0)
                mid_count = formation.get('MID', 0) 
                fwd_count = formation.get('FWD', 0)
                
                if def_count > 0 and mid_count > 0 and fwd_count > 0:
                    formation_template = random.choice(self.templates['formation_reasoning'])
                    formation_reasoning = formation_template.format(
                        def_count=def_count,
                        mid_count=mid_count,
                        fwd_count=fwd_count
                    )
                    reasoning_parts.append(formation_reasoning)
            
            # Budget efficiency reasoning
            if budget_remaining > 0:
                budget_template = random.choice(self.templates['budget_efficiency'])
                budget_reasoning = budget_template.format(remaining=budget_remaining)
                reasoning_parts.append(budget_reasoning)
            
            # Fixture analysis if available
            fixture_analysis = optimization_result.get('fixture_analysis', {})
            if fixture_analysis:
                avg_difficulty = fixture_analysis.get('average_fixture_difficulty')
                if avg_difficulty and avg_difficulty <= 3:  # Only mention if favorable
                    fixture_template = random.choice(self.templates['fixture_difficulty'])
                    fixture_reasoning = fixture_template.format(avg_difficulty=avg_difficulty)
                    reasoning_parts.append(fixture_reasoning)
            
            # Combine all reasoning parts
            full_reasoning = " ".join(reasoning_parts)
            
            # Ensure minimum length
            if len(full_reasoning) < 50:
                fallback = f"ทีมที่แนะนำใช้งบ £{total_cost:.1f}M คาดหวัง {expected_points:.1f} แต้ม มีประสิทธิภาพ {efficiency:.2f} แต้มต่อล้าน"
                return fallback
            
            return full_reasoning
            
        except Exception as e:
            logger.error(f"Error generating team reasoning: {e}")
            return "ทีมที่แนะนำได้รับการปรับให้เหมาะสมแล้วตามหลักการวิเคราะห์ข้อมูล"
    
    def generate_transfer_reasoning(self, transfer_suggestion: TransferSuggestion,
                                  fixture_context: Optional[Dict] = None) -> str:
        """
        Generate reasoning for transfer suggestions.
        
        Args:
            transfer_suggestion: Transfer suggestion from OptimizationService
            fixture_context: Optional fixture context for enhanced reasoning
            
        Returns:
            Transfer reasoning explanation
        """
        try:
            player_out = transfer_suggestion.player_out
            player_in = transfer_suggestion.player_in
            points_gain = transfer_suggestion.expected_points_gain
            cost_change = transfer_suggestion.cost_change
            
            reasoning_parts = []
            
            # Main transfer reasoning
            transfer_template = random.choice(self.templates['transfer_reasoning'])
            main_reasoning = transfer_template.format(
                player_out=player_out.web_name,
                player_in=player_in.web_name,
                points_gain=points_gain,
                cost_change=cost_change
            )
            reasoning_parts.append(main_reasoning)
            
            # Additional context based on player attributes
            if player_in.form > player_out.form:
                reasoning_parts.append(
                    f"{player_in.web_name} มีฟอร์มที่ดีกว่า ({player_in.form:.1f} เทียบ {player_out.form:.1f})"
                )
            
            if cost_change < 0:
                reasoning_parts.append(
                    f"ประหยัดเงินได้ £{abs(cost_change):.1f}M สำหรับการพัฒนาทีมในอนาคต"
                )
            elif cost_change > 0:
                reasoning_parts.append(
                    f"การลงทุนเพิ่ม £{cost_change:.1f}M น่าจะคุ้มค่าจากคะแนนที่เพิ่มขึ้น"
                )
            
            # Fixture context if available
            if fixture_context:
                in_difficulty = fixture_context.get(player_in.player_id, {}).get('fixture_difficulty', 3)
                out_difficulty = fixture_context.get(player_out.player_id, {}).get('fixture_difficulty', 3)
                
                if in_difficulty < out_difficulty:
                    reasoning_parts.append(
                        f"{player_in.web_name} มีฟิกเจอร์ที่ง่ายกว่า (ระดับ {in_difficulty}/5)"
                    )
            
            # Position-specific reasoning
            position_benefits = self._get_position_transfer_benefits(player_in.position, player_out.position)
            if position_benefits:
                reasoning_parts.append(position_benefits)
            
            return " ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"Error generating transfer reasoning: {e}")
            return f"แนะนำเปลี่ยน {player_out.web_name} เป็น {player_in.web_name} เพื่อประสิทธิภาพที่ดีขึ้น"
    
    def generate_captain_reasoning(self, captain_suggestion: Dict,
                                 fixture_context: Optional[Dict] = None) -> str:
        """
        Generate reasoning for captain selection.
        
        Args:
            captain_suggestion: Captain suggestion from OptimizationService
            fixture_context: Optional fixture context
            
        Returns:
            Captain selection reasoning
        """
        try:
            captain_name = captain_suggestion.get('captain_name', 'Unknown')
            captain_points = captain_suggestion.get('captain_expected_points', 0)
            vice_name = captain_suggestion.get('vice_captain_name', 'Unknown')
            captain_id = captain_suggestion.get('captain_id')
            
            reasoning_parts = []
            
            # Main captain reasoning
            captain_template = random.choice(self.templates['captain_reasoning'])
            main_reasoning = captain_template.format(
                captain_name=captain_name,
                expected_points=captain_points
            )
            reasoning_parts.append(main_reasoning)
            
            # Fixture-based reasoning if available
            if fixture_context and captain_id:
                context = fixture_context.get(captain_id, {})
                
                if context.get('is_home'):
                    reasoning_parts.append(f"เล่นที่บ้านทำให้มีข้อได้เปรียบเพิ่มเติม")
                
                fixture_difficulty = context.get('fixture_difficulty', 3)
                if fixture_difficulty <= 2:
                    reasoning_parts.append(f"คู่แข่งไม่แข็ง (ระดับ {fixture_difficulty}/5) เพิ่มโอกาสทำคะแนน")
            
            # Vice captain mention
            reasoning_parts.append(f"รองกัปตัน {vice_name} เป็นทางเลือกสำรองที่ดี")
            
            # Get additional player context
            player_context = self._get_captain_context(captain_id)
            if player_context:
                reasoning_parts.append(player_context)
            
            return " ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"Error generating captain reasoning: {e}")
            return f"แนะนำ {captain_name} เป็นกัปตันจากการวิเคราะห์สถิติและฟอร์มปัจจุบัน"
    
    def generate_formation_reasoning(self, formation: Dict[str, int],
                                   selected_players: List[int],
                                   fixture_analysis: Optional[Dict] = None) -> str:
        """
        Generate reasoning for formation choice.
        
        Args:
            formation: Formation breakdown (e.g., {'DEF': 4, 'MID': 4, 'FWD': 2})
            selected_players: List of selected player IDs
            fixture_analysis: Optional fixture difficulty analysis
            
        Returns:
            Formation reasoning explanation
        """
        try:
            def_count = formation.get('DEF', 0)
            mid_count = formation.get('MID', 0)
            fwd_count = formation.get('FWD', 0)
            
            reasoning_parts = []
            
            # Main formation reasoning
            formation_template = random.choice(self.templates['formation_reasoning'])
            main_reasoning = formation_template.format(
                def_count=def_count,
                mid_count=mid_count,
                fwd_count=fwd_count
            )
            reasoning_parts.append(main_reasoning)
            
            # Position-specific analysis
            if def_count >= 4:
                def_template = random.choice(self.templates['position_analysis'])
                def_reasoning = def_template.format(def_count=def_count, mid_count=mid_count, fwd_count=fwd_count)
                reasoning_parts.append("เน้นแนวรับสำหรับความมั่นคงและโอกาสคลีนชีท")
            
            if mid_count >= 5:
                reasoning_parts.append("เน้นกองกลางเพื่อควบคุมเกมและสร้างโอกาส")
            
            if fwd_count >= 3:
                reasoning_parts.append("เน้นแนวรุกเพื่อเพิ่มโอกาสทำประตู")
            
            # Fixture-based formation reasoning
            if fixture_analysis:
                easy_fixtures = fixture_analysis.get('easy_fixtures', 0)
                hard_fixtures = fixture_analysis.get('hard_fixtures', 0)
                
                if easy_fixtures > hard_fixtures and fwd_count >= 3:
                    reasoning_parts.append("ฟิกเจอร์ง่ายหลายเกมส์เหมาะกับการเน้นแนวรุก")
                elif hard_fixtures > easy_fixtures and def_count >= 4:
                    reasoning_parts.append("ฟิกเจอร์ยากต้องเน้นความมั่นคงแนวรับ")
            
            return " ".join(reasoning_parts)
            
        except Exception as e:
            logger.error(f"Error generating formation reasoning: {e}")
            return f"โครงสร้าง {def_count}-{mid_count}-{fwd_count} เหมาะสมกับสถานการณ์ปัจจุบัน"
    
    def generate_comprehensive_analysis(self, optimization_result: Dict,
                                      transfer_suggestions: Optional[List] = None,
                                      fixture_context: Optional[Dict] = None) -> Dict[str, str]:
        """
        Generate comprehensive analysis combining all reasoning types.
        
        Args:
            optimization_result: Complete optimization result
            transfer_suggestions: Optional transfer suggestions
            fixture_context: Optional fixture context
            
        Returns:
            Dictionary with different types of reasoning
        """
        try:
            analysis = {}
            
            # Team optimization reasoning
            analysis['team_reasoning'] = self.generate_team_reasoning(optimization_result)
            
            # Formation reasoning
            formation = optimization_result.get('formation', {})
            selected_players = optimization_result.get('players', [])
            fixture_analysis = optimization_result.get('fixture_analysis', {})
            
            if formation:
                analysis['formation_reasoning'] = self.generate_formation_reasoning(
                    formation, selected_players, fixture_analysis
                )
            
            # Captain reasoning
            captain_info = {
                'captain_name': optimization_result.get('captain_name'),
                'captain_expected_points': optimization_result.get('captain_expected_points'),
                'vice_captain_name': optimization_result.get('vice_captain_name'),
                'captain_id': optimization_result.get('captain_id')
            }
            
            if captain_info['captain_name']:
                analysis['captain_reasoning'] = self.generate_captain_reasoning(
                    captain_info, fixture_context
                )
            
            # Transfer reasoning if available
            if transfer_suggestions:
                transfer_reasons = []
                for suggestion in transfer_suggestions[:3]:  # Top 3 suggestions
                    reason = self.generate_transfer_reasoning(suggestion, fixture_context)
                    transfer_reasons.append(reason)
                analysis['transfer_reasoning'] = " | ".join(transfer_reasons)
            
            # Overall summary - avoid circular reference by not passing analysis dict
            analysis['summary'] = self._generate_overall_summary(optimization_result, {})
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error generating comprehensive analysis: {e}")
            return {'summary': 'การวิเคราะห์ทีมแบบครอบคลุมพร้อมคำแนะนำที่เป็นประโยชน์'}
    
    def _get_player_reasoning_data(self, player_ids: List[int]) -> Dict:
        """Get player data needed for reasoning."""
        query = db.session.query(
            Player.player_id,
            Player.web_name,
            Player.position,
            Player.form,
            Player.total_points,
            Player.now_cost,
            Player.expected_goals,
            Player.expected_assists
        ).filter(
            Player.player_id.in_(player_ids)
        )
        
        player_data = {}
        for row in query.all():
            player_data[row.player_id] = {
                'web_name': row.web_name,
                'position': row.position,
                'form': float(row.form or 0),
                'total_points': row.total_points,
                'cost': row.now_cost / 10.0,
                'expected_goals': float(row.expected_goals or 0),
                'expected_assists': float(row.expected_assists or 0),
                'expected_points': float(row.form or 0) * 2  # Simplified estimation
            }
        
        return player_data
    
    def _get_top_players(self, player_ids: List[int], player_data: Dict, 
                        limit: int = 3) -> List[Tuple[int, Dict]]:
        """Get top players by expected points for reasoning."""
        player_scores = []
        
        for player_id in player_ids:
            if player_id in player_data:
                data = player_data[player_id]
                score = data.get('expected_points', 0) + data.get('form', 0)
                player_scores.append((player_id, data, score))
        
        # Sort by score descending
        player_scores.sort(key=lambda x: x[2], reverse=True)
        
        return [(pid, data) for pid, data, _ in player_scores[:limit]]
    
    def _get_position_transfer_benefits(self, position_in: str, position_out: str) -> str:
        """Get position-specific transfer benefits."""
        position_benefits = {
            'GKP': "ประตูดีช่วยเพิ่มโอกาสคลีนชีทและแต้มจากเซฟ",
            'DEF': "แนวรับมั่นคงช่วยเก็บคลีนชีทและมีโอกาสทำประตู",
            'MID': "กองกลางสร้างสรรค์ช่วยทำประตูและแอสซิสต์",
            'FWD': "แนวรุกคมช่วยเพิ่มโอกาสทำประตูและโบนัส"
        }
        
        return position_benefits.get(position_in, "")
    
    def _get_captain_context(self, captain_id: Optional[int]) -> str:
        """Get additional context for captain selection."""
        if not captain_id:
            return ""
        
        try:
            player = Player.query.get(captain_id)
            if not player:
                return ""
            
            context_parts = []
            
            # Form-based context
            form = float(player.form or 0)
            if form >= 7:
                context_parts.append("ฟอร์มร้อนแรงในช่วงนี้")
            elif form >= 5:
                context_parts.append("ฟอร์มค่อนข้างดี")
            
            # Position-based context
            position_context = {
                'FWD': "แนวรุกมีโอกาสทำประตูและได้โบนัสสูง",
                'MID': "กองกลางได้แต้มทั้งประตูและแอสซิสต์",
                'DEF': "แนวรับได้คลีนชีทและมีโอกาสทำประตู",
                'GKP': "ประตูเก็บคลีนชีทและแต้มจากเซฟ"
            }
            
            pos_context = position_context.get(player.position, "")
            if pos_context:
                context_parts.append(pos_context)
            
            return " ".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting captain context: {e}")
            return ""
    
    def _generate_overall_summary(self, optimization_result: Dict, analysis: Dict) -> str:
        """Generate overall summary of the analysis."""
        try:
            total_cost = optimization_result.get('total_cost', 0)
            expected_points = optimization_result.get('expected_points', 0)
            
            summary_parts = [
                f"ทีมที่แนะนำใช้งบ £{total_cost:.1f}M คาดหวัง {expected_points:.1f} แต้ม"
            ]
            
            # Add formation summary
            formation = optimization_result.get('formation', {})
            if formation:
                def_count = formation.get('DEF', 0)
                mid_count = formation.get('MID', 0)
                fwd_count = formation.get('FWD', 0)
                summary_parts.append(f"แผน {def_count}-{mid_count}-{fwd_count}")
            
            # Add captain summary
            captain_name = optimization_result.get('captain_name')
            if captain_name:
                summary_parts.append(f"กัปตัน {captain_name}")
            
            # Add transfer summary if available (skip to avoid circular reference)
            # Transfer reasoning will be added separately in the analysis dict
            
            return " ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error generating overall summary: {e}")
            return "สรุปการวิเคราะห์ทีมและคำแนะนำที่ครอบคลุม"