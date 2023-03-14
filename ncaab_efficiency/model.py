from datetime import datetime, timedelta
from typing import List, Dict, Optional
from gdg_model_builder import Model, \
    private, session, spiodirect, universal, \
    poll, days, secs, dow, Event, root, Init
from pydantic import BaseModel
import csv
import json
from ncaab_efficiency.stats import get_possession_from_statline
import redis
from typing import Tuple, Sequence, Dict, List
import math
from ncaab_efficiency.hardcode import full_example
from functools import lru_cache

Bracket = List[List[Tuple[Optional[str], Optional[str]]]]
WinPctBracket = List[List[
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
    rows = len(bracket)
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

async def to_rows(bracket : TeamsByRoundBracket)->List[Dict]:
    
    rows = []
    for team_id in bracket:
        d = bracket[team_id]
        d["id"] = team_id
        rows.append(d)
       
    return rows

async def e2e_bracket_by_round(bracket : Bracket)->TeamsByRoundBracket:
    
    win_pct = await form_win_pct_bracket(bracket)
    win_pct = await expand_games(win_pct)
    return await get_teams_by_round(win_pct)

WRITE_BACKUPS : bool = False
UTL_FLAG=False
UTC_PLUS_PST=1000*60*60*11 # 4 AM PST

def get_projection(home_tempo: float, away_tempo: float, tempo_avg: float, home_oe: float, away_de: float, away_oe: float, home_de: float, ppp_avg: float , neutral : bool = False):

    proj_tempo = home_tempo + away_tempo - tempo_avg
    if neutral:
        home_projection = (proj_tempo*((1.12 * home_oe) + (.88 * away_de) - ppp_avg))/100
        away_projection = (proj_tempo*((1.12 * away_oe) + (.88 * home_de) - ppp_avg))/100
        return (home_projection, away_projection)
        
    home_projection = (proj_tempo*((1.014 * 1.12 * home_oe) + (1.014 * .88 * away_de) - ppp_avg))/100
    away_projection = (proj_tempo*((0.986  * 1.12 * away_oe) + (0.986 * .88 * home_de) - ppp_avg))/100
    return (home_projection, away_projection)

GAME_LOG_OUT = False

def get_game_t(tempo: float, oppontent_tempo: float, tempo_avg: float, possessions: float):
    
    if possessions < 1:
        return tempo
    
    proj_tempo = tempo + oppontent_tempo - tempo_avg
    factor = (1 + (possessions - proj_tempo)/(2 * possessions)) 
    game_t = tempo * factor
    
    return game_t

def get_weight_e(n_games: int):
    if n_games <= 23:
        weight = .04*n_games
    else: 
        weight = .94
    return weight

def get_weight_t(n_games: int):
    if n_games <= 13:
        weight = .07*n_games
    else:
        weight = .94
    return weight

def get_new_e(preseason_oe: float, preseason_de: float, avg_game_oe: float, avg_game_de: float, weight: float):
    oe = ((1-weight)*preseason_oe + weight*(avg_game_oe))
    de = ((1-weight)*preseason_de + weight*(avg_game_de)) 
    # print("Preseason coefficient: ",  1-weight, oe, de, preseason_de, preseason_oe, avg_game_de, avg_game_oe)
    return (oe, de)

def get_new_tempo(preseason_t: float, avg_game_t: float, weight: float):
    return ((1-weight)*preseason_t) + (weight*(avg_game_t))

class RadarDetail(BaseModel):
    
    class Config:
        extra = "ignore" # teall pydantic to ignore the extra fields
    
    FieldGoalsMade : int = 0
    FieldGoalsAttempted : int = 0
    TwoPointersMade : int = 0
    TwoPointersAttempted : int = 0
    TwoPointersPercentage : float = 0
    ThreePointersMade : int = 0
    ThreePointersAttempted : int = 0
    FreeThrowsMade : int = 0
    FreeThrowsAttempted : int = 0
    OffensiveRebounds : int = 0
    DefensiveRebounds : int = 0
    Rebounds : int = 0
    Assists : int = 0
    Steals : int = 0
    BlockedShots : int = 0
    Turnovers : int = 0
    PersonalFouls : int = 0
    Points : Optional[int] = 0
    TrueShootingAttempts : float = 0

class RadarEntry(BaseModel):
    team_id : int
    offense : RadarDetail
    defense : RadarDetail
    
class TrendDetail(BaseModel):
    last_rank : Optional[int]
    current_rank : int
    
class TrendEntry(BaseModel):
    team_id : int
    ap : TrendDetail
    gdg_power_rating : TrendDetail

class ProjectionEntry(BaseModel):
    game_id : int
    home_team_id : int
    away_team_id : int
    home_team_score : float
    away_team_score : float

class EfficiencyEntry(BaseModel):
    team_id : int
    oe : float
    de : float
    tempo : float

class GameEfficiencyEntry(BaseModel):
    team_id : int
    game_id : int
    game_oe : float
    game_de : float
    tempo : float

ncaab_efficiency = Model(
    cron_window=1
)

def get_median_efficiency_entry(team_id : int):
    return EfficiencyEntry(
        team_id = team_id,
        oe = 70.0,
        de = 70.0,
        tempo = 70.0
    )
    
def get_median_game_efficiency_entry(team_id : int, game_id : int):
    return GameEfficiencyEntry(
        team_id = team_id,
        game_id=game_id,
        game_oe = 70.0,
        game_de = 70.0,
        tempo = 70.0
    )

def get_seed_league_efficiency()->Dict[str, EfficiencyEntry]:
    seed_table : Dict[str, EfficiencyEntry] = dict()
    with open("./preseason_league_efficiency.csv") as f:
        for entry in csv.DictReader(f):
            seed_table[entry["id"]] = EfficiencyEntry(
                team_id = entry.get("id") or -1,
                oe = entry.get("oe") or 50.0,
                de = entry.get("de") or 50.0,
                tempo = entry.get("tempo") or 50.0
            )
    return seed_table

@ncaab_efficiency.task(e = Init)
async def init_ncaab(e):
    # trigger again again
    preseason_data = get_seed_league_efficiency()
    await set_preseason_league_efficiency_table(root, preseason_data)
    await set_league_efficiency_table(root, preseason_data)
    await set_game_efficiency_tables(root, {})
    await set_projection_table(root, {})
    await set_radar_table(root, {})
    await set_trend_table(root, {})
    print("Finished initializing NCAAB EFFICIENCY MODEL")
    
class ProjectionRequest(BaseModel):
    away_team_id : str
    home_team_id : str
    neutral : bool
    
# TODO: revisit ncaab_efficiency 
@ncaab_efficiency.method(a=ProjectionRequest, r=ProjectionEntry)
async def get_mock_projection(a : ProjectionRequest)->ProjectionEntry:
    
    # fix league efficiency at start of iteration
    eff = await get_league_efficiency_table(root)

    tempos = []
    ppps = []
    for _, item in eff.items():
        tempos.append(item.tempo)
        ppps.append(item.oe)
        ppps.append(item.de)
    tempo_avg = sum(tempos)/len(tempos)
    ppp_avg = sum(ppps)/len(ppps)
    
    
    
    home_projection, away_projection = get_projection(
        eff[a.home_team_id].tempo,
        eff[a.away_team_id].tempo,
        tempo_avg,
        eff[a.home_team_id].oe,  # TODO: get from efficiency and home id
        eff[a.away_team_id].de, # TODO: get from efficiency and away id
        eff[a.away_team_id].oe, # TODO: get from efficiency and away id
        eff[a.home_team_id].de, # TODO: get from efficiency and home id
        ppp_avg, # TODO: computed above
        a.neutral
    )
    
    return ProjectionEntry(
        game_id=-1,
        home_team_id=int(a.home_team_id),
        away_team_id=int(a.away_team_id),
        home_team_score=home_projection,
        away_team_score=away_projection
    )
    
class BracketRequest(BaseModel):
    id : int
    
# TODO: revisit ncaab_efficiency 

@lru_cache(4)
async def get_main_bracket():
    return await to_rows(await e2e_bracket_by_round(full_example))

@ncaab_efficiency.method(a=BracketRequest, r=TeamsByRoundBracket)
async def get_bracket_by_round(a : Bracket)->TeamsByRoundBracket:
    
   return await get_main_bracket()

@ncaab_efficiency.get("projection_table", universal, t=Dict[str, ProjectionEntry])
async def get_projection_table(context, value):
    return value

@ncaab_efficiency.set("projection_table", universal, private, t=Dict[str, ProjectionEntry])
async def set_projection_table(context, value):
    return value

@ncaab_efficiency.task(valid=days(1, at=UTC_PLUS_PST))
async def iterate_projection_table(event):

    # fix league efficiency at start of iteration
    eff = await get_league_efficiency_table(root)
    pre_eff = await get_preseason_league_efficiency_table(root)
    eff_out = eff.copy()
   
    ptable = await get_projection_table(root)
    ptable_out = ptable.copy()  # ! use this if you want eff to remain to the same throughout iteration
   
    # get games from sportsdataio
    lookahead = timedelta(days=7)
    iter_date = datetime.fromtimestamp(float(event.ts)/1000)
    print("Iterating on...", float(event.ts), iter_date)
    end_date = iter_date + lookahead

    tempos = []
    for _, item in eff_out.items():
        tempos.append(item.tempo)
    tempo_avg = sum(tempos)/len(tempos)

    ppps = []
    for _, item in eff_out.items():
        ppps.append(item.oe)
        ppps.append(item.de)
    ppp_avg = sum(ppps)/len(ppps)

    while iter_date < end_date:
        iter_date += timedelta(days=1)
        games = spiodirect.ncaab.games_by_date.get_games(iter_date)
        for game in games:
            
            """
            if game.NeutralVenue:
                print("Handling neutral game...", game.HomeTeam, game.AwayTeam, game.NeutralVenue)
            """
            
            # TODO:START I believe these are the same
            if (str(game.HomeTeamID) not in pre_eff) or (str(game.AwayTeamID) not in pre_eff):
                continue
            if not eff_out.get(str(game.AwayTeamID)) or not eff_out.get(str(game.HomeTeamID)):
                continue
             # TODO:END
            
            if str(game.HomeTeamID) not in eff_out:
                eff_out[str(game.HomeTeamID)] = get_median_efficiency_entry(game.HomeTeamID)
                
            if str(game.AwayTeamID) not in eff_out:
                eff_out[str(game.AwayTeamID)] = get_median_efficiency_entry(game.AwayTeamID)
        
            home_team_score, away_team_score = get_projection(
                eff_out[str(game.HomeTeamID)].tempo, 
                eff_out[str(game.AwayTeamID)].tempo, 
                tempo_avg, 
                eff_out[str(game.HomeTeamID)].oe, 
                eff_out[str(game.AwayTeamID)].de,
                eff_out[str(game.AwayTeamID)].oe, 
                eff_out[str(game.HomeTeamID)].de, 
                ppp_avg, 
                game.NeutralVenue
            )
            
            if game.HomeTeam == "PORT" or game.AwayTeam == "PORT":
                print("PORT: ", game.GameID, home_team_score, away_team_score)
            
            # ? ptable_out[game_id] = ...
            ptable_out[game.GameID] = ProjectionEntry(
                game_id = game.GameID,
                home_team_id = game.HomeTeamID,
                away_team_id = game.AwayTeamID,
                home_team_score = home_team_score,
                away_team_score = away_team_score
            )
            
    out_dict = dict()
    for key, value in ptable_out.items():
        out_dict[key] = value.dict()
    await set_projection_table(root, ptable_out)

@ncaab_efficiency.get("league_effiency_table", universal, t=Dict[str, EfficiencyEntry])
async def get_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.set("league_effiency_table", universal, private, t=Dict[str, EfficiencyEntry])
async def set_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.get("preseason_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
async def get_preseason_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.set("preseason_league_efficiency_table", universal, private, t=Dict[str, EfficiencyEntry])
async def set_preseason_league_efficiency_table(context,value):
    return value

@ncaab_efficiency.get("manual_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
async def get_manual_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.set("manual_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
async def set_manual_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.get("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, GameEfficiencyEntry]])
async def get_game_efficiency_tables(context, value):
    return value

@ncaab_efficiency.set("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, GameEfficiencyEntry]])
async def set_game_efficiency_tables(context, value):
    return value

def update_team_league_efficiency(*, 
    team_id : str,
    game : spiodirect.ncaab.games_by_date.GameByDatelike,                   
    eff_table : Dict[str, EfficiencyEntry],
    eff_table_out : Dict[str, EfficiencyEntry],
    pre_eff_table : Dict[str, EfficiencyEntry],
    game_eff_table : Dict[str, Dict[str, GameEfficiencyEntry]],
    game_eff_table_out : Dict[str, Dict[str, GameEfficiencyEntry]],
    team_stats : Dict[tuple[str, str], spiodirect.ncaab.game_stats_by_date.TeamGameStatsByDatelike],
    tempo_avg : float,
    ppp_avg : float
):
    
    # compute team averages
    game_oe = [eff.game_oe
    for eff in game_eff_table_out[team_id].values()]
    game_oe_avg = sum(game_oe)/len(game_oe)

    game_de = [eff.game_de
    for eff in game_eff_table_out[team_id].values()]
    game_de_avg = sum(game_de)/len(game_de)
    
    game_t = [eff.tempo
    for eff in game_eff_table_out[team_id].values()]
    game_t_avg = sum(game_t)/len(game_t)
    
    # compute the weights
    weight_e = get_weight_e(len(game_eff_table_out[team_id].items()))
    league_oe, league_de = get_new_e(pre_eff_table[team_id].oe, pre_eff_table[team_id].de, game_oe_avg, game_de_avg, weight_e)
    
    weight_t = get_weight_t(len(game_eff_table_out[team_id].items()))
    league_t = get_new_tempo(pre_eff_table[team_id].tempo, game_t_avg, weight_t)
    
    # update the efficiency entry
    eff_entry = EfficiencyEntry(
        team_id = int(team_id),
        oe = league_oe,
        de = league_de,
        tempo = league_t
    )

    eff_table_out[team_id] = eff_entry

def update_team_efficiencies(*, 
    game : spiodirect.ncaab.games_by_date.GameByDatelike,                   
    eff_table : Dict[str, EfficiencyEntry],
    eff_table_out : Dict[str, EfficiencyEntry],
    pre_eff_table : Dict[str, EfficiencyEntry],
    game_eff_table : Dict[str, Dict[str, GameEfficiencyEntry]],
    game_eff_table_out : Dict[str, Dict[str, GameEfficiencyEntry]],
    team_stats : Dict[tuple[str, str], spiodirect.ncaab.game_stats_by_date.TeamGameStatsByDatelike],
    tempo_avg : float,
    ppp_avg : float
):
    
    home_team_id = str(game.HomeTeamID)
    away_team_id = str(game.AwayTeamID)
    game_id = str(game.GameID)
    
    
    if (home_team_id not in eff_table) or (away_team_id not in eff_table):
        return
    
    # update the game efficiency entry
    # if there isn't already space for the game efficiency table, allocate it
    if home_team_id not in game_eff_table_out:
        game_eff_table_out[home_team_id] = {}
    if away_team_id not in game_eff_table_out:
        game_eff_table_out[away_team_id] = {}
    
    home_possessions = 70
    if (game_id, home_team_id) in team_stats:
        home_possessions = get_possession_from_statline(
            team_stats[(str(game.GameID), str(home_team_id))]
        )
    away_possessions = 70
    if (game_id, away_team_id) in team_stats:
        away_possessions = get_possession_from_statline(
            team_stats[(str(game.GameID), str(away_team_id))]
        )
    
    home_game_t = get_game_t(
        eff_table[home_team_id].tempo, 
        eff_table[away_team_id].tempo, 
        tempo_avg, home_possessions # TODO: possessions vs. home possesions, what's the diff?
    )
    
    away_game_t = get_game_t(
        eff_table[away_team_id].tempo, 
        eff_table[home_team_id].tempo, 
        tempo_avg, away_possessions # TODO: possessions vs. home possesions, what's the diff?
    )
        
    
    if (
        game.HomeTeamScore is not None and game.AwayTeamScore is not None
        and home_possessions > 0 and away_possessions > 0
    ):
        
        home_factor = 1.0 if game.NeutralVenue else 1.014
        away_factor = 1.0 if game.NeutralVenue else 0.986
        
        game_eff_table_out[home_team_id][game_id] = GameEfficiencyEntry(
            team_id = home_team_id,
            game_id = game.GameID,
            game_oe = 100 * ((game.HomeTeamScore/(home_possessions))/((home_factor * eff_table[away_team_id].de)/ppp_avg)),
            game_de = 100 * ((game.AwayTeamScore/(away_possessions))/((away_factor * eff_table[away_team_id].oe)/ppp_avg)),
            tempo = home_game_t
        )
        
        game_eff_table_out[away_team_id][game_id] = GameEfficiencyEntry(
            team_id = away_team_id,
            game_id = game.GameID,
            game_oe = 100 * ((game.AwayTeamScore/(away_possessions))/((away_factor * eff_table[home_team_id].de)/ppp_avg)),
            game_de = 100 * ((game.HomeTeamScore/(home_possessions))/((home_factor * eff_table[home_team_id].oe)/ppp_avg)),
            tempo = away_game_t
        )
        
        update_team_league_efficiency(
            game=game,
            team_id=home_team_id,
            eff_table=eff_table,
            eff_table_out=eff_table_out,
            pre_eff_table=pre_eff_table,
            game_eff_table=game_eff_table,
            game_eff_table_out=game_eff_table_out,
            team_stats=team_stats,
            tempo_avg=tempo_avg,
            ppp_avg=ppp_avg
        )
        
        update_team_league_efficiency(
            game=game,
            team_id=away_team_id,
            eff_table=eff_table,
            eff_table_out=eff_table_out,
            pre_eff_table=pre_eff_table,
            game_eff_table=game_eff_table,
            game_eff_table_out=game_eff_table_out,
            team_stats=team_stats,
            tempo_avg=tempo_avg,
            ppp_avg=ppp_avg
        )
    

    

@ncaab_efficiency.task(valid=days(1, at=UTC_PLUS_PST))
async def iterate_efficiency(e):
    iter_date = datetime.fromtimestamp(float(e.ts)/1000)
    print("Efficiency on...", float(e.ts), iter_date)
    
    # fix league efficiency at start of iteration
    eff = await get_league_efficiency_table(root)
    eff_out = eff.copy()
    pre_eff = await get_preseason_league_efficiency_table(root)
    game_effs = await get_game_efficiency_tables(root)
    game_effs_out = game_effs.copy()

    # Yesterday's games by date
    lookahead = timedelta(days=1)
    yesterday = datetime.fromtimestamp(float(e.ts)/1000) - lookahead
    yesterday_games = spiodirect.ncaab.games_by_date.get_games(yesterday)

    # Yesterday's game stats by date
    team_statlines = spiodirect.ncaab.get_game_stats_by_date(yesterday)
    team_stats : Dict[tuple[str, str], spiodirect.ncaab.game_stats_by_date.TeamGameStatsByDatelike] = dict()
    for statline in team_statlines:
        team_stats[(str(statline.GameID), str(statline.TeamID))] = statline

    tempos = []
    for _, item in eff.items():
        tempos.append(item.tempo)
    tempo_avg = sum(tempos)/len(tempos)
    
    ppps = [item.oe
    for _, item in eff.items()]
    ppp_avg = sum(ppps)/len(ppps)


    for game in yesterday_games:
        
        # home
        update_team_efficiencies(
            game=game,
            eff_table=eff,
            eff_table_out=eff_out,
            pre_eff_table=pre_eff,
            game_eff_table=game_effs,
            game_eff_table_out=game_effs_out,
            team_stats=team_stats,
            tempo_avg=tempo_avg,
            ppp_avg=ppp_avg
        )

        
    # merge 
    await set_game_efficiency_tables(root, game_effs_out)
    await set_league_efficiency_table(root, eff_out)

@ncaab_efficiency.get("radar_table", universal, t=Dict[str, RadarEntry])
async def get_radar_table(context, value):
    return value

@ncaab_efficiency.set("radar_table", universal, t=Dict[str, RadarEntry])
async def set_radar_table(context, value):
    return value

def handle_radar_for_statline(radar : Dict[str, RadarEntry], statline : spiodirect.ncaab.game_stats_by_date.TeamGameStatsByDate):
    """Takes a statline an makes updates to the radar table.

    Args:
        radar (Dict[str, RadarEntry]): _description_
        statline (spiodirect.ncaab.game_stats_by_date.TeamGameStatsByDate): _description_
    """
    
    statline_dict = statline.dict()
    
    team = radar.get(str(statline.TeamID)) or get_zero_radar(statline.TeamID)
    opponent = radar.get(str(statline.OpponentID)) or get_zero_radar(statline.OpponentID)
    
    team_updated_dict =  {
        k : v + statline_dict[k] for (k, v) in team.offense.dict().items()
    }
    radar[str(statline.TeamID)] = RadarEntry(
        team_id=statline.TeamID,
        offense=RadarDetail(**team_updated_dict),
        defense=team.defense # defense stays the same
    )
    
    opponent_updated_dict =  {
        k : v + statline_dict[k] for (k, v) in opponent.defense.dict().items()
    }
    radar[str(statline.OpponentID)] = RadarEntry(
        team_id=statline.OpponentID,
        offense=opponent.offense, # offense stays the same
        defense=RadarDetail(**opponent_updated_dict)
    )
    
def get_zero_radar(team_id : int):
    return RadarEntry(
        team_id=team_id,
        offense=RadarDetail(),
        defense=RadarDetail()
    )

@ncaab_efficiency.task(valid=days(1, at=UTC_PLUS_PST))
async def iterate_radar(e):
    
    # get state
    radar = await get_radar_table(root)
    radar_out = radar.copy()
    
    # Yesterday's statlines by date
    lookahead = timedelta(days=1)
    yesterday =  datetime.fromtimestamp(float(e.ts)/1000) - lookahead
    team_statlines = spiodirect.ncaab.get_game_stats_by_date(yesterday)
    for statline in team_statlines:
        handle_radar_for_statline(radar_out, statline)
        
    await set_radar_table(root, radar_out)
  
@ncaab_efficiency.get("trend_table", universal, t=Dict[str, TrendEntry])
async def get_trend_table(context, value):
    return value

@ncaab_efficiency.set("trend_table", universal, private, t=Dict[str, TrendEntry])
async def set_trend_table(context, value):
    return value
      
def compare_power_rating(a : EfficiencyEntry)->int:
    return  .56 * a.oe - .46 * a.de   

def compare_ap_rank(a : spiodirect.ncaab.team.Teamlike)->int:
    return  a.ApRank or 100

def get_max_trend(max : int, team_id : int):
    return TrendEntry(
        team_id=team_id,
        ap=TrendDetail(
            last_rank=None,
            current_rank=max
        ),
        gdg_power_rating=TrendDetail(
            last_rank=None,
            current_rank=max
        )
    )

def update_trend_for_game(
    game : spiodirect.ncaab.games_by_date.GameByDatelike,                   
    power_ratings_order : List[EfficiencyEntry],
    ap_rank_order : List[spiodirect.ncaab.team.Teamlike]
):
    pass

@ncaab_efficiency.task(valid=days(1, at=UTC_PLUS_PST))
async def iterate_trend(e):

    # get state
    eff = await get_league_efficiency_table(root)
    eff_out = eff.copy()
    trend = await get_trend_table(root)
    trend_out = trend.copy()
    teams = spiodirect.ncaab.get_teams()
    max_rank = len(eff_out.values())
    
    # Yesterday's games by date
    lookahead = timedelta(days=1)
    yesterday = datetime.fromtimestamp(float(e.ts)/1000) - lookahead
    yesterday_games = spiodirect.ncaab.games_by_date.get_games(yesterday)
    teams_yesterday  =  set()
    
    for game in yesterday_games:
        
        teams_yesterday.add(str(game.AwayTeamID))
        teams_yesterday.add(str(game.HomeTeamID))
    
    power_ratings_order : List[EfficiencyEntry] = sorted(eff_out.values(), key=compare_power_rating, reverse=True)
    for i, entry in enumerate(power_ratings_order):
        
        if str(entry.team_id) not in eff:
            continue
        
        last = trend_out.get(str(entry.team_id)) or get_max_trend(max_rank, entry.team_id) 
        
        if (
            (str(entry.team_id) not in yesterday_games) 
            and (i == last.gdg_power_rating.current_rank)
        ):
            continue
        
           
        trend_out[str(entry.team_id)] = TrendEntry(
            team_id=entry.team_id,
            ap=last.ap,
            gdg_power_rating=TrendDetail(
                last_rank=last.gdg_power_rating.current_rank,
                current_rank=i
            )
        )
        
            
    ap_rank_order : List[spiodirect.ncaab.team.Teamlike] = sorted(teams, key=compare_ap_rank)
    for i, entry in enumerate(ap_rank_order):
        
        if str(entry.TeamID) not in eff:
            continue
        
        last = trend_out.get(str(entry.TeamID)) or get_max_trend(max_rank, entry.TeamID)
        
        if (
            (str(entry.TeamID) not in yesterday_games) 
            and (i == last.ap.current_rank)
        ):
            continue
        
        trend_out[str(entry.TeamID)] = TrendEntry(
            team_id=entry.TeamID,
            ap=TrendDetail(
                last_rank=last.ap.current_rank,
                current_rank=i
            ),
            gdg_power_rating=last.gdg_power_rating
        )
    
    await set_trend_table(root, trend_out)

if __name__ == "__main__":
    ncaab_efficiency.retrodate = datetime.strptime("2022 11 6", "%Y %m %d").timestamp()
    # ncaab_efficiency.model_hostname = "nccab-efficiency"
    # ncaab_efficiency.cron_window = 60 * 60
    ncaab_efficiency.start()

