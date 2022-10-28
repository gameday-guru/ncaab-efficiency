from gdg_model_builder import Model, private, session, spiodirect, universal, poll, days, secs, dow, Event
from pydantic import BaseModel

class LeagueEfficiency(BaseModel):
    pass


ncaab_efficiency = Model(cron_window=1)

@ncaab_efficiency.get("league_effiency", universal, t=LeagueEfficiency)
def get_league_efficiency(context, value):
    pass

@ncaab_efficiency.set("league_effiency", universal, t=LeagueEfficiency)
def set_league_efficiency(context, value):
    pass

@ncaab_efficiency.get("top25", universal, t=LeagueEfficiency)
def get_top_25(context, value):
    pass

@ncaab_efficiency.set("top25", universal, t=LeagueEfficiency)
def get_top_25(context, value):
    pass

@ncaab_efficiency.task(valid=days(1))
def iterate_efficiency(context, value):
    pass


if __name__ == "__main__":
    my_model.start()