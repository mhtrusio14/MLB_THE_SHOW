import requests
import gspread
import time
import datetime
import pytz

start_time = time.time()

CREDS = {
  "type": "service_account",
  "project_id": "mlb-the-show-422202",
  "private_key_id": "8a9641dc74f0efdec3a973454abfc2bc57f30f07",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQC4ql22EfHE/kR2\nBJgoXs3nfGtw2S87hAY4lMX39aX37SbTXVbdhnNq+RPWDOVm4VtmsMKoZy3Wg7of\nL1cG34EznMbGEGP+2wOqH8DX/T8cu/eVkNvou3/91aExnr3Ynw76yYoDpTEKKmci\nCJLRsE78hNqnu8U3arDunBu6uUCatoALQ1dHYho2KzA8yyeyVfnTBnmFDjPiTS9F\nKzl7ONtB4wxmbi4FTNHYcBuRVYtyQIxjlBykO/7vGYIRP4o0ZidEzjXVeFShtsmP\niNzWC4uHjhE3ZBkbAVS5QkezI05Ef34TcO4hrT2XB9rQr9zhf38II6Oo3K7n2b5J\ns6ezJKLzAgMBAAECggEAIRSDzQXR5ZQW931DNJgnEny7Um/VgjfYVXJxNEYRASS+\ne8aQtQZMzrDn2MReo9ti4DZx6HDzSSY3xTZZxKVtI63F/d0ZzKG3OlaN2SNIlwEl\nDOnyOvK7ruECCz2AjLmRmWNZEeYZrtSBvRsEEgQfYiT6dmmwnojCQTw9y2k8JXqV\nTuz60kFk5xOc3UW3rEu72wDWdHuAe4+CAZKKIRxr4Qi4sZCsaxVMHzmTQYfnQLxv\nL1l+j/4eVc8e/q5TPu6o+iO3WnO5gzhT36YxK7R4c2M0SVFxBBHYAQsknyuskhn3\nyoznPBDMoPhyH9Eh4QiidZIvmA4waDS5TYQ/66N0wQKBgQD3lDQ2h1fzO4D78ckG\npDGZV3yRV+5euA5D3HqcWepiTsMWZzIOLN22RWRx2RThALt8W17XHj9XfXHyWRpm\n/kIMQjFOBuZeoClJALXM772/X7dQ7ITTgVZQVmYJh3bT92xeZXWJ6EthPtO06c5u\nhdJV1R+vyjZrcq1hwPOZ6MKryQKBgQC+8le/KgLYCCxXr7Hc+i5RKKlc2iHnrUFT\n4PVwer3sDXQBopL0losJVVd+NwGWG0NMTtgTVm956kCe21q83wz+S92BXBD1ayPO\ntdr7RgoFjTMgqaVkW2piFo8Dl+lHJkrRbduadLF69wN/TMYBiyiBa8idjqB/J0Ii\nZQrF1Xk+2wKBgQCucF3ZjcMKPgLDgbiCVW4c/OdoAOyTEFv8tHwvbasXWSdbwZoj\nIrmUk5ASJ0HuxvVSyY4pQ8adfmWqu90+dCdVO85Bi9sFERQFu9pcaw7mqCoheoSc\nAaUvNbDvReMTtmFEoXgPkvyJqBrCfXpVpTRuBZwt3+w4CLThC3KYHsgLAQKBgQCt\ndlpgPzn2JvahceqSZHRPJjE1OLQ0UyBVordVRyvhlRcdpSL7Lwd/oxeogS/fvUSV\nvcptRsheaH/r0DnN+pNDMIg5S/nb+Ui+MFaOjkHsaSlZMsQdNy6djQC+svIowJCX\nUMV+uyPAIUX8DzKRlGlnqRLGjxseZ/ucY042CofqoQKBgQC1ND9ezsJcapo0Hy+I\nNNEvxj/exy/9zs5MUzoiNqzt5z7dz9ff1n3tLRS+rc3yXjAwyy/2B2GERVGCBgfI\nhGkgOLJtdLKFs623zal348acetIprFELt8W15iU8+LjctwgYRL3DgqUwa4hiL4lC\nzOG5iVl6k9/XjTB2qDC91QZotg==\n-----END PRIVATE KEY-----\n",
  "client_email": "mlb-the-show-bot@mlb-the-show-422202.iam.gserviceaccount.com",
  "client_id": "107878503647520206684",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mlb-the-show-bot%40mlb-the-show-422202.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

gc = gspread.service_account_from_dict(CREDS)

sh = gc.open("MLB The Show Helper")

worksheet = sh.worksheet("Players")

base_url = 'https://mlb24.theshow.com/apis/listings.json'

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