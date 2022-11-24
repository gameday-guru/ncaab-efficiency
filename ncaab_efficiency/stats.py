from gdg_model_builder import spiodirect

def get_possession_from_statline(statline : spiodirect.ncaab.game_stats_by_date.TeamGameStatsByDate):

    if statline.Possessions is None:
        return (
            statline.FieldGoalsAttempted - statline.OffensiveRebounds
            + statline.Turnovers + (.475 * statline.FreeThrowsAttempted)
        )
    else:
        return statline.Possessions