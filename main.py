import requests
import gspread
import time
import datetime
import pytz
import os
import json

start_time = time.time()

creds_json = os.environ['CREDS']
CREDS = json.loads(creds_json)

gc = gspread.service_account_from_dict(CREDS)

sh = gc.open("MLB The Show 25 Helper")

worksheet = sh.worksheet("Players")

base_url = 'https://mlb25.theshow.com/apis/listings.json'

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
            time.sleep(60)
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

now = datetime.datetime.now()
est = pytz.timezone('US/Eastern')
now_est = now.astimezone(est)

short_date = now_est.strftime("%m/%d/%y")
current_time = now_est.strftime("%I:%M %p")

worksheet.update_acell('A1', "Prices Updated: " + short_date + " " + current_time + " EST")

flipping_helper_sheet = sh.worksheet("Flipping Helper")

# Copy data from Players worksheet to Flipping Helper and filter rows with column L > 0
players_data = worksheet.get_all_values()

# Filter rows with column L > 0
filtered_rows = [row for row in players_data if row[1] != "NAME" and float(row[11]) > 0]

# Sort filtered rows based on column L
filtered_rows.sort(key=lambda x: float(x[11]), reverse=True)

# Get header row from Players worksheet
header_row = players_data[0]

# Insert header row into the filtered and sorted data
filtered_rows.insert(0, header_row)

# Update Flipping Helper worksheet with sorted and filtered data
flipping_helper_sheet.clear()
flipping_helper_sheet.update(filtered_rows)

print("--- %s seconds ---" % (time.time() - start_time)) 
