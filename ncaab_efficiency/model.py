from datetime import datetime, timedelta
from typing import List, Dict
from gdg_model_builder import Model, \
    private, session, spiodirect, universal, \
    poll, days, secs, dow, Event, root, Init
from pydantic import BaseModel
import csv

def get_projection(home_tempo: float, away_tempo: float, tempo_avg: float, home_oe: float, away_de: float, away_oe: float, home_de: float, ppp_avg: float):
    proj_tempo = home_tempo + away_tempo - tempo_avg
    home_projection = proj_tempo*(home_oe + away_de - ppp_avg)
    away_projection = proj_tempo*(away_oe + home_de - ppp_avg)
    return (home_projection, away_projection)

def get_game_t(home_tempo: float, away_tempo: float, tempo_avg: float, possessions: int):
    proj_tempo = home_tempo + away_tempo - tempo_avg
    factor = 1 + (possessions - proj_tempo)/(2 * possessions)
    home_game_t = home_tempo * factor
    away_game_t = away_tempo * factor
    return (home_game_t, away_game_t)

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
    oe = (1-weight)*preseason_oe + weight*(avg_game_oe)
    de = (1-weight)*preseason_de + weight*(avg_game_de)
    return (oe, de)

def get_new_tempo(preseason_t: float, avg_game_t: float, weight: float):
    return (1-weight)*preseason_t + weight*(avg_game_t)

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

ncaab_efficiency = Model(cron_window=1)

def get_seed_league_efficiency(filename : str)->Dict[str, EfficiencyEntry]:
    seed_table : Dict[str, EfficiencyEntry] = dict()
    for entry in csv.DictReader(filename).read():
     seed_table[entry["id"]] = EfficiencyEntry(
        team_id = entry["id"],
         oe = entry["oe"],
         de = entry["de"],
         tempo = entry["tempo"])
    return seed_table

@ncaab_efficiency.task(e = Init)
async def Init_ncaab(e):
    preseason_data = get_seed_league_efficiency("file.csv")
    await set_preseason_league_efficiency_table(root, preseason_data)
    await set_league_efficiency_table(root, preseason_data)

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
    eff_out = eff.copy()
   
    ptable = await get_projection_table(root)
    ptable_out = ptable.copy()  # ! use this if you want eff to remain to the same throughout iteration
   
    # get games from sportsdataio
    lookahead = timedelta.days(7)
    iter_date = datetime.now()
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

    def projection_entry(**kwargs):
        for key, value in kwargs.items():
            ptable_out[key] = value

    while iter_date < end_date:
        games = spiodirect.ncaab.games_by_date.get_games(iter_date)
        for game in games:
            # do what you need with the games...
            # get_league_efficiency
            # proj_tempo = tempo + opp_tempo - tempo_avg
            # projection = proj_tempo*(oe+de-ppp_avg)/100
            home_team_score, away_team_score = get_projection(eff_out[game.HomeTeamID].tempo, eff_out[game.AwayTeamID].tempo, tempo_avg, eff_out[game.HomeTeamID].oe, eff_out[game.AwayTeamID].de,
            eff_out[game.AwayTeamID].oe, eff_out[game.HomeTeamID].de, ppp_avg)
            
            # ? ptable_out[game_id] = ...
            ptable_out[game.GameID] = ProjectionEntry(
                game_id = game.GameID,
                home_team_id = game.HomeTeamID,
                away_team_id = game.AwayTeamID,
                home_team_score = home_team_score,
                away_team_score = away_team_score
            )
    # TODO: Liam provide more performant redis bindings for this merge.
    # merge 
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

@ncaab_efficiency.get("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, EfficiencyEntry]])
async def get_game_efficiency_tables(context, value):
    return value

@ncaab_efficiency.set("game_efficiency_tables", universal, private, t=Dict[str, Dict[str, EfficiencyEntry]])
async def set_game_efficiency_tables(context, value):
    return value

@ncaab_efficiency.task(valid=days(1))
async def iterate_efficiency(e):
    
    # fix league efficiency at start of iteration
    eff = await get_league_efficiency_table(root)
    eff_out = eff.copy()
    pre_eff = await get_preseason_league_efficiency_table(root)
    pre_eff_out = pre_eff_out.copy()
    game_effs = await get_game_efficiency_tables(root)
    game_effs_out = game_effs.copy()
    yesterday_games = spiodirect.ncaab.games_by_date.get_games(yesterday)
    team_statlines = spiodirect.ncaab.get_game_stats_by_date(yesterday)
    lookahead = timedelta.days(1)
    yesterday = datetime.now() - lookahead

    game_oe = [eff.game_oe
    for eff in game_effs[team_id].values()]
    game_oe_avg = sum(game_oe)/len(game_oe)

    game_de = [eff.game_de
    for eff in game_effs[team_id].values()]
    game_de_avg = sum(game_de)/len(game_de)

    tempos = []
    for _, item in eff.items():
        tempos.append(item.tempo)
    tempo_avg = sum(tempos)/len(tempos)

    game_t = [eff.tempo
    for eff in game_effs[team_id].values()]
    game_t_avg = sum(game_t)/len(game_t)

    teams_yesterday : Dict[str, List[tuple[bool, str, str]]] = dict()
    for game in yesterday_games:
        # home
        if game.HomeTeamID not in teams_yesterday:
            teams_yesterday[game.HomeTeamID] = []
        teams_yesterday[game.HomeTeamID].append((True, game.GameID, game.AwayTeamID))
        
        # away
        if game.AwayTeamID not in teams_yesterday:
            teams_yesterday[game.AwayTeamID] = []
        teams_yesterday[game.AwayTeamID].append((False, game.GameID, game.HomeTeamID))
    for team_id, eff in eff_out.items():
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
        
        weight_e = get_weight_e(game_effs.game_id.count())
        league_oe, league_de = get_new_e(pre_eff[team_id].oe, pre_eff[team_id].de, game_oe_avg, game_de_avg, weight_e)
        
        weight_t = get_weight_t(game_effs.game_id.count())
        league_t = get_new_tempo(pre_eff[team_id].tempo, game_t_avg, weight_t)

        eff_entry = EfficiencyEntry(
            team_id = team_id,
            oe = league_oe,
            de = league_de,
            tempo = league_t
        )
        eff_out[team_id] = eff_entry
        
        if team_id in teams_yesterday:
            for is_home, game_id in teams_yesterday[team_id]:
                home_game_t, away_game_t = get_game_t(eff[game.HomeTeamID].tempo, eff[game.AwayTeamID].tempo, tempo_avg, team_statlines.Possessions)
                if game.HomeTeamID not in 
                game_effs_out[team_id][game_id] = GameEfficiencyEntry(
                    team_id = team_id,
                    game_id = game_id,
                    game_oe = yesterday_games[game_id].HomeTeamScore/team_statlines[game_id].Possessions,
                    game_de = yesterday_games[game_id].AwayTeamScore/team_statlines[game_id].Possessions,
                    tempo = game_t
                )
        # add game efficiency

        # check if team had a game yesterday/game was finished
        # if game.date == yesterday or last_game.finished: 
            # add to game_tables
            # ? game_effs[team_id][game.id] = ...
        pass
        
    # TODO: Liam provide more performant redis bindings for this merge.
    # merge 
    await set_game_efficiency_tables(root, game_effs)
    await set_league_efficiency_table(root, eff)


if __name__ == "__main__":
    ncaab_efficiency.start()
