import requests
import gspread
import time
import datetime
import pytz
from unidecode import unidecode
import re
import json
import os

start_time = time.time()

creds_json = os.environ['CREDS']
CREDS = json.loads(creds_json)

gc = gspread.service_account_from_dict(CREDS)

sh = gc.open("Roster Update Prediction Bot")

worksheet = sh.worksheet("Players_Prices")

base_url = 'https://mlb26.theshow.com/apis/listings.json' # replace with 2025 endpoint

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
                'SET': "",
                'IS_LIVE': "",
                'BUY_PRICE': listing['best_buy_price'],
                'SELL_PRICE': listing['best_sell_price'],
                'IMG_URL': listing['item']['baked_img']
            })
        # print(cards_info)
        # time.sleep(1)  # Sleep for 1 second between API calls to avoid rate limits
            
    counter += 1

print("Getting Espn IDs Now")

API_ENDPOINT = "https://sports.core.api.espn.com/v3/sports/baseball/mlb/athletes?limit=10000"
response = requests.get(API_ENDPOINT)
if response.status_code != 200:
    raise Exception("Failed to fetch data from ESPN API")
espn_data = response.json()
espn_players = {unidecode(player["displayName"]): player["id"] for player in espn_data["items"]}

def sanitize_name(name):
    return re.sub(r'[\.-]|Jr\.?', '', name).strip()

# print(cards_info[0])
# time.sleep(10)


# Append ESPN_ID to each player dict in cards_info
for player in cards_info:
    name = unidecode(player['NAME'])
    espn_id = espn_players.get(name)
    if not espn_id:
        sanitized_name = sanitize_name(name)
        espn_id = espn_players.get(sanitized_name)
    player['ESPN_ID'] = espn_id if espn_id else ""

# Prepare data for batch update (list of lists, including ESPN_ID as last column)
batch_update_values = [
    [
        player['NAME'],
        player['UUID'],
        player['SERIES'],
        player['TEAM'],
        player['OVERALL'],
        player['POSITION'],
        player['SET'],
        player['IS_LIVE'],
        player['BUY_PRICE'],
        player['SELL_PRICE'],
        player['IMG_URL'],
        player['ESPN_ID']
    ]
    for player in cards_info
]

# Clear all rows except headers before updating
num_rows = len(worksheet.get_all_values())
if num_rows > 1:
    worksheet.batch_clear([f"B2:M{num_rows}"])

# Batch update the whole sheet at once (A2:M...)
worksheet.update(f"B2:M{len(batch_update_values)+1}", batch_update_values)

now = datetime.datetime.now()
est = pytz.timezone('US/Eastern')
now_est = now.astimezone(est)
short_date = now_est.strftime("%m/%d/%y")
current_time = now_est.strftime("%I:%M %p")
worksheet.update_acell('A1', "Updated: " + short_date + " " + current_time + " EST")
print("--- %s seconds ---" % (time.time() - start_time))
