from typing import Tuple, Sequence, Dict, List
from .model import get_mock_projection, pythag_win, ProjectionRequest

Bracket = Sequence[Sequence[Tuple[str, str]]]
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
        
            top_pct, bottom_pct = pythag_win(
                *(await get_mock_projection(ProjectionRequest(
                    home_team_id=top_team_id,
                    away_team_id=bottom_team_id,
                    neutral=True
                )))
            )
            
            next_round_ver[top_team_id][0].append(top_pct)
            next_round_ver[top_team_id][1].append(bottom[bottom_team_id])
            
            next_round_ver[top_team_id][0].append(bottom_pct)
            next_round_ver[top_team_id][1].append(top[top_team_id])
            
    next_round : Dict[str, float] = {}        
    
    for team_id in next_round_ver:
        
        next_round[team_id] = weighted_avg(
            entries=next_round_ver[team_id][0],
            weights=next_round_ver[team_id][1]
        )  
            
    return next_round

async def expand_games(bracket : WinPctBracket)->WinPctBracket:
    
    cols = len(bracket[0])
    rows = len(bracket)
    
    for col_no in range(cols):
        for row_no in range(rows):
            
            next_round = await expand_next_round(
                bracket[row_no][col_no]
            )
            next_col_no = col_no + 1
            next_row_no = get_offset(row_no=row_no, col_no=col_no)
            top_or_bottom = should_leader_be_up(row_no=row_no, col_no=col_no)
            
            bracket[next_col_no][next_row_no][top_or_bottom] = next_round
            
    return bracket

async def get_teams_by_round(
    bracket : WinPctBracket
)->TeamsByRoundBracket:
    
    by_round : TeamsByRoundBracket = {}
    
    cols = len(bracket[0])
    rows = len(bracket)
    
    for col_no in range(cols):
        for row_no in range(rows):
            
            top_teams, bottom_teams = bracket[row_no][col_no]
            
            for top_team_id in top_teams:
                
                by_round[top_team_id][col_no] = top_teams[top_team_id]

            for bottom_team_id in bottom_teams:
                
                by_round[bottom_team_id][col_no] = bottom_teams[bottom_team_id]
                
    return by_round

async def form_win_pct_bracket(bracket : Bracket)->WinPctBracket:
    
    cols = len(bracket[0])
    rows = len(bracket)
    
    win_pct_bracket : WinPctBracket = [[] for row in range(rows)]
    
    for row in range(0, rows, 2):
        win_pct_bracket[row] = [
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

    
            