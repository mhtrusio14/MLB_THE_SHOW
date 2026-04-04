import requests
import gspread
import time
import datetime
import pytz
from unidecode import unidecode
import re
import json
from bs4 import BeautifulSoup
from unidecode import unidecode
from dateutil import parser
import random
import os

start_time = time.time()

def post_with_retry(session, url, **kwargs):
    max_retries = 10
    delay = 120  # seconds
    for attempt in range(max_retries):
        response = session.post(url, **kwargs)
        if response.status_code != 403 and response.status_code != 502:
            return response
        print(f"403 error encountered. Retry {attempt+1}/{max_retries} after {delay} seconds...")
        time.sleep(delay)
        delay += 30
    print("Max retries reached. Returning last response.")
    return response

creds_json = os.environ['CREDS']
CREDS = json.loads(creds_json)

gc = gspread.service_account_from_dict(CREDS)

sh = gc.open("Roster Update Prediction Bot")

base_worksheet = sh.worksheet("Players_Prices")

# Get all values from the worksheet
data = base_worksheet.get_all_values()

# Extract unique pairs from column B and D (index 1 and 3)
unique_list = [{"Player": row[1]} for row in data[1:]]

# print(unique_list[0:5])

# Get unique values from pairs
# unique_pairs = {tuple(pair.items()) for pair in pairs}
# unique_list = [dict(pair) for pair in unique_pairs]
# print(f"Unique Players Count: {unique_list[0]}")
# time.sleep(10)

# print(len(unique_list))

final_players_list = []

all_fangraphs_players = []

user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15", #5 for 5 on testing
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0", # 5 for 5 on testing
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/601.7.7 (KHTML, like Gecko) Version/9.1.2 Safari/601.7.7",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Edge/118.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/117.0.0.0"
]

headers = {
    "User-Agent": random.choice(user_agents),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.fangraphs.com/leaders.aspx",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

session = requests.Session()
# Optionally, add cookies from a real browser session here
# session.cookies.set('cookie_name', 'cookie_value')

# HITTERS TOTAL: 242
url = "https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=bat&lg=all&qual=1&season=2026&month=0&pageitems=2000000000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&sortdir=default&sortstat=WAR"
hitters_response = session.get(url, headers=headers)
print(hitters_response.status_code)
if hitters_response.status_code != 200:
    print("Non-200 status code, possible block. Response:")
    print(hitters_response.text)
try:
    hitters_data = hitters_response.json()['data']
    print(len(hitters_data))
except Exception as e:
    print("Failed to parse JSON or bot detection triggered:", e)


# PITCHERS TOTAL: 89
pitchers_url = "https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=pit&lg=all&qual=1&season=2026&month=0&pageitems=2000000000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&sortdir=default&sortstat=WAR"
pitchers_response = session.get(pitchers_url, headers=headers)
print(pitchers_response.status_code)
if pitchers_response.status_code != 200:
    print("Non-200 status code, possible block. Response:")
    print(pitchers_response.text)
try:
    pitchers_data = pitchers_response.json()['data']
    print(len(pitchers_data))
except Exception as e:
    print("Failed to parse JSON or bot detection triggered:", e)
    
# time.sleep(10)

for player_data in hitters_data + pitchers_data:
    player_name = player_data['PlayerName']
    href = player_data['Name']
    match = re.search(r'playerid=(\d+)', href)
    player_id = match.group(1) if match else None
    position = re.search(r'position=([\w/]+)', href).group(1) if 'position=' in href else None
    all_fangraphs_players.append({"Player": player_name, "Position": position, "Player_ID": player_id})

unique_players = {tuple(all_fangraphs_players.items()) for all_fangraphs_players in all_fangraphs_players}
flattened_fangraphs_players = [dict(unique_player) for unique_player in unique_players]

merged_players = []
no_match_players = []

#################################################################################################################

for unique_player in unique_list:
    original_mlb_the_show_name = unique_player["Player"]
    unique_name = unidecode(unique_player["Player"]).lower()
    # Remove common suffixes and punctuation
    for suffix in ["jr", "sr", "iii", "ii", "iv", "v"]:
        unique_name = unique_name.replace(suffix, "")
    unique_name = unique_name.replace(".", "")
    unique_name = unique_name.replace("-", " ")
    unique_name = unique_name.replace("'", "")
    unique_name = unique_name.replace(",", "")
    unique_name = unique_name.replace("  ", " ")
    unique_name = unique_name.strip()
    # Remove middle names: keep only first and last
    name_parts = unique_name.split()
    if len(name_parts) > 2:
        unique_name = f"{name_parts[0]} {name_parts[-1]}"
    
    def normalize_player_name(name):
        name = unidecode(name).lower()
        for suffix in ["jr", "sr", "iii", "ii", "iv", "v"]:
            name = name.replace(suffix, "")
        name = name.replace(".", "")
        name = name.replace("-", " ")
        name = name.replace("'", "")
        name = name.replace(",", "")
        name = name.replace("  ", " ")
        name = name.strip()
        name_parts = name.split()
        if len(name_parts) > 2:
            name = f"{name_parts[0]} {name_parts[-1]}"
        return name

    matching = next(
        (
            fg_player for fg_player in flattened_fangraphs_players
            if normalize_player_name(fg_player["Player"]) == unique_name
        ),
        None
    )

    if matching:
        merged_players.append({
            "Player": matching["Player"],
            "Original_MLB_The_Show_Name": original_mlb_the_show_name,
            "Position": matching["Position"],
            "Player_ID": matching["Player_ID"]
        })
    else:
        no_match_players.append({
            "Player": unique_player["Player"],
            "Original_MLB_The_Show_Name": original_mlb_the_show_name,
            "Position": "",
            "Player_ID": ""
        })

# print(len(no_match_players))
# print(merged_players[0:5])
# for player in no_match_players:
#     print(player["Player"])

counter = 0

for player in merged_players:
    time.sleep(3)
    print('################################################# New Player ###########################################################')
    print(player["Player"])
    print(player["Position"])
    print(player["Player_ID"])
    # print(player["Date"])
    print(f"Counter: {counter}")
    
    player_dictionary_entry = {
        "Player": "",
        "Original_MLB_The_Show_Name": "",
        "Position": "",
        "FanGraph_Player_ID": "",
        
        # Hitter Stats
         
        "BA vs Left": "",
        "HR vs Left": "",
        "ABs vs Left": "",
        "HR per AB vs Left": "",
            
        "BA vs Right": "",
        "HR vs Right": "",
        "ABs vs Right": "",
        "HR per AB vs Right": "",
            
        "BA with RISP": "",
        "HR with RISP": "",
        "ABs with RISP": "",
        "HR per AB with RISP": "",
        
        # Pitcher Stats       
        
        "H/9 vs Left": "",
        "H/9 vs Right": "",
        "K/9 vs Left": "",
        "K/9 vs Right": "",
            
        "BB/9": "",
        "Innings/Game": "",
        "OPP BA W RISP": ""
    }
    

    # converted_date = parser.parse(player["Date"]).strftime("%Y-%m-%d")
    # date = (parser.parse(converted_date) - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    test_date = datetime.datetime.now().strftime("%Y-%m-%d")
    opening_day_2024 = "2024-03-28"
    opening_day_2025 = "2025-03-27"
    if test_date.startswith("2024"):
        opening_day = opening_day_2024
    elif test_date.startswith("2025"):
        opening_day = opening_day_2025
    elif test_date.startswith("2026"):
        opening_day = "2026-03-25"
    print(f'Date Range: {opening_day} - {test_date}')
    print("***********************************************************************************************************************")
    # dates_to_get = ["2024-04-23", "2024-05-14", "2024-06-04", "2024-06-25", "2024-07-23"]
    base_api_url = "https://www.fangraphs.com/api/leaders/splits/splits-leaders"
    
    if player["Position"] == "P":
        
        pitchers_standard_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "1"
        }
        
        pitchers_advanced_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "2"
        }
        
        pitchers_with_risp_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [59],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "1"
        }
        
        pitchers_v_lhh_standard_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [5],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "1"
        }
        
        pitchers_v_lhh_advanced_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [5],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "2"
        }
        
        pitchers_v_rhh_standard_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [6],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "1"
        }
        
        pitchers_v_rhh_advanced_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [6],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "2"
        }
        pitcher_standard_response = post_with_retry(session, base_api_url, json=pitchers_standard_payload, headers=headers)
        pitcher_advanced_response = post_with_retry(session, base_api_url, json=pitchers_advanced_payload, headers=headers)
        pitcher_with_risp_response = post_with_retry(session, base_api_url, json=pitchers_with_risp_payload, headers=headers)
        pitcher_v_lhh_standard_response = post_with_retry(session, base_api_url, json=pitchers_v_lhh_standard_payload, headers=headers)
        pitcher_v_lhh_advanced_response = post_with_retry(session, base_api_url, json=pitchers_v_lhh_advanced_payload, headers=headers)
        pitcher_v_rhh_standard_response = post_with_retry(session, base_api_url, json=pitchers_v_rhh_standard_payload, headers=headers)
        pitcher_v_rhh_advanced_response = post_with_retry(session, base_api_url, json=pitchers_v_rhh_advanced_payload, headers=headers)
        
        if pitcher_advanced_response.status_code == 200 and pitcher_with_risp_response.status_code == 200 and pitcher_standard_response.status_code == 200 and pitcher_v_lhh_standard_response.status_code == 200 and pitcher_v_lhh_advanced_response.status_code == 200 and pitcher_v_rhh_standard_response.status_code == 200 and pitcher_v_rhh_advanced_response.status_code == 200:
            print('Successful API responses for all pitcher endpoints')
            # time.sleep(100)
            pitcher_standard_data = pitcher_standard_response.json()
            pitcher_advanced_data = pitcher_advanced_response.json()
            pitcher_with_risp_data = pitcher_with_risp_response.json()
            pitcher_v_lhh_standard_data = pitcher_v_lhh_standard_response.json()
            pitcher_v_lhh_advanced_data = pitcher_v_lhh_advanced_response.json()
            pitcher_v_rhh_standard_data = pitcher_v_rhh_standard_response.json()
            pitcher_v_rhh_advanced_data = pitcher_v_rhh_advanced_response.json()
            
            # print(pitcher_v_lhh_standard_data['v'])
            # print(pitcher_v_lhh_advanced_data['v'])
            
            player_dictionary_entry["Player"] = player["Player"]
            player_dictionary_entry["Original_MLB_The_Show_Name"] = player["Original_MLB_The_Show_Name"]
            player_dictionary_entry["Position"] = player["Position"]
            player_dictionary_entry["FanGraph_Player_ID"] = player["Player_ID"]
            
            if pitcher_with_risp_data['v']:
                player_dictionary_entry["OPP BA W RISP"] = round(float(pitcher_with_risp_data['v'][0][15]), 3)
            
            if pitcher_advanced_data['v']:
                player_dictionary_entry["BB/9"] = float(pitcher_advanced_data['v'][0][5])

            if pitcher_standard_data['v'] and pitcher_advanced_data['v']:
                innings = float(pitcher_advanced_data['v'][0][2])
                games = int(pitcher_standard_data['v'][0][2])
                player_dictionary_entry["Innings/Game"] = innings / games if games != 0 else 0
                # player_dictionary_entry["H/9"] = round((int(pitcher_standard_data['v'][0][5]) / float(pitcher_advanced_data['v'][0][2])) * 9, 8)
            
            if pitcher_v_lhh_standard_data['v'] and pitcher_v_lhh_advanced_data['v']:
                left_innings = float(pitcher_v_lhh_advanced_data['v'][0][2])
                left_hits = int(pitcher_v_lhh_standard_data['v'][0][5])
                player_dictionary_entry["H/9 vs Left"] = round((left_hits * 9) / left_innings, 8) if left_innings != 0 else 0
                player_dictionary_entry["K/9 vs Left"] = round(float(pitcher_v_lhh_advanced_data['v'][0][4]), 1)
            
            if pitcher_v_rhh_standard_data['v'] and pitcher_v_rhh_advanced_data['v']:
                right_innings = float(pitcher_v_rhh_advanced_data['v'][0][2])
                right_hits = int(pitcher_v_rhh_standard_data['v'][0][5])
                player_dictionary_entry["H/9 vs Right"] = round((right_hits * 9) / right_innings, 8) if right_innings != 0 else 0
                player_dictionary_entry["K/9 vs Right"] = round(float(pitcher_v_rhh_advanced_data['v'][0][4]), 1)                 
            
            # print(player_dictionary_entry)
            final_players_list.append(player_dictionary_entry)
            # time.sleep(100)
        else:
            print("One or more non-200 status codes for pitcher endpoints. Responses:")
            print(f"Standard: {pitcher_standard_response.status_code}")
            print(f"Advanced: {pitcher_advanced_response.status_code}")
            print(f"With RISP: {pitcher_with_risp_response.status_code}")
            print(f"v LHH Standard: {pitcher_v_lhh_standard_response.status_code}")
            print(f"v LHH Advanced: {pitcher_v_lhh_advanced_response.status_code}")
            print(f"v RHH Standard: {pitcher_v_rhh_standard_response.status_code}")
            print(f"v RHH Advanced: {pitcher_v_rhh_advanced_response.status_code}")
            time.sleep(5)

    else:
        vLHP_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [1],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "1"
        }
        
        vRHP_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [2],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "1"
        }
        
        with_risp_payload = {
            "arrPlayerId": [],
            "arrWxAirDensity": None,
            "arrWxElevation": None,
            "arrWxPressure": None,
            "arrWxTemperature": None,
            "arrWxWindSpeed": None,
            "dctFilters": [],
            "strAutoPt": "false",
            "strEndDate": test_date,
            "strGroup": "season",
            "strPlayerId": player["Player_ID"],
            "strPosition": player["Position"],
            "strSplitArr": [59],
            "strSplitArrPitch": [],
            "strSplitTeams": False,
            "strStartDate": opening_day,
            "strStatType": "player",
            "strType": "1"
        }

        vLHP_response = post_with_retry(session, base_api_url, json=vLHP_payload, headers=headers)
        vRHP_response = post_with_retry(session, base_api_url, json=vRHP_payload, headers=headers)
        with_risp_response = post_with_retry(session, base_api_url, json=with_risp_payload, headers=headers)

        if vLHP_response.status_code == 200 and vRHP_response.status_code == 200 and with_risp_response.status_code == 200:
            print("Successful API responses for all hitter endpoints")
            # time.sleep(100)
            vLHP_data = vLHP_response.json()
            vRHP_data = vRHP_response.json()
            with_risp_data = with_risp_response.json()
            
            player_dictionary_entry["Player"] = player["Player"]
            player_dictionary_entry["Original_MLB_The_Show_Name"] = player["Original_MLB_The_Show_Name"]
            player_dictionary_entry["Position"] = player["Position"]
            player_dictionary_entry["FanGraph_Player_ID"] = player["Player_ID"]
            
            
            if vLHP_data['v']:
                player_dictionary_entry["BA vs Left"] = round(float(vLHP_data['v'][0][-1]), 3)
                player_dictionary_entry["HR vs Left"] = int(vLHP_data['v'][0][9])
                player_dictionary_entry["ABs vs Left"] = int(vLHP_data['v'][0][4])
                ab_left = int(vLHP_data['v'][0][4])
                hr_left = int(vLHP_data['v'][0][9])
                player_dictionary_entry["HR per AB vs Left"] = hr_left / ab_left if ab_left != 0 else 0
                
            if vRHP_data['v']:
                player_dictionary_entry["BA vs Right"] = round(float(vRHP_data['v'][0][-1]), 3)
                player_dictionary_entry["HR vs Right"] = int(vRHP_data['v'][0][9])
                player_dictionary_entry["ABs vs Right"] = int(vRHP_data['v'][0][4])
                ab_right = int(vRHP_data['v'][0][4])
                hr_right = int(vRHP_data['v'][0][9])
                player_dictionary_entry["HR per AB vs Right"] = hr_right / ab_right if ab_right != 0 else 0
                
                
            if with_risp_data['v']:
                player_dictionary_entry["BA with RISP"] = round(float(with_risp_data['v'][0][-1]), 3)
                player_dictionary_entry["HR with RISP"] = int(with_risp_data['v'][0][9])
                player_dictionary_entry["ABs with RISP"] = int(with_risp_data['v'][0][4])
                ab_risp = int(with_risp_data['v'][0][4])
                hr_risp = int(with_risp_data['v'][0][9])
                player_dictionary_entry["HR per AB with RISP"] = hr_risp / ab_risp if ab_risp != 0 else 0
            
            # print(player_dictionary_entry)
            final_players_list.append(player_dictionary_entry)
        else:
            print("One or more non-200 status codes for hitter endpoints. Responses:")
            print(f"v LHP: {vLHP_response.status_code}")
            print(f"v RHP: {vRHP_response.status_code}")
            print(f"With RISP: {with_risp_response.status_code}")
            time.sleep(5)
    counter += 1
    
# UPDATING PITCHCERS DATA IN GOOGLE SHEETS
current_irl_stats_fangraphs_sheet = sh.worksheet("Current_IRL_Stats_Fangraphs")
    
current_irl_stats_fangraphs_sheet_existing_data = current_irl_stats_fangraphs_sheet.get_all_values()
headers = current_irl_stats_fangraphs_sheet_existing_data[0] if current_irl_stats_fangraphs_sheet_existing_data else []

# Add a section that deletes all existing data except headers before appending new data
if current_irl_stats_fangraphs_sheet_existing_data and len(current_irl_stats_fangraphs_sheet_existing_data) > 1:
    current_irl_stats_fangraphs_sheet.delete_rows(2, len(current_irl_stats_fangraphs_sheet_existing_data))

# append all the data from final_players_list to the google sheet starting from the 2nd column (B) start with the dictionary keys as the headers and then append all of the data
if final_players_list:
    # Prepare rows to append
    rows_to_append = [
        [
            player.get("Player", ""),
            player.get("Original_MLB_The_Show_Name", ""),
            player.get("Position", ""),
            player.get("FanGraph_Player_ID", ""),
            player.get("BA vs Left", ""),
            player.get("HR vs Left", ""),
            player.get("ABs vs Left", ""),
            player.get("HR per AB vs Left", ""),
            
            player.get("BA vs Right", ""),
            player.get("HR vs Right", ""),
            player.get("ABs vs Right", ""),
            player.get("HR per AB vs Right", ""),
            player.get("BA with RISP", ""),
            player.get("HR with RISP", ""),
            player.get("ABs with RISP", ""),
            player.get("HR per AB with RISP", ""),
            player.get("H/9 vs Left", ""),
            player.get("H/9 vs Right", ""),
            player.get("K/9 vs Left", ""),
            player.get("K/9 vs Right", ""),
            player.get("BB/9", ""),
            player.get("Innings/Game", ""),
            player.get("OPP BA W RISP", "")
        ]
        for player in final_players_list
    ]

    # Determine the starting row for the batch update
    start_row = 2  # Start from the second row since we want to keep headers

    # Prepare the range and values for batch_update
    range_to_update = f"B{start_row}:X{start_row + len(rows_to_append) - 1}"

    body = {
        "range": range_to_update,
        "values": rows_to_append
    }

    current_irl_stats_fangraphs_sheet.batch_update([body])

# Print total runtime at the end
end_time = time.time()
total_runtime = end_time - start_time
hours, rem = divmod(total_runtime, 3600)
minutes, seconds = divmod(rem, 60)
print(f"\nScript completed. Total runtime: {int(hours)}h {int(minutes)}m {seconds:.2f}s.")

now = datetime.datetime.now()
est = pytz.timezone('US/Eastern')
now_est = now.astimezone(est)

short_date = now_est.strftime("%m/%d/%y")
current_time = now_est.strftime("%I:%M %p")

current_irl_stats_fangraphs_sheet.update_acell('A1', "Updated: " + short_date + " " + current_time + " EST")

print("--- %s seconds ---" % (time.time() - start_time))
