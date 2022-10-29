from datetime import datetime, timedelta
from typing import List, Dict
from gdg_model_builder import Model, \
    private, session, spiodirect, universal, \
    poll, days, secs, dow, Event, root
from pydantic import BaseModel

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

    # fix league efficiency at start of iteration
    eff = await get_league_efficiency_table()
   
    ptable = await get_projection_table()
    ptable_out = ptable.copy()  # ! use this if you want eff to remain to the same throughout iteration
   
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
        # ? ptable_out[game_id] = ...
        
    # TODO: Liam provide more performant redis bindings for this merge.
    # merge 
    await set_projection_table(root, ptable_out)

@ncaab_efficiency.get("league_effiency_table", universal, t=Dict[str, EfficiencyEntry])
async def get_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.set("league_effiency_table", universal, private, t=Dict[str, EfficiencyEntry])
async def set_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.get("manual_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
async def get_manual_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.set("manual_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
async def set_manual_league_efficiency_table(context, value):
    return value

@ncaab_efficiency.get("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, EfficiencyEntry]])
async def get_game_efficiency_tables(context, value):
    return value

@ncaab_efficiency.set("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, EfficiencyEntry]])
async def set_game_efficiency_tables(context, value):
    return value

@ncaab_efficiency.task(valid=days(1))
async def iterate_efficiency(e):
    
    # fix league efficiency at start of iteration
    eff = await get_league_efficiency_table()
    eff_out = eff.copy()
    game_effs = await get_game_efficiency_tables()
    games_effs_out = games_effs.copy()
   
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
        
        # ? eff[team_id] = ... 
        
        # check if team had a game yesterday/game was finished
        # if game.date == yesterday or last_game.finished: 
            # add to game_tables
            # ? game_effs[team_id][game.id] = ...
        pass
        
    # TODO: Liam provide more performant redis bindings for this merge.
    # merge 
    await set_league_efficiency_table(root, game_effs)
    await set_league_efficiency_table(root, eff)


if __name__ == "__main__":
    ncaab_efficiency.start()
