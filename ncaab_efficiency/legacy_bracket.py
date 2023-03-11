import math
from pprint import pprint
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import requests
import csv
from flask import Flask
import time
from datetime import date
import pytz

app = Flask(__name__)


FILE_KEY: str = "13Sz9qLW4goGYZPTBnzarTjfV41Cum4GhyxlFj3ZlTp8"
MAIN_SHEET_NAME: str = "Kenpom NCAA"
HCA_SHEET_NAME: str = "Kenpom Home Court Advantage"
BET_ONLINE_SHEET_NAME: str = "BetOnline Odds"
CALCS_SHEET_NAME: str = "Calcs"
PCTS_SHEET_NAME: str = "Pre-Tournament Simulation"
CURRENT_ROUND_SHEET_NAME: str = "Round of 64"
KENPOM_URL = "https://kenpom.com/"
KENPOM_HCA = "https://kenpom.com/hca.php"
BETONLINE_API = "https://betonline-basketball-ncaa.datafeeds.net/api/csv/odds/v2/basketball/ncaa?api-key=eb022d00cfb3df82f71ce454008b28c9"

FIXED_SHEET_IDS = [
    0,
    1363918304,
    191791557,
    1074785143,
    2140183563,
    1071137860,
    444017198,
    1879600827,
    287631293,
    977523894,
    934204985,
    94240272,
    1841456151,
    973371187,
]
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", SCOPE
)
GC = gspread.authorize(CREDENTIALS)
WB = GC.open_by_key(FILE_KEY)

KENPOM_HEADER: dict = {
    "authority": "kenpom.com",
    "cache-control": "max-age=0",
    "dnt": "1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "sec-gpc": "1",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "referer": "https://kenpom.com/handlers/login_handler.php",
    "accept-language": "en-US,en;q=0.9",
    "cookie": "PHPSESSID=f9b64c62e81ac2779d6578e10c0b5897; kenpomuser=ajrotunno31%40gmail.com; kenpomid=a680be18df11d17085befafcb211f23b",
}


PLAY_INS = [
    "Drake",
    "Wichita St.",
    "Norfolk St.",
    "Appalachian St.",
    "Michigan St.",
    "UCLA",
    "Mount St. Mary's",
    "Texas Southern",
]

PLAY_INS_SEEDS = [11, 11, 16, 16, 11, 11, 16, 16]
PLAY_INS_REGIONS = ["West", "West", "West", "West", "East", "East", "East", "East"]

BRACKET = {
    "West": [
        "Gonzaga",
        "Iowa",
        "Kansas",
        "Virginia",
        "Creighton",
        "USC",
        "Oregon",
        "Oklahoma",
        "Missouri",
        "VCU",
        "Drake",
        "UC Santa Barbara",
        "Ohio",
        "Eastern Washington",
        "Grand Canyon",
        "Norfolk St.",
    ],
    "South": [
        "Baylor",
        "Ohio St.",
        "Arkansas",
        "Purdue",
        "Villanova",
        "Texas Tech",
        "Florida",
        "North Carolina",
        "Wisconsin",
        "Virginia Tech",
        "Utah St.",
        "Winthrop",
        "North Texas",
        "Colgate",
        "Oral Roberts",
        "Hartford",
    ],
    "Midwest": [
        "Illinois",
        "Houston",
        "West Virginia",
        "Oklahoma St.",
        "Tennessee",
        "San Diego St.",
        "Clemson",
        "Loyola Chicago",
        "Georgia Tech",
        "Rutgers",
        "Syracuse",
        "Oregon St.",
        "Liberty",
        "Morehead St.",
        "Cleveland St.",
        "Drexel",
    ],
    "East": [
        "Michigan",
        "Alabama",
        "Texas",
        "Florida St.",
        "Colorado",
        "BYU",
        "Connecticut",
        "LSU",
        "St. Bonaventure",
        "Maryland",
        "UCLA",
        "Georgetown",
        "UNC Greensboro",
        "Abilene Christian",
        "Iona",
        "Texas Southern",
    ],
}
REGION_ORDER = ["West", "East", "Midwest", "South"]

KENPOM_TRENDS_URL = "https://kenpom.com/trends.php"
KENPOM_CSV_URL = "https://kenpom.com/getdata.php?file=summary21"

response = requests.get(KENPOM_TRENDS_URL, headers=KENPOM_HEADER)
league_stats_df = pd.read_html(response.text, header=0)[0].head(1)
CURRENT_YEAR_EFFICIENCY = float(league_stats_df["Efficiency"][0])
CURRENT_YEAR_TEMPO = float(league_stats_df["Tempo"][0])
YEAR_CONSTANT = (CURRENT_YEAR_EFFICIENCY * CURRENT_YEAR_TEMPO) / 100


@app.route("/")
def main():
    betonline_df = grab_betonline()
    print("PassedBetonline")
    kenpom_df = grab_kenpom()
    print("Passed Kenpom")
    push_bet_data(kenpom_df, betonline_df)
    print("Pushed Bet Data")
    df = simulate_matchups(MATCHUPS, kenpom_df)
    print("Simulated Matchups")
    df.to_csv("pct-" + date.today().strftime("%b-%d-%Y") + ".csv")
    return "<h1>Successful Upload to the Sheet</h1>\n"


def generate_matchups():
    MATCHUPS = {}
    playins = []
    for region in BRACKET:
        for team in BRACKET[region]:
            if "/" in team:
                playin_game = set()
                matchup = team.split("/")
                playin_game.add(matchup[0])
                playin_game.add(matchup[1])
                playins.append(playin_game)
        r1 = list()
        for x in BRACKET[region][::-1]:
            team_set = set()
            team_set.add(x)
            r1.append(team_set)
        MATCHUPS[region + "-r1"] = r1
        r2_matchups = []
        for i in range(8):
            matchup_set = set()
            matchup_set = matchup_set | r1[0 + i]
            matchup_set = matchup_set | r1[-1 - i]
            r2_matchups.append(matchup_set)
        r2 = []
        for team in BRACKET[region]:
            for matchup in r2_matchups:
                if team in matchup:
                    neg_index = -1 - r2_matchups.index(matchup)
                    r2.append(r2_matchups[neg_index])
        MATCHUPS[region + "-r2"] = r2
        r3_matchups = []
        for i in range(4):
            matchup_set = set()
            matchup_set = matchup_set | r2[0 + i]
            matchup_set = matchup_set | r2[-9 - i]
            r3_matchups.append(matchup_set)

        r3 = []
        for team in BRACKET[region]:
            for matchup in r3_matchups:
                if team in matchup:
                    neg_index = -1 - r3_matchups.index(matchup)
                    r3.append(r3_matchups[neg_index])
        MATCHUPS[region + "-r3"] = r3
        r4_matchups = []
        for i in range(2):
            matchup_set = set()
            matchup_set = matchup_set | r3[0 + i]
            matchup_set = matchup_set | r3[-13 - i]
            r4_matchups.append(matchup_set)

        r4 = []
        for team in BRACKET[region]:
            for matchup in r4_matchups:
                if team in matchup:
                    neg_index = -1 - r4_matchups.index(matchup)
                    r4.append(r4_matchups[neg_index])
        MATCHUPS[region + "-r4"] = r4

    MATCHUPS["Midwest-r5"] = [MATCHUPS["South-r4"][0] | MATCHUPS["South-r4"][1]] * 16
    MATCHUPS["South-r5"] = [MATCHUPS["Midwest-r4"][0] | MATCHUPS["Midwest-r4"][1]] * 16
    MATCHUPS["West-r5"] = [MATCHUPS["East-r4"][0] | MATCHUPS["East-r4"][1]] * 16
    MATCHUPS["East-r5"] = [MATCHUPS["West-r4"][0] | MATCHUPS["West-r4"][1]] * 16

    MATCHUPS["Midwest-r6"] = [MATCHUPS["West-r5"][0] | MATCHUPS["East-r5"][0]] * 16
    MATCHUPS["South-r6"] = [MATCHUPS["West-r5"][0] | MATCHUPS["East-r5"][0]] * 16
    MATCHUPS["West-r6"] = [MATCHUPS["South-r5"][0] | MATCHUPS["Midwest-r5"][0]] * 16
    MATCHUPS["East-r6"] = [MATCHUPS["South-r5"][0] | MATCHUPS["Midwest-r5"][0]] * 16
    MATCHUPS["play-in"] = playins
    return MATCHUPS


teams = set()
MATCHUPS = generate_matchups()
for x in MATCHUPS:
    for y in MATCHUPS[x]:
        if type(y) is set:
            for z in y:
                if "/" in z:
                    split = z.split("/")
                    teams.add(split[0])
                    teams.add(split[1])
                else:
                    teams.add(z)


def grab_betonline():
    team_name_replacement_dict = write_name_changes()
    session = requests.Session()
    information = session.get(BETONLINE_API)
    decoded_information = information.content.decode("utf-8")
    print(decoded_information)
    file = open("betonline.csv", "w")
    file.write(decoded_information)
    file.close()
    time.sleep(10)
    betonline_df = (
        pd.read_csv("betonline.csv")
        .drop(
            [
                "Sport",
                "League",
                "Sportsbook",
                "Game UID",
                "ID",
                "Away Rotation Number",
                "Home Rotation Number",
            ],
            axis=1,
        )
        .replace(team_name_replacement_dict)
        .replace(" State$", " St.", regex=True)
        .replace(" State ", " St. ", regex=True)
    )
    betonline_df["newdescription"] = (
        betonline_df["Away Team"] + " vs " + betonline_df["Home Team"]
    )
    betonline_df = betonline_df.set_index("Start Date")
    eastern = pytz.timezone("US/Eastern")
    betonline_df.index = pd.to_datetime(betonline_df.index, errors="coerce").tz_convert(
        eastern
    )
    betonline_df = betonline_df.reset_index().set_index("newdescription")
    sh: gspread.Worksheet = _get_worksheet(FILE_KEY, BET_ONLINE_SHEET_NAME)
    write(sh, betonline_df)
    return betonline_df


def grab_kenpom():
    session = requests.Session()
    information = session.get(KENPOM_CSV_URL, headers=KENPOM_HEADER)
    decoded_information = information.content.decode("utf-8")
    file = open("kenpom.csv", "w")
    file.write(decoded_information)
    file.close
    kenpom_main_df = pd.read_csv(
        "kenpom.csv",
        header=0,
        names=[
            "Season",
            "Team",
            "Tempo",
            "RankTempo",
            "AdjT",
            "Rank AdjT",
            "OE",
            "RankOE",
            "AdjO",
            "Rank AdjO",
            "DE",
            "RankDE",
            "AdjD",
            "Rank AdjD",
            "AdjEM",
            "Rank AdjEM",
        ],
    )
    kenpom_main_df = kenpom_main_df[kenpom_main_df["Team"].isin(teams)]
    kenpom_main_df["AdjT"] = kenpom_main_df["AdjT"].astype(float)
    kenpom_main_df["AdjO"] = kenpom_main_df["AdjO"].astype(float)
    kenpom_main_df["AdjD"] = kenpom_main_df["AdjD"].astype(float)
    kenpom_main_df["relativetempo"] = kenpom_main_df["AdjT"] - CURRENT_YEAR_TEMPO
    kenpom_main_df["relativeo"] = kenpom_main_df["AdjO"] - CURRENT_YEAR_EFFICIENCY
    kenpom_main_df["relatived"] = kenpom_main_df["AdjD"] - CURRENT_YEAR_EFFICIENCY
    kenpom_main_df.set_index("Team", inplace=True)
    response = requests.get(KENPOM_HCA, headers=KENPOM_HEADER)
    rows_to_skip = []
    accumulator = 0
    for i in range(1, 9):
        rows_to_skip.append(i * 40 + accumulator)
        accumulator += 1
    kenpom_hca_df = (
        pd.read_html(response.text, header=0, skiprows=[i for i in range(0, 9)])[0]
        .drop(rows_to_skip)
        .drop("Conf", axis=1)
    )
    kenpom_hca_df.set_index("Team", inplace=True)
    kenpom_df = kenpom_main_df.join(kenpom_hca_df, on="Team")
    kenpom_df["HCA"] = kenpom_df["HCA"].astype(float)
    sh: gspread.Worksheet = _get_worksheet(FILE_KEY, MAIN_SHEET_NAME)
    writei(sh, kenpom_df)
    return kenpom_df


def write_name_changes():
    sh: gspread.Worksheet = _get_worksheet(FILE_KEY, "Name Changes")
    df = get_as_dataframe(sh)

    team_name_replacement_dict = {}
    for pair in df.to_dict("records"):
        team_name_replacement_dict[pair["Unnamed: 0"]] = pair["kenpom"]
    return team_name_replacement_dict


def win_probability(team1score, team2score):
    constant_exponent = 11.5
    team1exp = team1score ** constant_exponent
    team2exp = team2score ** constant_exponent
    team1winpct = team1exp / (team1exp + team2exp)
    return team1winpct


def calculate_metrics(team1, team2, kenpom_df, betonline_df=None):
    team1t, team1o, team1d = kenpom_df[["AdjT", "AdjO", "AdjD"]].loc[[team1]].values[0]
    team2t, team2o, team2d = kenpom_df[["AdjT", "AdjO", "AdjD"]].loc[[team2]].values[0]
    team1rt, team1ro, team1rd = (
        kenpom_df[["relativetempo", "relativeo", "relatived"]].loc[[team1]].values[0]
    )
    team2rt, team2ro, team2rd = (
        kenpom_df[["relativetempo", "relativeo", "relatived"]].loc[[team2]].values[0]
    )
    first_term_team2 = (
        YEAR_CONSTANT
        - (team2o + team1d - CURRENT_YEAR_EFFICIENCY)
        * (CURRENT_YEAR_TEMPO + team2rt + team1rt)
        / 100
    ) / 15
    first_term_team1 = (
        YEAR_CONSTANT
        - (team2d + team1o - CURRENT_YEAR_EFFICIENCY)
        * (CURRENT_YEAR_TEMPO + team2rt + team1rt)
        / 100
    ) / 15
    second_term_team2 = (
        (team2o + team1d - CURRENT_YEAR_EFFICIENCY)
        * (CURRENT_YEAR_TEMPO + team2rt + team1rt)
        / 100
    )
    second_term_team1 = (
        (team2d + team1o - CURRENT_YEAR_EFFICIENCY)
        * (CURRENT_YEAR_TEMPO + team2rt + team1rt)
        / 100
    )
    team2_score = first_term_team2 + second_term_team2
    team1_score = first_term_team1 + second_term_team1
    team2_spread = team1_score - team2_score
    team1_spread = team2_score - team1_score
    projected_total = team1_score + team2_score

    team1_win_pct = win_probability(team1_score, team2_score)
    finals_team = ["Gonzaga", "Houston"]
    if team1 in finals_team and team2 in finals_team:
        pprint(
            [
                team1,
                team2,
                team2_score,
                team1_score,
                team1_win_pct,
            ]
        )
    hca_term = kenpom_df["HCA"].loc[[team1]].values[0] / 2
    if betonline_df is None:
        return team1_win_pct
    else:
        team1_spread_bet, team2_spread_bet, betonline_total = process_betonline(
            betonline_df, team1, team2
        )
        team1_value = team1_spread_bet - team1_spread
        team2_value = team2_spread_bet - team2_spread
        value_on_total = projected_total - betonline_total
        return (
            team2_score,
            team1_score,
            team2_spread,
            team1_spread,
            team2_value,
            team1_value,
            team2_spread_bet,
            team1_spread_bet,
            betonline_total,
            projected_total,
            value_on_total,
            team1_win_pct,
        )


def _get_worksheet(
    key: str,
    worksheet_name: str,
    creds: "filepath to Google account CREDENTIALS" = "credentials.json",
) -> gspread.Worksheet:
    """ return a gspread Worksheet instance for given Google Sheets workbook/worksheet """
    SCOPE = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    CREDENTIALS = ServiceAccountCredentials.from_json_keyfile_name(creds, SCOPE)
    GC = gspread.authorize(CREDENTIALS)
    WB = GC.open_by_key(key)
    sheet = WB.worksheet(worksheet_name)
    return sheet


def write(sheet: gspread.Worksheet, df: pd.DataFrame, **options) -> None:
    set_with_dataframe(sheet, df, include_index=False, resize=True, **options)


def writei(sheet: gspread.Worksheet, df: pd.DataFrame, **options) -> None:
    set_with_dataframe(sheet, df, include_index=True, **options)


def process_betonline(betonline_df, team1, team2):
    game_description = team2 + " vs " + team1
    team1_spread_bet, team2_spread_bet, betonline_total = (
        betonline_df[
            [
                "Game Spread Home Handicap",
                "Game Spread Away Handicap",
                "Game Total Points",
            ]
        ]
        .loc[[game_description]]
        .values[0]
    )
    return team1_spread_bet, team2_spread_bet, betonline_total


def simulate_matchups(MATCHUPS, kenpom_df):
    pcts = []
    for playin in MATCHUPS["play-in"]:
        playin = list(playin)
        team1 = playin[0]
        team2 = playin[1]
        win = calculate_metrics(team1, team2, kenpom_df)
        team1_rank, team1_region = get_rank(team1)
        team2_rank, team2_region = get_rank(team2)
        pcts.append(
            {
                "Seed": team1_rank,
                "Team": team1,
                "opponent": team2,
                "Round": 0,
                "win_pct": win,
            }
        )
        pcts.append(
            {
                "Seed": team2_rank,
                "Team": team2,
                "opponent": team1,
                "Round": 0,
                "win_pct": (1.0 - win),
            }
        )

    for region in BRACKET:
        for team in BRACKET[region]:
            rank, _ = get_rank(team)
            seed = BRACKET[region].index(team)
            if "/" in team:
                split = team.split("/")
                for team in split:
                    for i in range(1, 7):
                        opponents = MATCHUPS[region + "-r" + str(i)][seed]
                        for opp in opponents:
                            if "/" in opp:
                                split = opp.split("/")
                                for opp in split:
                                    win_pct = calculate_metrics(team, opp, kenpom_df)
                                    pcts.append(
                                        {
                                            "Seed": rank,
                                            "Team": team,
                                            "opponent": opp,
                                            "Round": i,
                                            "win_pct": win_pct,
                                            "Region": region,
                                        }
                                    )
                            else:
                                win_pct = calculate_metrics(team, opp, kenpom_df)
                                pcts.append(
                                    {
                                        "Seed": rank,
                                        "Team": team,
                                        "opponent": opp,
                                        "Round": i,
                                        "win_pct": win_pct,
                                        "Region": region,
                                    }
                                )
            else:
                for i in range(1, 7):
                    opponents = MATCHUPS[region + "-r" + str(i)][seed]
                    for opp in opponents:
                        if "/" in opp:
                            split = opp.split("/")
                            for opp in split:
                                win_pct = calculate_metrics(team, opp, kenpom_df)
                                pcts.append(
                                    {
                                        "Seed": rank,
                                        "Team": team,
                                        "opponent": opp,
                                        "Round": i,
                                        "win_pct": win_pct,
                                        "Region": region,
                                    }
                                )
                        else:
                            win_pct = calculate_metrics(team, opp, kenpom_df)
                            pcts.append(
                                {
                                    "Seed": rank,
                                    "Team": team,
                                    "opponent": opp,
                                    "Round": i,
                                    "win_pct": win_pct,
                                    "Region": region,
                                }
                            )
    # pprint(pcts)
    # print(pd.DataFrame(pcts))
    df = (
        pd.DataFrame(pcts)
        .set_index(["Round", "Team", "opponent", "Region"])
        .sort_index()
    )
    df.to_csv("matchups.csv")
    counter = 0
    for index, row in df.iterrows():
        rnd = index[0]
        team = index[1]
        opponent = index[2]
        if rnd == 0:
            df.loc[index, "pct_for_next_round"] = df.loc[index, "win_pct"]
        elif rnd == 1:
            try:
                previous_round_opponent = df.loc[(0, opponent)]
                df.loc[index, "pct_for_next_round"] = (
                    previous_round_opponent["pct_for_next_round"].sum() * row["win_pct"]
                )
                counter += 1
            except:
                df.loc[index, "pct_for_next_round"] = row["win_pct"]
        elif rnd > 1:
            previous_round_opponent = df.loc[((rnd - 1), opponent)].copy()
            previous_round = df.loc[((rnd - 1), team)].copy()
            # if opponent in PLAY_INS:
            #     if PLAY_INS.index(opponent) % 2 == 0:
            #         previous_round_opponent["pct_for_next_round"] = (
            #             previous_round_opponent["pct_for_next_round"] / 2
            #         )
            #     else:
            #         previous_round_opponent["pct_for_next_round"] = (
            #             previous_round_opponent["pct_for_next_round"] / 2
            #         )
            # elif team in PLAY_INS:
            #     if PLAY_INS.index(team) % 2 == 0:
            #         previous_round["pct_for_next_round"] = (
            #             previous_round["pct_for_next_round"] / 2
            #         )
            #     else:
            #         previous_round["pct_for_next_round"] = (
            #             previous_round["pct_for_next_round"] / 2
            #         )
            df.loc[index, "pct_for_next_round"] = (
                previous_round_opponent["pct_for_next_round"].sum()
                * row["win_pct"]
                * previous_round["pct_for_next_round"].sum()
            )
    df = (
        df.groupby(by=["Region", "Round", "Seed", "Team"])["pct_for_next_round"]
        .sum()
        .reset_index()
        .pivot_table(
            values="pct_for_next_round",
            index=["Region", "Seed", "Team"],
            columns="Round",
            aggfunc="first",
        )
    )
    df.columns = [
        "Round of 64",
        "Round of 32",
        "Sweet Sixteen",
        "Elite Eight",
        "Final Four",
        "Championship",
    ]
    df = df.sort_index(level=1)
    splits = [j for i, j in df.groupby(by="Region")]
    sh: gspread.Worksheet = _get_worksheet(FILE_KEY, PCTS_SHEET_NAME)
    cols = 1
    rows = 2
    sheetId = sh._properties["sheetId"]
    splits = reorder_splits(splits)
    for region in splits:
        if region.index[0][0] == "East":
            rows += region.shape[0] + 3
        elif region.index[0][0] == "Midwest":
            cols += region.shape[1] + 4
        elif region.index[0][0] == "South":
            rows = 2
        writei(sh, region, resize=False, col=cols, row=rows)
    res = WB.batch_update(resize_columns(sheetId))
    return df


def reorder_splits(splits):
    r1, r2, r3, r4 = splits
    splits = [None] * 4
    for r in r1, r2, r3, r4:
        splits[REGION_ORDER.index(r.index[0][0])] = r
    return splits


def clean_sheets():
    for worksheet in WB.worksheets():
        if worksheet.id not in FIXED_SHEET_IDS:
            WB.del_worksheet(worksheet)
    print("Sleeping...")
    time.sleep(100)
    print("Finished slumber")


def push_bet_data(kenpom_df, betonline_df):
    games_list = []
    for i, row in betonline_df.iterrows():
        team1 = row["Home Team"]
        team2 = row["Away Team"]
        if team1 in teams and team2 in teams:
            # try:
            team1_rank, team1_region = get_rank(team1)
            team2_rank, team2_region = get_rank(team2)
            (
                team2_score,
                team1_score,
                team2_spread,
                team1_spread,
                team2_value,
                team1_value,
                team2_spread_bet,
                team1_spread_bet,
                betonline_total,
                projected_total,
                value_on_total,
                team1_win_pct,
            ) = calculate_metrics(team1, team2, kenpom_df, betonline_df)
            row_dict = {
                "Date": row["Start Date"].strftime("%A %B %d, %Y %I:%M %p"),
                "t": "",
                "Team 1": team1,
                "Team 1\nProjected Score": team1_score,
                "Team 2": team2,
                "Team 2\nProjected Score": team2_score,
                "a": "",
                "Team 1\nProjected Spread": team1_spread,
                "Team 1\nBetOnline Spread": team1_spread_bet,
                "Team 1\nValue on Spread": team1_value,
                "o": "",
                "Team 2\nProjected Spread": team2_spread,
                "Team 2\nBetOnline Spread": team2_spread_bet,
                "Team 2\nValue on Spread": team2_value,
                "c": "",
                "Projected Total": projected_total,
                "BetOnline Total": betonline_total,
                "Value on the Over": value_on_total,
                "Value on the Under": -1 * value_on_total,
            }
            games_list.append(row_dict)
    df = pd.DataFrame(games_list)
    sh: gspread.Worksheet = _get_worksheet(FILE_KEY, CURRENT_ROUND_SHEET_NAME)
    # sh.clear()
    write(sh, df)
    sheetId = sh._properties["sheetId"]
    res = WB.batch_update(resize_columns(sheetId))


def generate_matchup_tabs(df):
    clean_sheets()
    print(df.reset_index().drop("Region"))


def resize_columns(sheetId):
    body = {
        "requests": [
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "dimension": "COLUMNS",
                        "sheetId": sheetId,
                        "startIndex": 0,
                        "endIndex": 18,
                    }
                }
            }
        ]
    }
    return body


def create_merge_obj(startRow, endRow, startColumn, endColumn, sheetId):
    body = {
        "requests": [
            {
                "mergeCells": {
                    "mergeType": "MERGE_ROWS",
                    "range": {
                        "sheetId": sheetId,
                        "startRowIndex": startRow,
                        "endRowIndex": endRow,
                        "startColumnIndex": startColumn,
                        "endColumnIndex": endColumn,
                    },
                }
            }
        ]
    }
    return body


def get_rank(team):
    if team in PLAY_INS:
        return (
            PLAY_INS_SEEDS[PLAY_INS.index(team)],
            PLAY_INS_REGIONS[PLAY_INS.index(team)],
        )
    for region in BRACKET:
        for t in BRACKET[region]:
            if t == team:
                return BRACKET[region].index(team) + 1, region


if __name__ == "__main__":
    app.run(port=5000, debug=True)