import sqlalchemy, pandas
from sqlalchemy import create_engine
import MySQLdb
import mysql.connector

engine = sqlalchemy.create_engine('mysql+mysqldb://root:password@localhost:3306')
con = engine.connect()
con.execute("CREATE DATABASE soccer")

#importing data into a dataframe
all_data = pandas.read_excel('squawka_Spain_2016_17.xlsx', sheet_name='Spain 2016_17', usecols="A:N",
                             true_values=['True'], false_values=['False'], nrows=112127, na_values="-",
                             parse_dates=[1]) #dtype=object

events = ["blocked_shots", "cards", "clearances", "fouls", "headed_duels", "interceptions", "shots", "tackles", "takeons"]

matches = all_data.drop_duplicates(subset=["home", "away"]).loc[:,["date", "home", "away"]]
matches.to_sql("matches", engine, schema = "soccer", if_exists="append", index=False)
players = all_data.drop_duplicates(subset=["player", "team"]).loc[all_data["is_own"] != True, ["player", "team"]]
#check if some players played for 2 different teams in the same season: # group by player -> select unique records by team in each group -> keep those that have only a player
players.to_sql("players", engine, schema = "soccer", if_exists="append", index=False) #if some player played for 2 different teams during the season he will have 2 different entries in the table

for event in events:
    if event == 'blocked_events':
        all_data.loc[all_data["event"] == "blocked_events", ["date", "mins", "player", "type", "shot_player", "headed"]].to_sql("blocked_events", engine, schema = "soccer", if_exists="append", index=False)
    elif event == 'cards':
        all_data.loc[all_data["event"] == "cards", ["date", "mins", "player", "card"]].to_sql("cards", engine, schema="soccer", if_exists="append", index=False)
    elif event == 'clearances':
        all_data.loc[all_data["event"] == "clearances", ["date", "mins", "player"]].to_sql("clearances", engine, schema="soccer", if_exists="append", index=False)
    elif event == 'fouls':
        all_data.loc[all_data["event"] == "fouls", ["date", "mins", "player", "opponent"]].to_sql("fouls", engine, schema="soccer", if_exists="append", index=False)
    elif event == 'headed_duels':
        all_data.loc[all_data["event"] == "headed_duals", ["date", "mins", "player", "opponent", "type"]].to_sql("headed_duels", engine, schema="soccer", if_exists="append", index=False)
    elif event == 'interceptions':
        all_data.loc[all_data["event"] == "interceptions", ["date", "mins", "player", "headed"]].to_sql("interceptions", engine, schema="soccer", if_exists="append", index=False)
    elif event == 'shots':
        all_data.loc[all_data["event"].isin(["shots", "shots_on_target", "goals"]), ["date", "mins", "player", "event", "type", "is_own"]].to_sql("shots", engine, schema="soccer", if_exists="append", index=False)
    elif event == 'tackles':
        all_data.loc[all_data["event"] == "tackles", ["date", "mins", "player", "opponent", "type"]].to_sql("tackles", engine, schema="soccer", if_exists="append", index=False)
    elif event == 'takeons':
        df = all_data.loc[all_data["event"] == "takeons", ["date", "mins", "player", "opponent", "type"]]
        df.columns = ["date", "mins", "player", "opponent", "success"]
        df.loc[df["success"] == "Success", "success"] = True
        df.loc[df["success"] == "Failed", "success"] = False
        df.to_sql("takeons", engine, schema="soccer", if_exists="append", index=False)

con.close()