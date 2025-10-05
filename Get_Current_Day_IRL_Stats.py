import requests
import json
import gspread
import time
import datetime
import pytz
import os
from datetime import datetime
from bs4 import BeautifulSoup

start_time = time.time()

creds_json = os.environ['CREDS']
CREDS = json.loads(creds_json)

client = gspread.service_account_from_dict(CREDS)

# Open the spreadsheet
spreadsheet = client.open("Roster Update Prediction Bot")

# Get the Players sheet
players_sheet = spreadsheet.worksheet("Current_Day_IRL_Stats")

base_url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/"

current_players = []

teams = ['ari', 'ath', 'atl', 'bal', 'bos', 'chc', 'chw', 'cin', 'cle', 'col', 'det', 'hou', 'kc', 'laa', 'lad', 'mia', 'mil', 'min', 'nym', 'nyy', 'phi', 'pit', 'sd', 'sea', 'sf', 'stl', 'tb', 'tex', 'tor', 'wsh']

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
}

## Loop Depth Chart Pages
print("Getting Depth Chart Pages")

for team in teams:
    url = f'https://www.espn.com/mlb/team/depth/_/name/{team}'
    # print(url)
    api_call = requests.get(url, headers=headers)
    soup = BeautifulSoup(api_call.text, "html.parser")
    team_name_full = soup.find('h1', class_='headline headline__h1 dib').text.strip()
    team_name = team_name_full.split(" Depth Chart")[0]
    # print(f"Team Name: {team_name}")
    tr_elements = soup.find_all('tr', class_='Table__TR Table__TR--sm Table__even')
    for tr in tr_elements:
        if tr.find('span', class_='fw-medium'):
            row_index = tr['data-idx']
            # print(f"Row Index: {row_index}")
            tds = tr.find_all('td', class_='Table__TD')
            for td in tds:
                # print(td)
                a_tag = td.find('a', href=True)
                if a_tag:
                    href = a_tag['href']
                    player_id = href.split('/')[-1]
                    player_name = a_tag.text.strip()
                    row_idx = int(row_index)
                    if row_idx == 0:
                        player_position = "SP"
                    elif row_idx == 1:
                        player_position = "RP"
                    elif row_idx == 2:
                        player_position = "CP"
                    elif row_idx == 3:
                        player_position = "C"
                    elif row_idx == 4:
                        player_position = "1B"
                    elif row_idx == 5:
                        player_position = "2B"
                    elif row_idx == 6:
                        player_position = "3B"
                    elif row_idx == 7:
                        player_position = "SS"
                    elif row_idx == 8:
                        player_position = "LF"
                    elif row_idx == 9:
                        player_position = "CF"
                    elif row_idx == 10:
                        player_position = "RF"
                    elif row_idx == 11:
                        player_position = "DH"
                    # print(f"Player ID: {player_id}, Player Name: {player_name}, Player Position: {player_position}")
                    
                    # Only append if player_name isn't already in current_players
                    if not any(p['Player_Name'] == player_name for p in current_players):
                        current_players.append({
                            'Player_Name': player_name,
                            'Player_ID': player_id,
                            'Team': team_name,
                            'Player_Position': player_position,
                            
                            'At Bats': "",
                            'At Bats v LEFT': "",
                            'At Bats v RIGHT': "",
                            'Batting Average': "",
                            'Home Runs': "",
                            'BA w RISP': "",
                            'HR v LEFT': "",
                            'HR v RIGHT': "",
                            'BA v LEFT': "",
                            'BA v RIGHT': "",
                            'HR v LEFT / AB v Left': "",
                            'HR v RIGHT / AB v Right': "",
                            'OPS': "",
                            'RBIS': "",
                            
                            'IP': "",
                            'GP': "",
                            'Hits Allowed': "",
                            'Ks': "",
                            'OPP BA w RISP': "",
                            'ERA': "",
                            'Walks': "",
                            'H/9': "",
                            'BB/9': "",
                            'K/9': "",
                            'IP Per Game': ""
                        })

# Loop Roster Pages
print("Getting Roster Pages")                        

for i in range(30):
    
    i += 1
    url = f"{base_url}{i}/roster"
    api_call = requests.get(url)
    api_json = api_call.json()
    
    team = api_json['team']['displayName']
    # print(f"Team: {team}")
    players = api_json['athletes']
    
    for position in players:
        #print(f"Curent Position: {position['position']}")
        for player in position['items']:
            player_name = player['displayName']
            player_position = player['position']['abbreviation']
            player_id = player['id']
            
            if not any(p['Player_Name'] == player_name for p in current_players):
                current_players.append({
                    'Player_Name': player_name,
                    'Player_ID': player_id,
                    'Team': team,
                    'Player_Position': player_position,
                    
                    'At Bats': "",
                    'At Bats v LEFT': "",
                    'At Bats v RIGHT': "",
                    'Batting Average': "",
                    'Home Runs': "",
                    'BA w RISP': "",
                    'HR v LEFT': "",
                    'HR v RIGHT': "",
                    'BA v LEFT': "",
                    'BA v RIGHT': "",
                    'HR v LEFT / AB v Left': "",
                    'HR v RIGHT / AB v Right': "",
                    'OPS': "",
                    'RBIS': "",
                    
                    'IP': "",
                    'GP': "",
                    'Hits Allowed': "",
                    'Ks': "",
                    'OPP BA w RISP': "",
                    'ERA': "",
                    'Walks': "",
                    'H/9': "",
                    'BB/9': "",
                    'K/9': "",
                    'IP Per Game': ""
                })


# Loop Injuries Pages
print("Getting Injuries Pages")

for team in teams:
    url = f'https://www.espn.com/mlb/team/injuries/_/name/{team}'
    # print(url)
    api_call = requests.get(url, headers=headers)
    soup = BeautifulSoup(api_call.text, "html.parser")
    team_name_full = soup.find('h1', class_='headline headline__h1 dib headline__capitalize').text.strip()
    team_name = team_name_full.split(" Injuries")[0]
    # print(f"Team Name: {team_name}")
    # time.sleep(10000)
    list_items = [
        item for item in soup.find_all('div', class_='ContentList__Item')
        if item.find('a', class_='Athlete')
    ]
    # print(list_items[0])
    for item in list_items:
        href = item.find('a', class_='Athlete')['href']
        player_id = href.split('/')[-1]
        player_name = item.find('span', class_='Athlete__PlayerName').text.strip()
        player_position = item.find('span', class_='Athlete__NameDetails').text.strip()
        # print(f"Player ID: {player_id}, Player Name: {player_name}, Player Position: {player_position}")
        if not any(p['Player_Name'] == player_name for p in current_players):
                current_players.append({
                    'Player_Name': player_name,
                    'Player_ID': player_id,
                    'Team': team_name,
                    'Player_Position': player_position,
                    
                    'At Bats': "",
                    'At Bats v LEFT': "",
                    'At Bats v RIGHT': "",
                    'Batting Average': "",
                    'Home Runs': "",
                    'BA w RISP': "",
                    'HR v LEFT': "",
                    'HR v RIGHT': "",
                    'BA v LEFT': "",
                    'BA v RIGHT': "",
                    'HR v LEFT / AB v Left': "",
                    'HR v RIGHT / AB v Right': "",
                    'OPS': "",
                    'RBIS': "",
                    
                    'IP': "",
                    'GP': "",
                    'Hits Allowed': "",
                    'Ks': "",
                    'OPP BA w RISP': "",
                    'ERA': "",
                    'Walks': "",
                    'H/9': "",
                    'BB/9': "",
                    'K/9': "",
                    'IP Per Game': ""
                })

print('Finished looping through all teams')

# Hitter: Aaron Judge
# Pitcher: Chris Sale            
# Test Hitter Stats: https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/33192/stats?region=us&lang=en&contentorigin=espn&category=batting
# Test Pitcher Stats: https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/30948/stats?region=us&lang=en&contentorigin=espn&category=pitching
# Test Pitcher Splits: https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/30948/splits?region=us&lang=en&contentorigin=espn&season=2024&category=pitching
# Test Hitter Splits: https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/33192/splits?region=us&lang=en&contentorigin=espn&season=2024&category=batting


stats_url = 'https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/'
# pitcher_stats_url_suffix = '/stats?region=us&lang=en&contentorigin=espn&category=pitching'
# hitter_stats_url_suffix = '/stats?region=us&lang=en&contentorigin=espn&category=batting'

current_year = time.strftime("%Y")
# use current year
pitcher_splits_url_suffix = f'/splits?region=us&lang=en&contentorigin=espn&season=2025&category=pitching'
hitter_splits_url_suffix = f'/splits?region=us&lang=en&contentorigin=espn&season=2025&category=batting'

print("Getting Stats")
    
for player in current_players:
    try:
        if player['Player_Position'] in ["CP", "SP", "RP"]:
            full_splits_url = f"{stats_url}{player['Player_ID']}{pitcher_splits_url_suffix}"
            try:
                splits_api = requests.get(full_splits_url)
                api_json = splits_api.json()
                if 'splits' in api_json['splitCategories'][0]:
                    try:
                        player['IP'] = api_json['splitCategories'][0]['splits'][0]['stats'][8]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting IP")
                    try:
                        player['GP'] = api_json['splitCategories'][0]['splits'][0]['stats'][5]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting Games Played")
                    try:
                        player['Hits Allowed'] = api_json['splitCategories'][0]['splits'][0]['stats'][9]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting Hits Allowed")
                    try:
                        player['Ks'] = api_json['splitCategories'][0]['splits'][0]['stats'][14]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting Ks")
                    try:
                        player['OPP BA w RISP'] = api_json['splitCategories'][10]['splits'][2]['stats'][12]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting OPP BA w RISP")
                    try:
                        player['ERA'] = api_json['splitCategories'][0]['splits'][0]['stats'][0]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting ERA")
                    try:
                        player['Walks'] = api_json['splitCategories'][0]['splits'][0]['stats'][13]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting Walks")
            except requests.RequestException as e:
                print("Error Getting Splits")
                print(f"RequestException: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting splits")
            
            if player['IP'] != "" or player['IP'] != "0":
                player['H/9'] = round(float(player['Hits Allowed']) / float(player['IP']) * 9, 2)
                player['BB/9'] = round(float(player['Walks']) / float(player['IP']) * 9, 2)
                player['K/9'] = round(float(player['Ks']) / float(player['IP']) * 9, 2)
                player['IP Per Game'] = round(float(player['IP']) / float(player['GP']), 2)
        else:
            full_splits_url = f"{stats_url}{player['Player_ID']}{hitter_splits_url_suffix}"
            try:
                splits_api = requests.get(full_splits_url)
                api_json = splits_api.json()
                if 'splits' in api_json['splitCategories'][0]:
                    try:
                        player['At Bats'] = api_json['splitCategories'][0]['splits'][0]['stats'][0]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting At Bats")
                    try:
                        player['At Bats v LEFT'] = api_json['splitCategories'][1]['splits'][0]['stats'][0]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting AB v LEFT")
                    try:
                        player['At Bats v RIGHT'] = api_json['splitCategories'][1]['splits'][1]['stats'][0]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting AB v RIGHT")
                    try:
                        player['Batting Average'] = api_json['splitCategories'][0]['splits'][0]['stats'][12]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting Batting Average")
                    try:
                        player['Home Runs'] = api_json['splitCategories'][0]['splits'][0]['stats'][5]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting Home Runs")
                    try:
                        player['BA w RISP'] = api_json['splitCategories'][8]['splits'][2]['stats'][12]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting BA w RISP")
                    try:
                        player['HR v LEFT'] = api_json['splitCategories'][1]['splits'][0]['stats'][5]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting HR v LEFT")
                    try:
                        player['HR v RIGHT'] = api_json['splitCategories'][1]['splits'][1]['stats'][5]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting HR v RIGHT")
                    try:
                        player['BA v LEFT'] = api_json['splitCategories'][1]['splits'][0]['stats'][12]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting BA v LEFT")
                    try:
                        player['BA v RIGHT'] = api_json['splitCategories'][1]['splits'][1]['stats'][12]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting BA v RIGHT")
                    try:
                        player['OPS'] = api_json['splitCategories'][0]['splits'][0]['stats'][15]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting OPS")
                    try:
                        player['RBIS'] = api_json['splitCategories'][0]['splits'][0]['stats'][6]
                    except (KeyError, IndexError) as e:
                        print(f"KeyError or IndexError: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting RBIS")
            except requests.RequestException as e:
                print("Error Getting Splits")
                print(f"RequestException: {e} for player {player['Player_Name']} with ID {player['Player_ID']} when getting splits")
                
            if player['At Bats'] != "" or player['At Bats'] != "0":
                player['HR v LEFT / AB v Left'] = round(float(player['HR v LEFT']) / float(player['At Bats v LEFT']), 4)
                player['HR v RIGHT / AB v Right'] = round(float(player['HR v RIGHT']) / float(player['At Bats v RIGHT']), 4)
    except Exception as e:
        print("Overall Error")
        print(f"Error processing player {player['Player_Name']} with ID {player['Player_ID']}: {e}")

# Prepare the data to update (excluding the headers in the list)
data_to_update = []

# Get the headers from the first player dictionary
headers = list(current_players[0].keys())

# Append the player data directly
for player in current_players:
    row = [player[key] for key in headers]
    data_to_update.append(row)

# Calculate the end column letter
def get_column_letter(col_num):
    string = ""
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        string = chr(65 + remainder) + string
    return string

end_column = get_column_letter(len(headers) + 1)

# Update the sheet, starting from cell B2
cell_range = f'B2:{end_column}{len(data_to_update) + 1}'
players_sheet.update(cell_range, data_to_update)

now = datetime.now()
est = pytz.timezone('US/Eastern')
now_est = now.astimezone(est)

short_date = now_est.strftime("%m/%d/%y")
current_time = now_est.strftime("%I:%M %p")

players_sheet.update_acell('A1', "Updated: " + short_date + " " + current_time + " EST")

print("--- %s seconds ---" % (time.time() - start_time))
