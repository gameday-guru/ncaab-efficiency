from typing import List
from gdg_model_builder import Model, \
    private, session, spiodirect, universal, \
    poll, days, secs, dow, Event
from pydantic import BaseModel

class LeagueEfficiency(BaseModel):
    pass


ncaab_efficiency = Model(cron_window=1)

@ncaab_efficiency.get("projection_table", universal, t=LeagueEfficiency)
def get_projection_table(context, value):
    # get_league_efficiency
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
    pass


if __name__ == "__main__":
    ncaab_efficiency.start()