import requests
import gspread
import time
import datetime
import pytz
from unidecode import unidecode
import re
import json

start_time = time.time()

creds_json = os.environ['CREDS']
CREDS = json.loads(creds_json)

gc = gspread.service_account_from_dict(CREDS)

sh = gc.open("Roster Update Prediction Bot")

worksheet = sh.worksheet("Players_Prices")

base_url = 'https://mlb25.theshow.com/apis/listings.json' # replace with 2025 endpoint

counter = 1
row_counter = 2
update_counter = 0
cards_info = []

while True:
    # print(counter)
    url = f"{base_url}?page={counter}"
    print(url)
    api_call = requests.get(url)
    api_json = api_call.json()
    
    if counter == int(api_json['total_pages']) + 1:
        break
    
    batch_update_values = []
    
    # print(api_json['listings'])
    for listing in api_json['listings']:
        if listing['item']['series'] == "Live":
            cards_info.append({
                'NAME': listing['item']['name'],
                'UUID': listing['item']['uuid'],
                'SERIES': listing['item']['series'],
                'TEAM': listing['item']['team'],
                'OVERALL': listing['item']['ovr'],
                'POSITION': listing['item']['display_position'],
                'SET': listing['item']['set_name'],
                'IS_LIVE': listing['item']['is_live_set'],
                'BUY_PRICE': listing['best_buy_price'],
                'SELL_PRICE': listing['best_sell_price']
            })

            if update_counter == 59:
                print("Sleeping..........")
                time.sleep(70)
                update_counter = 0
                

            row_values = [
                cards_info[row_counter - 2]['NAME'],
                cards_info[row_counter - 2]['UUID'],
                cards_info[row_counter - 2]['SERIES'],
                cards_info[row_counter - 2]['TEAM'],
                cards_info[row_counter - 2]['OVERALL'],
                cards_info[row_counter - 2]['POSITION'],
                cards_info[row_counter - 2]['SET'],
                cards_info[row_counter - 2]['IS_LIVE'],
                cards_info[row_counter - 2]['BUY_PRICE'],
                cards_info[row_counter - 2]['SELL_PRICE']
            ]

            batch_update_values.append(row_values)

            row_counter += 1

    
    # print(len(cards_info))
            
    worksheet.batch_update([
        {
            'range': f'B{index}:K{index}',
            'values': [row_values]
        } for index, row_values in enumerate(batch_update_values, start=row_counter - len(batch_update_values))
    ])
    
    update_counter += 1
    counter += 1

print("Getting Espn IDs Now")

# ESPN API endpoint
API_ENDPOINT = "https://sports.core.api.espn.com/v3/sports/baseball/mlb/athletes?limit=10000"

# Fetch player data from Google Sheets
players_data = worksheet.get_all_records()

# Fetch player data from ESPN API
response = requests.get(API_ENDPOINT)
if response.status_code != 200:
    raise Exception("Failed to fetch data from ESPN API")
espn_data = response.json()

# Create a dictionary mapping player display names to their ESPN IDs
espn_players = {unidecode(player["displayName"]): player["id"] for player in espn_data["items"]}

# Function to sanitize names
def sanitize_name(name):
    # Remove ".", "-", and "Jr."
    return re.sub(r'[\.-]|Jr\.?', '', name).strip()

# Collect all updates to be made
updates = []

for idx, player in enumerate(players_data, start=2):
    name = unidecode(player["NAME"])
    espn_id = espn_players.get(name)

    if not espn_id:
        # Sanitize name if no match is found initially
        sanitized_name = sanitize_name(name)
        espn_id = espn_players.get(sanitized_name)
        
    if espn_id:
        updates.append({
            "range": f"L{idx}",
            "values": [[espn_id]]
        })

# Perform the batch update
if updates:
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": updates
    }
    worksheet.batch_update(body["data"])
    
now = datetime.datetime.now()
est = pytz.timezone('US/Eastern')
now_est = now.astimezone(est)

short_date = now_est.strftime("%m/%d/%y")
current_time = now_est.strftime("%I:%M %p")

worksheet.update_acell('A1', "Updated: " + short_date + " " + current_time + " EST")

print("--- %s seconds ---" % (time.time() - start_time)) 
