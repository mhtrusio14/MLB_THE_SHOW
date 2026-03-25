import requests
import gspread
import time
import datetime
import pytz
from unidecode import unidecode
import re
import json
import os
import random

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

print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ NEW CODE $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')

user_agents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15", #5 for 5 on testing
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0", # 5 for 5 on testing
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.15"
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
    "Referer": "https://mlb26.theshow.com",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

session = requests.Session()

def robust_api_get(url, max_retries=5, backoff_factor=1.5):
    """
    Makes a GET request with retries and exponential backoff for 403/429 errors.
    Randomizes User-Agent for each request.
    """
    for attempt in range(1, max_retries + 1):
        # Randomize User-Agent for each request
        headers["User-Agent"] = random.choice(user_agents)
        try:
            resp = session.get(url, headers=headers, timeout=20)
            if resp.status_code == 403 or resp.status_code == 429:
                print(f"[WARN] {resp.status_code} error on {url} (attempt {attempt})")
                print(f"Response: {resp.text[:500]}")
                if attempt == max_retries:
                    resp.raise_for_status()
                sleep_time = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
                print(f"Sleeping {sleep_time:.2f}s before retry...")
                time.sleep(sleep_time)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            print(f"[ERROR] Request failed: {e} (attempt {attempt})")
            if attempt == max_retries:
                raise
            sleep_time = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(f"Sleeping {sleep_time:.2f}s before retry...")
            time.sleep(sleep_time)
    raise Exception(f"Failed to GET {url} after {max_retries} attempts.")

while True:
    url = f"{base_url}?page={counter}"
    print(url)
    api_call = robust_api_get(url)
    try:
        api_json = api_call.json()
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON for {url}: {e}")
        print(f"Response text: {api_call.text[:500]}")
        raise

    if counter == int(api_json['total_pages']) + 1:
        break

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
        # time.sleep(1)  # Uncomment if you want to slow down requests

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
