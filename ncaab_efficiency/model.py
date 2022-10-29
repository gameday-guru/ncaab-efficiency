from datetime import datetime, timedelta
from typing import List, Dict
from gdg_model_builder import Model, \
    private, session, spiodirect, universal, \
    poll, days, secs, dow, Event, root
from pydantic import BaseModel

def get_ppp(pts: int, possessions: int):
    return pts/possessions

def get_game_efficiency(ppp_o: float, ppp_d: float, opp_de: float, opp_oe: float, ppp_avg: float):
    game_oe = = ppp_o/(opp_de/ppp_avg)
    game_de = ppp_d/(opp_oe/ppp_avg)
    return (game_oe, game_de)

def get_projection(tempo: float, opp_tempo: float, tempo_avg: float, oe: float, de: float, ppp_avg: float):
    proj_tempo = tempo + opp_tempo - tempo_avg
    return proj_tempo * (oe + de - ppp_avg)/100

def get_power_ranking(oe: float, de: float):
    return (.56)*oe + (.44)*de

def get_weight(n_games: int)
    if n_games <= 23:
        weight = .04*n_games
    else: 
        weight = .94
    return weight

def get_new_e(preseason_oe: float, preseason_de: float, avg_game_oe: float, avg_game_de: float, weight: float):
    oe = (1-weight)*preseason_oe + weight*(avg_game_oe)
    de = (1-weight)*preseason_de + weight*(avg_game_de)
    return (oe, de)

class ProjectionEntry(BaseModel):
    game_id : int
    home_team_id : int
    away_team_id : int
    home_team_score : float
    away_team_score : float

class EfficiencyEntry(BaseModel):
    team_id : int
    ppp_o : int
    ppp_d : int
    ppp_avg : float
    opp_de : float
    opp_oe : float


ncaab_efficiency = Model(cron_window=1)

@ncaab_efficiency.get("projection_table", universal, t=Dict[str, ProjectionEntry])
async def get_projection_table(context, value):
    return value

@ncaab_efficiency.set("projection_table", universal, private, t=Dict[str, ProjectionEntry])
async def set_projection_table(context, value):
    return value

@ncaab_efficiency.task(valid=days(1))
async def iterate_projection_table(event):
    
    # addended projection
    update : Dict[str, ProjectionEntry] = {}
    
    # fix league efficiency at start of iteration
    eff = await get_league_efficiency()
   
    # get games from sportsdataio
    lookahead = timedelta.days(7)
    iter_date = datetime.now()
    end_date = iter_date + lookahead
    while iter_date < end_date:
        games = spiodirect.ncaab.games_by_date.get_games(iter_date)
        # do what you need with the games...
        # get_league_efficiency
        # proj_tempo = tempo + opp_tempo - tempo_avg
        # projection = proj_tempo*(oe+de-ppp_avg)/100
        
    # TODO: Liam provide more performant redis bindings for this merge.
    # merge 
    await set_projection_table(root, {**update, **(await get_projection_table())})

@ncaab_efficiency.get("league_effiency_table", universal, t=Dict[str, EfficiencyEntry])
async def get_league_efficiency(context, value):
    return value

@ncaab_efficiency.set("league_effiency_table", universal, private, t=Dict[str, EfficiencyEntry])
async def set_league_efficiency(context, value):
    return value

@ncaab_efficiency.get("manual_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
async def set_league_table(context, value):
    return value

@ncaab_efficiency.set("manual_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
async def set_league_table(context, value):
    return value

@ncaab_efficiency.get("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, EfficiencyEntry]])
async def get_game_efficiency(context, value):
    return value

@ncaab_efficiency.set("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, EfficiencyEntry]])
async def set_game_efficiency(context, value):
    return value

@ncaab_efficiency.task(valid=days(1))
async def iterate_efficiency(context, value):
    
    # addended projection
    update : Dict[str, EfficiencyEntry] = {}
    
    # fix league efficiency at start of iteration
    eff = await get_league_efficiency()
   
    for team_id, eff in eff.items():
        # adjust update
        
        # you will want to call set efficiency from here
        # Season efficiency will be weighted avg between preseason and in game efficiencies
        # preseason weight starts at 1 and decreases by .04 after each game until .08, then will stay static at .06 for the remainder of the season
        
        # count all game values first and multiply by .04 to get weight (upper bound .92; if >.92, weight = .94)
        # 1-(weight) = preseason weight
        # season efficiency = preseason weight(preseason value) + game weight(AVG(game values))
        
        # oe = (1-weight)*preseason_oe + weight*(AVG(game_efficiency_table[game_oe]))
        # de = (1-weight)*preseason_de + weight*(AVG(game_efficiency_table[game_de]))
        
        # check if team had a game yesterday/game was finished
        # if game.date == yesterday or last_game.finished: 
            # add to game_tables
        pass
        
    # TODO: Liam provide more performant redis bindings for this merge.
    # merge 
    await set_projection_table(root, {**update, **(await get_projection_table())})


if __name__ == "__main__":
    ncaab_efficiency.start()
