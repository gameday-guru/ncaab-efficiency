from typing import List
from gdg_model_builder import Model, \
    private, session, spiodirect, universal, \
    poll, days, secs, dow, Event
from pydantic import BaseModel

class LeagueEfficiency(BaseModel):
    # ppp_o and ppp_d = points scored (for and against)/possessions for each game from SportsData.io
    # ppp_avg = average of all oe and de from league table
    # opp_de = season defensive efficiency from league table
    ppp_o : int
    ppp_d : int
    ppp_avg : float
    opp_de : float
    opp_oe : float
    pass

class Team():
    id : int
    name : str
    pass


ncaab_efficiency = Model(cron_window=1)

@ncaab_efficiency.get("projection_table", universal, t=LeagueEfficiency)
def get_projection_table(context, value):
    # get_league_efficiency
    # proj_tempo = tempo + opp_tempo - tempo_avg
    # projection = proj_tempo*(oe+de-ppp_avg)/100
    pass

# IN CASE WE ENCOUNTER COMPLEXITIES
@ncaab_efficiency.get("projection_table", universal, private, t=LeagueEfficiency)
def set_projection_table(context, value):
    # get_league_efficiency
    pass

@ncaab_efficiency.task(valid=days(1))
def iterate_projection_table(context, value):
    # you will want to call set efficiency from here
    pass

@ncaab_efficiency.get("league_effiency_table", universal, t=LeagueEfficiency)
def get_league_efficiency(context, value):
    
    pass

@ncaab_efficiency.set("league_effiency_table", universal, t=LeagueEfficiency)
def set_league_efficiency(context, value):
    pass

@ncaab_efficiency.get("manual_league_efficiency_table", universal, t=LeagueEfficiency)
def set_league_table(context, value):
    # does this need to be state?
    pass

@ncaab_efficiency.set("manual_league_efficiency_table", universal, t=LeagueEfficiency)
def set_league_table(context, value):
    # does this need to be state?
    pass

@ncaab_efficiency.get("game_efficiency_tables", universal, t=LeagueEfficiency)
# game_oe = ppp_o/(opp_de/ppp_avg)
# game_de = ppp_d/(opp_oe/ppp_avg)
def get_game_efficiency(context, value):
    pass

@ncaab_efficiency.set("game_efficiency_tables", universal, t=LeagueEfficiency)
def set_game_efficiency(context, value):
    pass

@ncaab_efficiency.get("top25", universal, t=LeagueEfficiency)
def get_top_25(context, value):
    # reference get_league_efficiency
    pass

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
