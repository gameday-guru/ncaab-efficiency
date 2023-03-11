from typing import Tuple, Sequence, Dict, List
from .model import get_mock_projection, pythag_win, ProjectionRequest

Bracket = Sequence[Sequence[Tuple[str, str]]]

def weighted_avg(entries : Sequence[float])->List[float]:
    sum = 0
    for entry in entries:
        sum += entry
    out = []
    for entry in entries:
        out.append(entry/sum) 
    return out
    

async def simulate_games(bracket : Bracket):
    
    opponent_pcts_by_round : Dict[str, Dict[int, Sequence[str]]] = {
        
    }
    
    pcts_by_round : Dict[str, Dict[int, Dict[str, Sequence[float]]]] = {
        
    }
    
    for i, round in enumerate(bracket):
        for game in round:
            home, away = game
            
            for possible_opponent in opponent_pcts_by_round[home][i]:
            
                pcts_by_round[away][i][possible_opponent], pcts_by_round[home][i][possible_opponent] = get_mock_projection(ProjectionRequest(
                    home_team_id=home,
                    away_team_id=possible_opponent
                ))
            
            for possible_opponent in opponent_pcts_by_round[away][i]:
            
                pcts_by_round[away][i][possible_opponent], pcts_by_round[home][i][possible_opponent] = get_mock_projection(ProjectionRequest(
                    home_team_id=possible_opponent,
                    away_team_id=away
                ))
                
    return pcts_by_round
            
            