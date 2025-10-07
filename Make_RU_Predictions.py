import requests
import gspread
import time
import datetime
import pytz
from unidecode import unidecode
import re
import json
import os

def remove_middle_initials(name):
  parts = name.split()
  if len(parts) > 2:
    return f"{parts[0]} {parts[-1]}"
  return name

def clean_row(row, headers):
  cleaned = []
  for idx, cell in enumerate(row):
    col = headers[idx]
    if col in ("Player", "Name"):
      val = remove_middle_initials(
        re.sub(r'\bJr\.?\b', '', re.sub(r'[^A-Za-z0-9 ]+', '', unidecode(str(cell)))).strip()
      )
    else:
      val = str(cell).strip()
    cleaned.append(val)
  return cleaned

start_time = time.time()

creds_json = os.environ['CREDS']
CREDS = json.loads(creds_json)

gc = gspread.service_account_from_dict(CREDS)

sh = gc.open("Roster Update Prediction Bot")
current_in_game_stats_sheet = sh.worksheet("Current_In_Game_Stats") ## Driver sheets for current calculations
current_day_irl_stats_sheet = sh.worksheet("Current_Day_IRL_Stats")

historical_ru_data_sheet = sh.worksheet("Historical_RU_Data")
historical_irl_stats_hitters_sheet = sh.worksheet("Historical_IRL_Stats_Hitters")
historical_irl_stats_pitchers_sheet = sh.worksheet("Historical_IRL_Stats_Pitchers")

thresholds_sheet = sh.worksheet("Thresholds")
calculation_sheet = sh.worksheet("Calculations")

# Get all values from the Current_In_Game_Stats sheet in cols B to U and save it to a list of dictionaries with the first row as the keys

headers = [re.sub(r'[^A-Za-z0-9 ]+', '', unidecode(h)) for h in current_in_game_stats_sheet.get("B1:AI")[0]]
rows = current_in_game_stats_sheet.get("B2:AI")
cleaned_rows = [clean_row(row, headers) for row in rows]
current_in_game_stats = [dict(zip(headers, row)) for row in cleaned_rows]

# Get all values from the Current_Day_IRL_Stats sheet in cols B to AD and save it to a list of dictionaries with the first row as the keys

headers_irl = [re.sub(r'[^A-Za-z0-9 ]+', '', unidecode(h)) for h in current_day_irl_stats_sheet.get("B1:AD1")[0]]
rows_irl = current_day_irl_stats_sheet.get("B2:AD")
cleaned_rows_irl = [clean_row(row, headers_irl) for row in rows_irl]
current_day_irl_stats = [dict(zip(headers_irl, row)) for row in cleaned_rows_irl]

# loop through current_in_game_stats and find the player match with the value in current_day_irl_stats
# when you find a match combine the 2 lists entries and append it to a new list of dictionaries called current_players

current_players = []
no_match_current_players = []

for in_game_player in current_in_game_stats:
  match = next((irl_player for irl_player in current_day_irl_stats if irl_player.get('Player') == in_game_player.get('Name')), None)
  if match:
    combined = {**in_game_player, **match}
    current_players.append(combined)
  else:
    no_match_current_players.append(in_game_player)

## NOTE: We are still not perfectly matching all players
## If a player is currently in the minors we cannot match them
## If a player is Mike on Mlb the Show and Michael in real life we cannot match them
## If a player is currently not on a team we cannot match

# Get all values from Historical_RU_Data sheet in cols B to AT
ru_data_headers = [re.sub(r'[^A-Za-z0-9 ]+', '', unidecode(h)) for h in historical_ru_data_sheet.get("B1:AT1")[0]]
ru_data_rows = historical_ru_data_sheet.get("B2:AT")
ru_data_cleaned_rows = [clean_row(row, ru_data_headers) for row in ru_data_rows]
historical_ru_data = [dict(zip(ru_data_headers, row)) for row in ru_data_cleaned_rows]

historical_ru_hitters_data = [row for row in historical_ru_data if row.get('Player Type') == 'Hitter']
historical_ru_pitchers_data = [row for row in historical_ru_data if row.get('Player Type') == 'Pitcher']

# Get all values from Historical_IRL_Stats_Hitters sheet in cols B to Q
irl_hitters_headers = [re.sub(r'[^A-Za-z0-9 ]+', '', unidecode(h)) for h in historical_irl_stats_hitters_sheet.get("B1:Q1")[0]]
irl_hitters_rows = historical_irl_stats_hitters_sheet.get("B2:Q")
irl_hitters_cleaned_rows = [clean_row(row, irl_hitters_headers) for row in irl_hitters_rows]
historical_irl_hitters_data = [dict(zip(irl_hitters_headers, row)) for row in irl_hitters_cleaned_rows]

# Get all values from Historical_IRL_Stats_Pitchers sheet in cols B to J
irl_pitchers_headers = [re.sub(r'[^A-Za-z0-9 ]+', '', unidecode(h)) for h in historical_irl_stats_pitchers_sheet.get("B1:J1")[0]]
irl_pitchers_rows = historical_irl_stats_pitchers_sheet.get("B2:J")
irl_pitchers_cleaned_rows = [clean_row(row, irl_pitchers_headers) for row in irl_pitchers_rows]
historical_irl_pitchers_data = [dict(zip(irl_pitchers_headers, row)) for row in irl_pitchers_cleaned_rows]


# Match Hisorical Hitters Data to each other
historical_hitters = []
no_match_historical_hitters = []

for ru_entry in historical_ru_hitters_data:
  player = ru_entry.get('Player')
  date = ru_entry.get('Date')
  date_obj = datetime.datetime.strptime(date, "%m/%d/%Y")
  target_date = (date_obj - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
  match = next(
    (irl_entry for irl_entry in historical_irl_hitters_data
     if irl_entry.get('Player') == player and irl_entry.get('Date') == target_date),
    None
  )
  if match:
    combined = {**ru_entry, **match}
    historical_hitters.append(combined)
  else:
    no_match_historical_hitters.append(ru_entry)

# print(f"Matched {len(historical_hitters)} historical hitters entries.")
# print(f"Example match: {historical_hitters[0]}")
# time.sleep(1000)
# print(f"Found {len(no_match_historical_hitters)} historical hitters entries with no IRL match.")
# print(f"Example no match: {no_match_historical_hitters}")
# Match Historical Pitchers Data to each other
historical_pitchers = []
no_match_historical_pitchers = []

for ru_entry in historical_ru_pitchers_data:
  player = ru_entry.get('Player')
  date = ru_entry.get('Date')
  date_obj = datetime.datetime.strptime(date, "%m/%d/%Y")
  target_date = (date_obj - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
  match = next(
    (irl_entry for irl_entry in historical_irl_pitchers_data
     if irl_entry.get('Player') == player and irl_entry.get('Date') == target_date),
    None
  )
  if match:
    combined = {**ru_entry, **match}
    historical_pitchers.append(combined)
  else:
    no_match_historical_pitchers.append(ru_entry)

# print(f"Matched {len(historical_pitchers)} historical pitchers entries.")
# print(f"Example match: {historical_pitchers[0]}")
# time.sleep(1000)
# print(f"Found {len(no_match_historical_pitchers)} historical pitchers entries with no IRL match.")
# print(f"Example no match: {no_match_historical_pitchers}")

# Get Thresholds from the thresholds sheet
thresholds_headers = thresholds_sheet.get("A1:G1")[0]
thresholds_rows = thresholds_sheet.get("A2:G")
thresholds = [dict(zip(thresholds_headers, row)) for row in thresholds_rows]

# apply logic and thresholds to take current_players and historical stats and calculate the predictions
# Append threshold values to the current_players list
players_w_thresholds = []

for live_player in current_players:
  player_name = live_player.get('Name')
  # print(live_player)
  
  if player_name == "Shohei Ohtani":
    player_position = "P/DH"
  else:
    player_position = live_player.get('Position')

  # Prepare a dict to store threshold values for this player
  player_thresholds = {}

  if player_position in ("SP", "RP", "CP", "P/DH"):
    player_k_per_9 = int(live_player.get('Ks Per 9'))
    player_bb_per_9 = int(live_player.get('BB Per 9'))
    player_hit_per_9 = int(live_player.get('Hit Per 9'))
    player_pitching_clutch = int(live_player.get('Pitching Clutch'))
    player_stamina = int(live_player.get('Stamina'))

    player_irl_k_per_9 = float(live_player.get('K9', 0) or 0)
    player_irl_bb_per_9 = float(live_player.get('BB9', 0) or 0)
    player_irl_hit_per_9 = float(live_player.get('H9', 0) or 0)
    player_irl_pitching_clutch = float(live_player.get('Opp BA with RISP', 0) or 0)
    player_irl_stamina = float(live_player.get('IP Per Game', 0) or 0)
    
    threshold_k_per_9_set = False
    threshold_bb_per_9_set = False
    threshold_pitching_clutch_set = False
    threshold_hit_per_9_set = False
    threshold_stamina_set = False

    for threshold in thresholds:
      threshold_irl_stat = threshold.get('IRL Stat')
      threshold_irl_stat_range = float(threshold.get('IRL Stat Range'))
      threshold_irl_stat_threshold = float(threshold.get('IRL Stat Threshold'))
      threshold_in_game_stat = threshold.get('In Game Stat')
      threshold_in_game_range = int(threshold.get('In Game Range'))
      threshold_in_game_threshold = int(threshold.get('In Game Threshold'))

      if threshold_k_per_9_set == False and threshold_in_game_stat == 'K/9' and (player_k_per_9 <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_k_per_9 <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['K/9'] = {
          'in_game_upper': player_k_per_9 + threshold_in_game_threshold,
          'in_game_lower': player_k_per_9 - threshold_in_game_threshold
        }
        player_thresholds['K9'] = {
          'irl_upper': player_irl_k_per_9 + threshold_irl_stat_threshold,
          'irl_lower': player_irl_k_per_9 - threshold_irl_stat_threshold
        }
        threshold_k_per_9_set = True
      elif threshold_bb_per_9_set == False and threshold_in_game_stat == 'BB/9' and (player_bb_per_9 <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_bb_per_9 <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['BB/9'] = {
          'in_game_upper': player_bb_per_9 + threshold_in_game_threshold,
          'in_game_lower': player_bb_per_9 - threshold_in_game_threshold
        }
        player_thresholds['BB9'] = {
          'irl_upper': player_irl_bb_per_9 + threshold_irl_stat_threshold,
          'irl_lower': player_irl_bb_per_9 - threshold_irl_stat_threshold
        }
        threshold_bb_per_9_set = True
      elif threshold_pitching_clutch_set == False and threshold_in_game_stat == 'Pitching Clutch' and (player_pitching_clutch <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_pitching_clutch <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['Pitching Clutch'] = {
          'in_game_upper': player_pitching_clutch + threshold_in_game_threshold,
          'in_game_lower': player_pitching_clutch - threshold_in_game_threshold
        }
        player_thresholds['Opp BA with RISP'] = {
          'irl_upper': player_irl_pitching_clutch + threshold_irl_stat_threshold,
          'irl_lower': player_irl_pitching_clutch - threshold_irl_stat_threshold
        }
        threshold_pitching_clutch_set = True
      elif threshold_hit_per_9_set == False and threshold_in_game_stat == 'Hit Per 9' and (player_hit_per_9 <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_hit_per_9 <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['Hit/9'] = {
          'in_game_upper': player_hit_per_9 + threshold_in_game_threshold,
          'in_game_lower': player_hit_per_9 - threshold_in_game_threshold
        }
        player_thresholds['H9'] = {
          'irl_upper': player_irl_hit_per_9 + threshold_irl_stat_threshold,
          'irl_lower': player_irl_hit_per_9 - threshold_irl_stat_threshold
        }
        threshold_hit_per_9_set = True
      elif threshold_stamina_set == False and threshold_in_game_stat == 'Stamina' and (player_stamina <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_stamina <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['Stamina'] = {
          'in_game_upper': player_stamina + threshold_in_game_threshold,
          'in_game_lower': player_stamina - threshold_in_game_threshold
        }
        player_thresholds['IP Per Game'] = {
          'irl_upper': player_irl_stamina + threshold_irl_stat_threshold,
          'irl_lower': player_irl_stamina - threshold_irl_stat_threshold
        }
        threshold_stamina_set = True
  else:
    player_con_l = int(live_player.get('Contact Left'))
    player_con_r = int(live_player.get('Contact Right'))
    player_batting_clutch = int(live_player.get('Batting Clutch'))
    player_power_l = int(live_player.get('Power Left'))
    player_power_r = int(live_player.get('Power Right'))

    player_ba_v_left = float(live_player.get('BA vs Left', 0) or 0)
    player_ba_v_right = float(live_player.get('BA vs Right', 0) or 0)
    player_ba_w_risp = float(live_player.get('BA with RISP', 0) or 0)
    player_hrs_v_left = float(live_player.get('HR v Left normalized', 0) or 0)
    player_hrs_v_right = float(live_player.get('HR v Right normalized', 0) or 0)
    
    threshold_con_l_set = False
    threshold_con_r_set = False
    threshold_batting_clutch_set = False
    threshold_ba_v_left_set = False
    threshold_ba_v_right_set = False

    for threshold in thresholds:
      threshold_irl_stat = threshold.get('IRL Stat')
      threshold_irl_stat_range = float(threshold.get('IRL Stat Range'))
      threshold_irl_stat_threshold = float(threshold.get('IRL Stat Threshold'))
      threshold_in_game_stat = threshold.get('In Game Stat')
      threshold_in_game_range = int(threshold.get('In Game Range'))
      threshold_in_game_threshold = int(threshold.get('In Game Threshold'))

      if threshold_con_l_set == False and threshold_in_game_stat == 'Con L' and (player_con_l <= threshold_in_game_range or threshold_in_game_range == 0) and (player_ba_v_left <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        # print('Con L and BA vs Left thresholds')
        # print(threshold_in_game_threshold, threshold_irl_stat_threshold)
        player_thresholds['Con L'] = {
          'in_game_upper': player_con_l + threshold_in_game_threshold,
          'in_game_lower': player_con_l - threshold_in_game_threshold
        }
        player_thresholds['BA vs Left'] = {
          'irl_upper': player_ba_v_left + threshold_irl_stat_threshold,
          'irl_lower': player_ba_v_left - threshold_irl_stat_threshold
        }
        threshold_con_l_set = True
      elif threshold_con_r_set == False and threshold_in_game_stat == 'Con R' and (player_con_r <= threshold_in_game_range or threshold_in_game_range == 0) and (player_ba_v_right <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        # print('Con R and BA vs Right thresholds')
        # print(threshold_in_game_threshold, threshold_irl_stat_threshold)
        player_thresholds['Con R'] = {
          'in_game_upper': player_con_r + threshold_in_game_threshold,
          'in_game_lower': player_con_r - threshold_in_game_threshold
        }
        player_thresholds['BA vs Right'] = {
          'irl_upper': player_ba_v_right + threshold_irl_stat_threshold,
          'irl_lower': player_ba_v_right - threshold_irl_stat_threshold
        }
        threshold_con_r_set = True
      elif threshold_batting_clutch_set == False and threshold_in_game_stat == 'Batting Clutch' and (player_batting_clutch <= threshold_in_game_range or threshold_in_game_range == 0) and (player_ba_w_risp <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        # print('Batting Clutch and BA with RISP thresholds')
        # print(threshold_in_game_threshold, threshold_irl_stat_threshold)
        player_thresholds['Batting Clutch'] = {
          'in_game_upper': player_batting_clutch + threshold_in_game_threshold,
          'in_game_lower': player_batting_clutch - threshold_in_game_threshold
        }
        player_thresholds['BA with RISP'] = {
          'irl_upper': player_ba_w_risp + threshold_irl_stat_threshold,
          'irl_lower': player_ba_w_risp - threshold_irl_stat_threshold
        }
        threshold_batting_clutch_set = True
      elif threshold_ba_v_left_set == False and threshold_in_game_stat == 'Pow L' and (player_power_l <= threshold_in_game_range or threshold_in_game_range == 0) and (player_hrs_v_left <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        # print('POW L and HR v Left normalized thresholds')
        # print(threshold_in_game_threshold, threshold_irl_stat_threshold)
        player_thresholds['Power L'] = {
          'in_game_upper': player_power_l + threshold_in_game_threshold,
          'in_game_lower': player_power_l - threshold_in_game_threshold
        }
        player_thresholds['HR v Left normalized'] = {
          'irl_upper': player_hrs_v_left + threshold_irl_stat_threshold,
          'irl_lower': player_hrs_v_left - threshold_irl_stat_threshold
        }
        threshold_ba_v_left_set = True
      elif threshold_ba_v_right_set == False and threshold_in_game_stat == 'Pow R' and (player_power_r <= threshold_in_game_range or threshold_in_game_range == 0) and (player_hrs_v_right <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        # print('POW R and HR v Right normalized thresholds')
        # print(threshold_in_game_threshold, threshold_irl_stat_threshold)
        player_thresholds['Power R'] = {
          'in_game_upper': player_power_r + threshold_in_game_threshold,
          'in_game_lower': player_power_r - threshold_in_game_threshold
        }
        player_thresholds['HR v Right normalized'] = {
          'irl_upper': player_hrs_v_right + threshold_irl_stat_threshold,
          'irl_lower': player_hrs_v_right - threshold_irl_stat_threshold
        }
        threshold_ba_v_right_set = True
  # Attach the thresholds to the player dictionary
  live_player['thresholds'] = player_thresholds
  # print(live_player)
  # time.sleep(10000)
  players_w_thresholds.append(live_player)
  # print(players_w_thresholds)
  
# Search through the historical_hitters data for matches based on the thresholds

predicted_players = []

# print('Getting Historical Matches now')

for player in players_w_thresholds:
  
  # print(f"Processing player: {player['Name']}")

  if player['Name'] == "Shohei Ohtani":
    player_position = "P/DH"
  else:
    player_position = player.get('Position')
  
  player_thresholds = player.get('thresholds', {})
  
  power_r_collector = []
  power_l_collector = []
  contact_r_collector = []
  contact_l_collector = []
  batting_clutch_collector = []
  
  k_per_9_collector = []
  bb_per_9_collector = []
  hit_per_9_collector = []
  pitching_clutch_collector = []
  stamina_collector = []

  if player_position in ("SP", "RP", "CP", "P/DH"):
    # print(player)
    # time.sleep(1000)
    for entry in historical_pitchers:
      # print(entry)
      # time.sleep(1000)
      hist_entry_name = entry.get('Player')
      hist_entry_date = entry.get('Date')
      hist_entry_k_per_9_before = int(entry.get('K9 Before') or 0)
      hist_entry_bb_per_9_before = int(entry.get('BB9 Before') or 0)
      hist_entry_hit_per_9_before = int(entry.get('H9 Before') or 0)
      hist_entry_pitching_clutch_before = int(entry.get('PCLT Before') or 0)
      hist_entry_stamina_before = int(entry.get('STA Before') or 0)
      
      if (player_thresholds.get('K/9', {}).get('in_game_lower', 0) <= hist_entry_k_per_9_before <= player_thresholds.get('K/9', {}).get('in_game_upper', 0) and player_thresholds.get('K9', {}).get('irl_lower', 0) <= float(entry.get('K9 IRL', 0) or 0) <= player_thresholds.get('K9', {}).get('irl_upper', 0)):
        k9_change_val = entry.get('K9 Change', 0)
        try:
          k_per_9_collector.append(int(k9_change_val) if k9_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          k_per_9_collector.append(0)
      if (player_thresholds.get('BB/9', {}).get('in_game_lower', 0) <= hist_entry_bb_per_9_before <= player_thresholds.get('BB/9', {}).get('in_game_upper', 0) and player_thresholds.get('BB9', {}).get('irl_lower', 0) <= float(entry.get('BB9 IRL', 0) or 0) <= player_thresholds.get('BB9', {}).get('irl_upper', 0)):
        bb9_change_val = entry.get('BB9 Change', 0)
        try:
          bb_per_9_collector.append(int(bb9_change_val) if bb9_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          bb_per_9_collector.append(0)
      if (player_thresholds.get('Hit/9', {}).get('in_game_lower', 0) <= hist_entry_hit_per_9_before <= player_thresholds.get('Hit/9', {}).get('in_game_upper', 0) and player_thresholds.get('H9', {}).get('irl_lower', 0) <= float(entry.get('H9 IRL', 0) or 0) <= player_thresholds.get('H9', {}).get('irl_upper', 0)):
        hit9_change_val = entry.get('H9 Change', 0)
        try:
          hit_per_9_collector.append(int(hit9_change_val) if hit9_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          hit_per_9_collector.append(0)
      if (player_thresholds.get('Pitching Clutch', {}).get('in_game_lower', 0) <= hist_entry_pitching_clutch_before <= player_thresholds.get('Pitching Clutch', {}).get('in_game_upper', 0) and player_thresholds.get('Opp BA with RISP', {}).get('irl_lower', 0) <= float(entry.get('OPP BA W RISP IRL', 0) or 0) <= player_thresholds.get('Opp BA with RISP', {}).get('irl_upper', 0)):
        pclt_change_val = entry.get('PCLT Change', 0)
        try:
          pitching_clutch_collector.append(int(pclt_change_val) if pclt_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          pitching_clutch_collector.append(0)
      if (player_thresholds.get('Stamina', {}).get('in_game_lower', 0) <= hist_entry_stamina_before <= player_thresholds.get('Stamina', {}).get('in_game_upper', 0) and player_thresholds.get('IP Per Game', {}).get('irl_lower', 0) <= float(entry.get('InningsGame IRL', 0) or 0) <= player_thresholds.get('IP Per Game', {}).get('irl_upper', 0)):
        sta_change_val = entry.get('STA Change', 0)
        try:
          stamina_collector.append(int(sta_change_val) if sta_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          stamina_collector.append(0)
    
    # print(f"K/9 Collector: {k_per_9_collector}")
    # print(f"BB/9 Collector: {bb_per_9_collector}")
    # print(f"Hit/9 Collector: {hit_per_9_collector}")
    # print(f"Pitching Clutch Collector: {pitching_clutch_collector}")
    # print(f"Stamina Collector: {stamina_collector}")
    
    k_per_9_change_avg = round(sum(k_per_9_collector) / len(k_per_9_collector)) if k_per_9_collector else 0
    bb_per_9_change_avg = round(sum(bb_per_9_collector) / len(bb_per_9_collector)) if bb_per_9_collector else 0
    hit_per_9_change_avg = round(sum(hit_per_9_collector) / len(hit_per_9_collector)) if hit_per_9_collector else 0
    pitching_clutch_change_avg = round(sum(pitching_clutch_collector) / len(pitching_clutch_collector)) if pitching_clutch_collector else 0
    stamina_change_avg = round(sum(stamina_collector) / len(stamina_collector)) if stamina_collector else 0
    
    # print(f"K/9 Change Avg: {k_per_9_change_avg}")
    # print(f"BB/9 Change Avg: {bb_per_9_change_avg}")
    # print(f"Hit/9 Change Avg: {hit_per_9_change_avg}")
    # print(f"Pitching Clutch Change Avg: {pitching_clutch_change_avg}")
    # print(f"Stamina Change Avg: {stamina_change_avg}")
    
    player['K/9 Change Avg'] = k_per_9_change_avg
    player['BB/9 Change Avg'] = bb_per_9_change_avg
    player['Hit/9 Change Avg'] = hit_per_9_change_avg
    player['Pitching Clutch Change Avg'] = pitching_clutch_change_avg
    player['Stamina Change Avg'] = stamina_change_avg
    predicted_players.append(player)

  else:
    for entry in historical_hitters:
      
      hist_entry_name = entry.get('Player')
      hist_entry_date = entry.get('Date')
      hist_entry_pow_r_before = int(entry.get('POW R Before') or 0)
      hist_entry_pow_l_before = int(entry.get('POW L Before') or 0)
      hist_entry_con_r_before = int(entry.get('CON R Before') or 0)
      hist_entry_con_l_before = int(entry.get('CON L Before') or 0)
      hist_entry_batting_clutch = int(entry.get('CLT Before') or 0)
      
      if (player_thresholds.get('Power R', {}).get('in_game_lower', 0) <= hist_entry_pow_r_before <= player_thresholds.get('Power R', {}).get('in_game_upper', 0) and player_thresholds.get('HR v Right normalized', {}).get('irl_lower', 0) <= float(entry.get('HR per AB vs Right IRL', 0) or 0) <= player_thresholds.get('HR v Right normalized', {}).get('irl_upper', 0)):
        # print(entry)
        pow_r_change_val = entry.get('POW R Change', 0)
        try:
          power_r_collector.append(int(pow_r_change_val) if pow_r_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          power_r_collector.append(0)
      if (player_thresholds.get('Power L', {}).get('in_game_lower', 0) <= hist_entry_pow_l_before <= player_thresholds.get('Power L', {}).get('in_game_upper', 0) and player_thresholds.get('HR v Left normalized', {}).get('irl_lower', 0) <= float(entry.get('HR per AB vs Left IRL', 0) or 0) <= player_thresholds.get('HR v Left normalized', {}).get('irl_upper', 0)):
        pow_l_change_val = entry.get('POW L Change', 0)
        try:
          power_l_collector.append(int(pow_l_change_val) if pow_l_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          power_l_collector.append(0)
      if (player_thresholds.get('Con R', {}).get('in_game_lower', 0) <= hist_entry_con_r_before <= player_thresholds.get('Con R', {}).get('in_game_upper', 0) and player_thresholds.get('BA vs Right', {}).get('irl_lower', 0) <= float(entry.get('BA vs Right IRL', 0) or 0) <= player_thresholds.get('BA vs Right', {}).get('irl_upper', 0)):
        con_r_change_val = entry.get('CON R Change', 0)
        try:
          contact_r_collector.append(int(con_r_change_val) if con_r_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          contact_r_collector.append(0)
      if (player_thresholds.get('Con L', {}).get('in_game_lower', 0) <= hist_entry_con_l_before <= player_thresholds.get('Con L', {}).get('in_game_upper', 0) and player_thresholds.get('BA vs Left', {}).get('irl_lower', 0) <= float(entry.get('BA vs Left IRL', 0) or 0) <= player_thresholds.get('BA vs Left', {}).get('irl_upper', 0)):
        con_l_change_val = entry.get('CON L Change', 0)
        try:
          contact_l_collector.append(int(con_l_change_val) if con_l_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          contact_l_collector.append(0)
      if (player_thresholds.get('Batting Clutch', {}).get('in_game_lower', 0) <= hist_entry_batting_clutch <= player_thresholds.get('Batting Clutch', {}).get('in_game_upper', 0) and player_thresholds.get('BA with RISP', {}).get('irl_lower', 0) <= float(entry.get('BA with RISP IRL', 0) or 0) <= player_thresholds.get('BA with RISP', {}).get('irl_upper', 0)):
        batting_clutch_change_val = entry.get('CLT Change', 0)
        try:
          batting_clutch_collector.append(int(batting_clutch_change_val) if batting_clutch_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          batting_clutch_collector.append(0)
    
    # print(f"Power R Collector: {power_r_collector}")
    # print(f"Power L Collector: {power_l_collector}")
    # print(f"Contact R Collector: {contact_r_collector}")
    # print(f"Contact L Collector: {contact_l_collector}")
    # print(f"Batting Clutch Collector: {batting_clutch_collector}")
    
    power_r_change_avg = round(sum(power_r_collector) / len(power_r_collector)) if power_r_collector else 0
    power_l_change_avg = round(sum(power_l_collector) / len(power_l_collector)) if power_l_collector else 0
    contact_r_change_avg = round(sum(contact_r_collector) / len(contact_r_collector)) if contact_r_collector else 0
    contact_l_change_avg = round(sum(contact_l_collector) / len(contact_l_collector)) if contact_l_collector else 0
    batting_clutch_change_avg = round(sum(batting_clutch_collector) / len(batting_clutch_collector)) if batting_clutch_collector else 0
    
    # print(f"Power R Change Avg: {power_r_change_avg}")
    # print(f"Power L Change Avg: {power_l_change_avg}")
    # print(f"Contact R Change Avg: {contact_r_change_avg}")
    # print(f"Contact L Change Avg: {contact_l_change_avg}")
    # print(f"Batting Clutch Change Avg: {batting_clutch_change_avg}")
    
    player['Power R Change Avg'] = power_r_change_avg
    player['Power L Change Avg'] = power_l_change_avg
    player['Contact R Change Avg'] = contact_r_change_avg
    player['Contact L Change Avg'] = contact_l_change_avg
    player['Batting Clutch Change Avg'] = batting_clutch_change_avg
    predicted_players.append(player)
    
# print(predicted_players)

## Get the True Overall Change for each player

audit_sheet_output = []
calculation_sheet_output = []

print("Calculating True Overall Changes now")
# print(predicted_players[0])
# time.sleep(1000)
for player in predicted_players:
  print(f"Calculating True Overall for player: {player['Name']}")
  player_before_stats = {
      "display_position": player.get('Position'),
      "stamina": int(player.get('Stamina')),
      "pitching_clutch": int(player.get('Pitching Clutch')),
      "hits_per_bf": int(player.get('Hit Per 9')),
      "k_per_bf": int(player.get('Ks Per 9')),
      "bb_per_bf": int(player.get('BB Per 9')),
      "hr_per_bf": player.get('HR Per 9'),
      "pitch_control": player.get('Pitch Control'),
      "pitch_velocity": player.get('Pitch Velocity'),
      "pitch_movement": player.get('Pitch Movement'),
      "pitching_durability": player.get('Durability'),
      "contact_right": int(player.get('Contact Right')),
      "contact_left": int(player.get('Contact Left')),
      "power_right": int(player.get('Power Right')),
      "power_left": int(player.get('Power Left')),
      "plate_vision": player.get('Plate Vision'),
      "plate_discipline": player.get('Plate Discipline'),
      "batting_clutch": int(player.get('Batting Clutch')),
      "bunting_ability": player.get('Bunting Ability'),
      "drag_bunting_ability": player.get('Drag Bunting'),
      "hitting_durability": player.get('Hitting Durability'),
      "fielding_ability": player.get('Fielding'),
      "arm_strength": player.get('Arm Strength'),
      "arm_accuracy": player.get('Arm Accuracy'),
      "reaction_time": player.get('Reaction Time'),
      "blocking": player.get('Blocking'),
      "speed": player.get('Speed'),
      "baserunning_ability": player.get('Baserunning'),
      "baserunning_aggression": player.get('Baserunning Aggro')
    }

  
  # print(player_before_stats)
  
  player_after_stats = {
      "display_position": player.get('Position'),
      "stamina": int(player.get('Stamina')) + player.get('Stamina Change Avg', 0),
      "pitching_clutch": int(player.get('Pitching Clutch')) + player.get('Pitching Clutch Change Avg', 0),
      "hits_per_bf": int(player.get('Hit Per 9')) + player.get('Hit/9 Change Avg', 0),
      "k_per_bf": int(player.get('Ks Per 9')) + player.get('K/9 Change Avg', 0),
      "bb_per_bf": int(player.get('BB Per 9')) + player.get('BB/9 Change Avg', 0),
      "hr_per_bf": player.get('HR Per 9'),
      "pitch_control": player.get('Pitch Control'),
      "pitch_velocity": player.get('Pitch Velocity'),
      "pitch_movement": player.get('Pitch Movement'),
      "pitching_durability": player.get('Durability'),
      "contact_right": int(player.get('Contact Right')) + player.get('Contact R Change Avg', 0),
      "contact_left": int(player.get('Contact Left')) + player.get('Contact L Change Avg', 0),
      "power_right": int(player.get('Power Right')) + player.get('Power R Change Avg', 0),
      "power_left": int(player.get('Power Left')) + player.get('Power L Change Avg', 0),
      "plate_vision": player.get('Plate Vision'),
      "plate_discipline": player.get('Plate Discipline'),
      "batting_clutch": int(player.get('Batting Clutch')) + player.get('Batting Clutch Change Avg', 0),
      "bunting_ability": player.get('Bunting Ability'),
      "drag_bunting_ability": player.get('Drag Bunting'),
      "hitting_durability": player.get('Hitting Durability'),
      "fielding_ability": player.get('Fielding'),
      "arm_strength": player.get('Arm Strength'),
      "arm_accuracy": player.get('Arm Accuracy'),
      "reaction_time": player.get('Reaction Time'),
      "blocking": player.get('Blocking'),
      "speed": player.get('Speed'),
      "baserunning_ability": player.get('Baserunning'),
      "baserunning_aggression": player.get('Baserunning Aggro')
    }
  
  # print(player_after_stats)
  
  response1 = requests.post('https://api.showzone.gg/api/generate-true-overall', json=player_before_stats)
  response2 = requests.post('https://api.showzone.gg/api/generate-true-overall', json=player_after_stats)
  
  old_true_overall = float(response1.json().get('True Overall Rating', 0))
  new_true_overall = float(response2.json().get('True Overall Rating', 0))
  
  # print(f"Old True Overall: {old_true_overall}, New True Overall: {new_true_overall}")
  
  overall_change_float = new_true_overall - old_true_overall
  overall_change_final = round(overall_change_float, 2)
  
  # print(overall_change_float, overall_change_final)
  
  player['Overall Change'] = overall_change_final
  player['Before Stats'] = player_before_stats
  player['After Stats'] = player_after_stats
  player['Old True Overall'] = old_true_overall
  player['New True Overall'] = new_true_overall
  audit_sheet_output.append(player)
  
  calculation_sheet_output.append({
      'Player': player.get('Name'),
      'Position': player.get('Position'),
      'Current Stats': {
          'Stamina': player.get('Stamina'),
          'Pitching Clutch': player.get('Pitching Clutch'),
          'H/9': player.get('Hit Per 9'),
          'K/9': player.get('Ks Per 9'),
          'BB/9': player.get('BB Per 9'),
          'Con R': player.get('Contact Right'),
          'Con L': player.get('Contact Left'),
          'Pow R': player.get('Power Right'),
          'Pow L': player.get('Power Left'),
          'Batting Clutch': player.get('Batting Clutch'),
          'Overall': player.get('OVR')
        },
      'Predicted Changes': {
          'Stamina': int(player.get('Stamina')) + player.get('Stamina Change Avg', 0),
          'Pitching Clutch': int(player.get('Pitching Clutch')) + player.get('Pitching Clutch Change Avg', 0),
          'H/9': int(player.get('Hit Per 9')) + player.get('Hit/9 Change Avg', 0),
          'K/9': int(player.get('Ks Per 9')) + player.get('K/9 Change Avg', 0),
          'BB/9': int(player.get('BB Per 9')) + player.get('BB/9 Change Avg', 0),
          'Con R': int(player.get('Contact Right')) + player.get('Contact R Change Avg', 0),
          'Con L': int(player.get('Contact Left')) + player.get('Contact L Change Avg', 0),
          'Pow R': int(player.get('Power Right')) + player.get('Power R Change Avg', 0),
          'Pow L': int(player.get('Power Left')) + player.get('Power L Change Avg', 0),
          'Batting Clutch': int(player.get('Batting Clutch')) + player.get('Batting Clutch Change Avg', 0),
          'Overall': round(int(player.get('OVR')) + overall_change_final)
        },
      'Change': {
          'Stamina Change': player.get('Stamina Change Avg', 0),
          'Pitching Clutch Change': player.get('Pitching Clutch Change Avg', 0),
          'H/9 Change': player.get('Hit/9 Change Avg', 0),
          'K/9 Change': player.get('K/9 Change Avg', 0),
          'BB/9 Change': player.get('BB/9 Change Avg', 0),
          'Con R Change': player.get('Contact R Change Avg', 0),
          'Con L Change': player.get('Contact L Change Avg', 0),
          'Pow R Change': player.get('Power R Change Avg', 0),
          'Pow L Change': player.get('Power L Change Avg', 0),
          'Batting Clutch Change': player.get('Batting Clutch Change Avg', 0),
          'Overall Change': overall_change_final
      }
  })
  
  # print(calculation_sheet_output)
  
## Print the results to Calculations Sheet and Audit Sheet

# Define the header order
header_order = [
  'Player', 'Position', 'Stamina', 'Pitching Clutch', 'H/9', 'K/9', 'BB/9',
  'Con R', 'Con L', 'Pow R', 'Pow L', 'Batting Clutch', 'Overall'
]

rows_to_write = []

print('Writing to sheet now')

for entry in calculation_sheet_output:
  # First line: Player, Position, Current Stats
  current_stats = entry['Current Stats']
  row1 = [
    "Current Stats",
    entry['Player'],
    entry['Position'],
    int(current_stats.get('Stamina', 0) or 0),
    int(current_stats.get('Pitching Clutch', 0) or 0),
    int(current_stats.get('H/9', 0) or 0),
    int(current_stats.get('K/9', 0) or 0),
    int(current_stats.get('BB/9', 0) or 0),
    int(current_stats.get('Con R', 0) or 0),
    int(current_stats.get('Con L', 0) or 0),
    int(current_stats.get('Pow R', 0) or 0),
    int(current_stats.get('Pow L', 0) or 0),
    int(current_stats.get('Batting Clutch', 0) or 0),
    int(current_stats.get('Overall', 0) or 0)
  ]
  # Second line: blank Player/Position, Predicted Stats
  predicted_stats = entry['Predicted Changes']
  row2 = [
    "Predicted Stats",
    '', '',
    predicted_stats.get('Stamina', ''),
    predicted_stats.get('Pitching Clutch', ''),
    predicted_stats.get('H/9', ''),
    predicted_stats.get('K/9', ''),
    predicted_stats.get('BB/9', ''),
    predicted_stats.get('Con R', ''),
    predicted_stats.get('Con L', ''),
    predicted_stats.get('Pow R', ''),
    predicted_stats.get('Pow L', ''),
    predicted_stats.get('Batting Clutch', ''),
    predicted_stats.get('Overall', '')
  ]
  # Third line: blank Player/Position, Change
  change_stats = entry['Change']
  row3 = [
    "Change",
    '', '',
    change_stats.get('Stamina Change', ''),
    change_stats.get('Pitching Clutch Change', ''),
    change_stats.get('H/9 Change', ''),
    change_stats.get('K/9 Change', ''),
    change_stats.get('BB/9 Change', ''),
    change_stats.get('Con R Change', ''),
    change_stats.get('Con L Change', ''),
    change_stats.get('Pow R Change', ''),
    change_stats.get('Pow L Change', ''),
    change_stats.get('Batting Clutch Change', ''),
    change_stats.get('Overall Change', '')
  ]
  rows_to_write.extend([row1, row2, row3])

cell_list = f"A2:N{len(rows_to_write)+1}"
calculation_sheet.update(cell_list, rows_to_write)

now = datetime.datetime.now()
est = pytz.timezone('US/Eastern')
now_est = now.astimezone(est)

short_date = now_est.strftime("%m/%d/%y")
current_time = now_est.strftime("%I:%M %p")

calculation_sheet.update_acell('A1', "Updated: " + short_date + " " + current_time + " EST")

print("--- %s seconds ---" % (time.time() - start_time)) 
