from typing import Tuple, Sequence, Dict, List
from .model import get_mock_projection, ProjectionRequest, Optional
import math

Bracket = Sequence[Sequence[Tuple[Optional[str], Optional[str]]]]
WinPctBracket = Sequence[Sequence[
    Tuple[
        Dict[str, float],
        Dict[str, float]
    ]
]]
TeamsByRoundBracket = Dict[str, Dict[str, float]]

"""
/**
 * 
 * @param pos 
 * @returns 
 */
export const whichBracketWindow = (pos : {
    rowNo : number,
    colNo : number
}) : number =>{

    const colWindowSize = 2 ** (pos.colNo + 1); 
    return Math.floor(pos.rowNo/colWindowSize);

}

/**
 * 
 * @param pos 
 * @returns 
 */
export const shouldLeaderBeUp = (pos : {
    rowNo : number,
    colNo : number
}) : boolean =>{

    return (whichBracketWindow(pos) % 2) === 1;

}
"""

def which_bracket_window(*, row_no : int, col_no : int)->int:
    
    col_window_size = 2 ** (col_no + 1); 
    return row_no//col_window_size

def should_leader_be_up(*, row_no : int, col_no : int)->bool:
    return (which_bracket_window(row_no=row_no, col_no=col_no) % 2) == 1

def get_offset(*, row_no : int, col_no : int)->int:
    
    # const offset = 2 ** (kwargs.pos.colNo);
    offset = 2 ** col_no
    return -1 * offset \
        if should_leader_be_up(row_no=row_no, col_no=col_no) \
            else offset
    
NCAAB_EXPONENT = 11.5

def pythag_win(left_score : float, right_score : float)->Tuple[float, float]:
    left = left_score ** NCAAB_EXPONENT
    right = right_score ** NCAAB_EXPONENT
    total = left + right
    left_win = left/total
    return [left_win, 1-left_win]
    

def weighted_avg(
    *,
    entries : Sequence[float],
    weights : Sequence[float]
)->List[float]:
    
    sum = 0
    weight_sum = 0
    for i, entry in enumerate(entries):
        sum += entry * weights[i]
        weight_sum += weights[i]
    
    return sum/weight_sum
    
async def expand_next_round(
    top : Dict[str, float],
    bottom : Dict[str, float]
)->Dict[str, float]:
    
    next_round_ver : Dict[
        str,
        Tuple[
            List[float],
            List[float]
        ] 
    ] = {}
    
    for top_team_id in top:
        for bottom_team_id in bottom:
            
            projection_entry = await get_mock_projection(ProjectionRequest(
                home_team_id=top_team_id,
                away_team_id=bottom_team_id,
                neutral=True
            ))
            
            top_score = projection_entry.home_team_score
            bottom_score = projection_entry.away_team_score
        
            top_pct, bottom_pct = pythag_win(
                top_score,
                bottom_score
            )
            
            if top_team_id not in next_round_ver:
                next_round_ver[top_team_id] = [
                    [],
                    []
                ]
            next_round_ver[top_team_id][0].append(top_pct)
            next_round_ver[top_team_id][1].append(bottom[bottom_team_id])
            
            if bottom_team_id not in next_round_ver:
                next_round_ver[bottom_team_id] = [
                    [],
                    []
                ]
            next_round_ver[bottom_team_id][0].append(bottom_pct)
            next_round_ver[bottom_team_id][1].append(top[top_team_id])
            
    next_round : Dict[str, float] = {}        
    
    for team_id in next_round_ver:
        
        pct = .5
        if team_id in top:
            pct = top[team_id]
        elif team_id in bottom:
            pct = bottom[team_id]
        
        next_round[team_id] = pct * weighted_avg(
            entries=next_round_ver[team_id][0],
            weights=next_round_ver[team_id][1]
        )  
            
    return next_round

async def expand_games(bracket : WinPctBracket)->WinPctBracket:
    
    cols = len(bracket[0])
    rows = len(bracket)
    
    for col_no in range(cols):
        for row_no in range(rows):
            
            if bracket[row_no][col_no] is None:
                continue
            
            top, bottom = bracket[row_no][col_no]
            next_round = await expand_next_round(
                top, bottom
            )
            next_col_no = col_no + 1
            next_row_no = row_no + get_offset(row_no=row_no, col_no=col_no)
            top_or_bottom = should_leader_be_up(row_no=row_no, col_no=col_no)
    
            if next_col_no > cols - 1:
                continue
        
            if bracket[next_row_no][next_col_no] is None:
                bracket[next_row_no][next_col_no] = [
                    {},
                    {}
                ]
            bracket[next_row_no][next_col_no][top_or_bottom] = next_round
            
    return bracket

async def get_teams_by_round(
    bracket : WinPctBracket
)->TeamsByRoundBracket:
    
    by_round : TeamsByRoundBracket = {}
    
    cols = len(bracket[0])
    rows = len(bracket)
    
    for col_no in range(cols):
        for row_no in range(rows):
            
            if bracket[row_no][col_no] is None:
                continue
            
            top_teams, bottom_teams = bracket[row_no][col_no]
            
            for top_team_id in top_teams:
                
                if top_team_id not in by_round:
                    by_round[top_team_id] = {}
                
                by_round[top_team_id][col_no] = top_teams[top_team_id]

            for bottom_team_id in bottom_teams:
                
                if bottom_team_id not in by_round:
                    by_round[bottom_team_id] = {}
                
                by_round[bottom_team_id][col_no] = bottom_teams[bottom_team_id]
                
    return by_round

async def form_win_pct_bracket(bracket : Bracket)->WinPctBracket:
    
    # cols = len(bracket[0])
    rows = len(bracket) + 1
    cols = math.floor(math.log2(rows)) + 1
    
    win_pct_bracket : WinPctBracket = [[] for row in range(rows)]
    
    for row in range(0, rows):
        win_pct_bracket[row] = [None for col in range(cols)]
        if row % 2 == 0:
            win_pct_bracket[row][0] = [
                {
                    bracket[row][0][0] : 1.0
                },
                {
                    bracket[row][0][1] : 1.0
                }
            ]
        
    return win_pct_bracket

async def e2e_bracket_by_round(bracket : Bracket)->TeamsByRoundBracket:
    
    win_pct = await form_win_pct_bracket(bracket)
    win_pct = await expand_games(win_pct)
    return await get_teams_by_round(win_pct)

async def to_rows(bracket : TeamsByRoundBracket)->List[Dict]:
    
    rows = []
    for team_id in bracket:
        d = bracket[team_id]
        d["id"] = team_id
        rows.append(d)
       
    return rows
