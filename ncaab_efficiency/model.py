from typing import List, Dict
from gdg_model_builder import Model, \
    private, session, spiodirect, universal, \
    poll, days, secs, dow, Event
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
def get_projection_table(context, value):
    # get_league_efficiency
    # proj_tempo = tempo + opp_tempo - tempo_avg
    # projection = proj_tempo*(oe+de-ppp_avg)/100
    return value

@ncaab_efficiency.get("league_effiency_table", universal, t=Dict[str, EfficiencyEntry])
def get_league_efficiency(context, value):
    return value

@ncaab_efficiency.set("league_effiency_table", universal, private, t=Dict[str, EfficiencyEntry])
def set_league_efficiency(context, value):
    return value

@ncaab_efficiency.get("manual_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
def set_league_table(context, value):
    return value

@ncaab_efficiency.set("manual_league_efficiency_table", universal, t=Dict[str, EfficiencyEntry])
def set_league_table(context, value):
    return value

@ncaab_efficiency.get("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, EfficiencyEntry]])
def get_game_efficiency(context, value):
    return value

@ncaab_efficiency.set("game_efficiency_tables", universal, private t=Dict[str, Dict[str, EfficiencyEntry]])
def set_game_efficiency(context, value):
    return value

@ncaab_efficiency.task(valid=days(1))
def iterate_efficiency(context, value):
    # you will want to call set efficiency from here
    # Season efficiency will be weighted avg between preseason and in game efficiencies
    # preseason weight starts at 1 and decreases by .04 after each game until .08, then will stay static at .06 for the remainder of the season
    
    # count all game values first and multiply by .04 to get weight (upper bound .92; if >.92, weight = .94)
    # 1-(weight) = preseason weight
    # season efficiency = preseason weight(preseason value) + game weight(AVG(game values))
    
    # oe = (1-weight)*preseason_oe + weight*(AVG(game_efficiency_table[game_oe]))
    # de = (1-weight)*preseason_de + weight*(AVG(game_efficiency_table[game_de]))
    pass


if __name__ == "__main__":
    ncaab_efficiency.start()
