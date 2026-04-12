import requests
import random
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

def normalize_name(name):
    if not name:
      return ''
    # Remove accents, punctuation, suffixes, and middle initials, lower case
    name = unidecode(str(name))
    name = re.sub(r'[^A-Za-z0-9 ]+', '', name)
    name = re.sub(r'\bJr\.?\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+', ' ', name).strip()
    # Remove middle initials (e.g., "Elly D. La Cruz" -> "Elly La Cruz")
    parts = name.split()
    if len(parts) > 2:
      name = f"{parts[0]} {parts[-1]}"
    name = name.lower()
    return name

start_time = time.time()

creds_json = os.environ['CREDS']
CREDS = json.loads(creds_json)

gc = gspread.service_account_from_dict(CREDS)

live_sheet = gc.open("Roster Update Prediction Bot")
current_in_game_stats_sheet = live_sheet.worksheet("Current_In_Game_Stats") ## Driver sheets for current calculations
current_day_irl_stats_sheet = live_sheet.worksheet("Current_IRL_Stats_Fangraphs")


history_sheet = gc.open("Historical RU Data Backup")
historical_ru_data_sheet = history_sheet.worksheet("Historical_RU_Data")
historical_irl_stats_hitters_sheet = history_sheet.worksheet("Historical_IRL_Stats_Hitters")
historical_irl_stats_pitchers_sheet = history_sheet.worksheet("Historical_IRL_Stats_Pitchers")

thresholds_sheet = live_sheet.worksheet("Thresholds")
calculation_sheet = live_sheet.worksheet("Calculations")
website_output_sheet = live_sheet.worksheet("Website Output")

headers = [re.sub(r'[^A-Za-z0-9 ]+', '', unidecode(h)) for h in current_in_game_stats_sheet.get("B1:AM1")[0]]
rows = current_in_game_stats_sheet.get("B2:AM")
original_names = [row[0] for row in rows]  # Assuming column B is index 0
cleaned_rows = [clean_row(row, headers) for row in rows]
current_in_game_stats = []
for cleaned, original in zip(cleaned_rows, original_names):
  player_dict = dict(zip(headers, cleaned))
  player_dict['Original_Name'] = original
  player_dict['In_Game_Position'] = player_dict.get('Position')
  current_in_game_stats.append(player_dict)

# Get all values from the Current_Day_IRL_Stats sheet in cols B to AD and save it to a list of dictionaries with the first row as the keys

headers_irl = [re.sub(r'[^A-Za-z0-9 ]+', '', unidecode(h)) for h in current_day_irl_stats_sheet.get("B1:X1")[0]]
# print(headers_irl)
rows_irl = current_day_irl_stats_sheet.get("B2:X")
# Pad each row to the length of headers_irl
rows_irl_padded = [row + [''] * (len(headers_irl) - len(row)) if len(row) < len(headers_irl) else row[:len(headers_irl)] for row in rows_irl]
cleaned_rows_irl = [clean_row(row, headers_irl) for row in rows_irl_padded]
current_day_irl_stats = [dict(zip(headers_irl, row)) for row in cleaned_rows_irl]

# print(current_day_irl_stats[0])
# time.sleep(100)

# loop through current_in_game_stats and find the player match with the value in current_day_irl_stats
# when you find a match combine the 2 lists entries and append it to a new list of dictionaries called current_players

current_players = []
no_match_current_players = []

print('Matching players now')

for in_game_player in current_in_game_stats:
  in_game_name_norm = normalize_name(in_game_player.get('Name'))
  # Try to match with normalized names
  match = next(
    (
      irl_player for irl_player in current_day_irl_stats
      if normalize_name(irl_player.get('OriginalMLBTheShowName')) == in_game_name_norm
    ),
    None
  )
  if not match:
    # Try matching with Original_Name if available
    in_game_orig_name_norm = normalize_name(in_game_player.get('Original_Name'))
    match = next(
      (
        irl_player for irl_player in current_day_irl_stats
        if normalize_name(irl_player.get('OriginalMLBTheShowName')) == in_game_orig_name_norm
      ),
      None
    )
  if match:
    combined = {**in_game_player, **match}
    current_players.append(combined)
  else:
    # print(f"No match found for player: {in_game_player.get('Name')} (Original: {in_game_player.get('Original_Name')})")
    no_match_current_players.append(in_game_player)

# Find IRL players that weren't matched using normalized names
matched_irl_names = set()
in_game_names_norm = set()
for p in current_in_game_stats:
  in_game_names_norm.add(normalize_name(p.get('Name')))
  in_game_names_norm.add(normalize_name(p.get('Original_Name')))
for player in current_day_irl_stats:
  irl_name_norm = normalize_name(player.get('OriginalMLBTheShowName'))
  if irl_name_norm in in_game_names_norm:
    matched_irl_names.add(player.get('OriginalMLBTheShowName'))
unmatched_irl_players = [player for player in current_day_irl_stats if player.get('OriginalMLBTheShowName') not in matched_irl_names]

print(f"\nUnmatched IRL players ({len(unmatched_irl_players)}):")
for player in unmatched_irl_players:
  print(f"  - {player.get('OriginalMLBTheShowName')}")
    
# print(len(current_players))
# print(len(no_match_current_players))
# time.sleep(100)

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

# $$$$$$$$$$$$$$$$$$ MAY NEED TO NORMALIZE NAMES $$$$$$$$$$$$$$$$$$
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

## START FIX HERE ON 3/29

for live_player in current_players:
  player_name = live_player.get('Name')
  
  if player_name == "Shohei Ohtani":
    player_position = "P/DH"
  else:
    player_position = live_player.get('Position')

  # Prepare a dict to store threshold values for this player
  player_thresholds = {}

  if player_position in ("SP", "RP", "CP", "P"):
    # player_k_per_9 = int(live_player.get('Ks Per 9'))
    
    # IN GAME STATS #
    player_k_per_9_v_l = int(live_player.get('K9 V L'))
    player_k_per_9_v_r = int(live_player.get('K9 V R'))
    player_bb_per_9 = int(live_player.get('BB Per 9'))
    # player_hit_per_9 = int(live_player.get('Hit Per 9'))
    player_hit_per_9_v_l = int(live_player.get('H9 V L'))
    player_hit_per_9_v_r = int(live_player.get('H9 V R'))
    player_pitching_clutch = int(live_player.get('Pitching Clutch'))
    player_stamina = int(live_player.get('Stamina'))
    
    # IRL STATS #
    player_irl_k_per_9_v_l = float(live_player.get('K9 vs Left', 0) or 0)
    player_irl_k_per_9_v_r = float(live_player.get('K9 vs Right', 0) or 0)
    player_irl_bb_per_9 = float(live_player.get('BB9', 0) or 0)
    player_irl_hit_per_9_v_l = float(live_player.get('H9 vs Left', 0) or 0)
    player_irl_hit_per_9_v_r = float(live_player.get('H9 vs Right', 0) or 0)
    player_irl_pitching_clutch = float(live_player.get('OPP BA W RISP', 0) or 0)
    player_irl_stamina = float(live_player.get('InningsGame', 0) or 0)
    
    threshold_k_per_9_v_l_set = False
    threshold_k_per_9_v_r_set = False
    threshold_bb_per_9_set = False
    threshold_pitching_clutch_set = False
    threshold_hit_per_9_v_l_set = False
    threshold_hit_per_9_v_r_set = False
    threshold_stamina_set = False

    for threshold in thresholds:
      threshold_irl_stat = threshold.get('IRL Stat')
      threshold_irl_stat_range = float(threshold.get('IRL Stat Range'))
      threshold_irl_stat_threshold = float(threshold.get('IRL Stat Threshold'))
      threshold_in_game_stat = threshold.get('In Game Stat')
      threshold_in_game_range = int(threshold.get('In Game Range'))
      threshold_in_game_threshold = int(threshold.get('In Game Threshold'))

      if threshold_k_per_9_v_l_set == False and threshold_in_game_stat == 'K/9 V L' and (player_k_per_9_v_l <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_k_per_9_v_l <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['K/9 v L'] = {
          'in_game_upper': player_k_per_9_v_l + threshold_in_game_threshold,
          'in_game_lower': player_k_per_9_v_l - threshold_in_game_threshold
        }
        player_thresholds['K9 v L'] = {
          'irl_upper': player_irl_k_per_9_v_l + threshold_irl_stat_threshold,
          'irl_lower': player_irl_k_per_9_v_l - threshold_irl_stat_threshold
        }
        threshold_k_per_9_v_l_set = True
      elif threshold_k_per_9_v_r_set == False and threshold_in_game_stat == 'K/9 V R' and (player_k_per_9_v_r <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_k_per_9_v_r <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['K/9 v R'] = {
          'in_game_upper': player_k_per_9_v_r + threshold_in_game_threshold,
          'in_game_lower': player_k_per_9_v_r - threshold_in_game_threshold
        }
        player_thresholds['K9 v R'] = {
          'irl_upper': player_irl_k_per_9_v_r + threshold_irl_stat_threshold,
          'irl_lower': player_irl_k_per_9_v_r - threshold_irl_stat_threshold
        }
        threshold_k_per_9_v_r_set = True
      elif threshold_bb_per_9_set == False and threshold_in_game_stat == 'BB Per 9' and (player_bb_per_9 <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_bb_per_9 <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
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
      elif threshold_hit_per_9_v_l_set == False and threshold_in_game_stat == 'H/9 V L' and (player_hit_per_9_v_l <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_hit_per_9_v_l <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['H/9 v L'] = {
          'in_game_upper': player_hit_per_9_v_l + threshold_in_game_threshold,
          'in_game_lower': player_hit_per_9_v_l - threshold_in_game_threshold
        }
        player_thresholds['H9 v L'] = {
          'irl_upper': player_irl_hit_per_9_v_l + threshold_irl_stat_threshold,
          'irl_lower': player_irl_hit_per_9_v_l - threshold_irl_stat_threshold
        }
        threshold_hit_per_9_v_l_set = True
      elif threshold_hit_per_9_v_r_set == False and threshold_in_game_stat == 'H/9 V R' and (player_hit_per_9_v_r <= threshold_in_game_range or threshold_in_game_range == 0) and (player_irl_hit_per_9_v_r <= threshold_irl_stat_range or threshold_irl_stat_range == 0):
        player_thresholds['H/9 v R'] = {
          'in_game_upper': player_hit_per_9_v_r + threshold_in_game_threshold,
          'in_game_lower': player_hit_per_9_v_r - threshold_in_game_threshold
        }
        player_thresholds['H9 v R'] = {
          'irl_upper': player_irl_hit_per_9_v_r + threshold_irl_stat_threshold,
          'irl_lower': player_irl_hit_per_9_v_r - threshold_irl_stat_threshold
        }
        threshold_hit_per_9_v_r_set = True
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
    player_hrs_v_left = float(live_player.get('HR per AB vs Left', 0) or 0)
    player_hrs_v_right = float(live_player.get('HR per AB vs Right', 0) or 0)
    
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
  # if player_name == "Tarik Skubal":
  #   print(live_player)
  #   time.sleep(10)
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
  
  k_per_9_v_l_collector = []
  k_per_9_v_r_collector = []
  bb_per_9_collector = []
  hit_per_9_v_l_collector = []
  hit_per_9_v_r_collector = []
  pitching_clutch_collector = []
  stamina_collector = []

  if player_position in ("SP", "RP", "CP", "P"):
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
      
      # Should be good
      
      if (player_thresholds.get('K/9 v L', {}).get('in_game_lower', 0) <= hist_entry_k_per_9_before <= player_thresholds.get('K/9 v L', {}).get('in_game_upper', 0) and player_thresholds.get('K9 v L', {}).get('irl_lower', 0) <= float(entry.get('K9 IRL', 0) or 0) <= player_thresholds.get('K9 v L', {}).get('irl_upper', 0)):
        k9_v_l_change_val = entry.get('K9 Change', 0)
        try:
          k_per_9_v_l_collector.append(int(k9_v_l_change_val) if k9_v_l_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          k_per_9_v_l_collector.append(0)
        # print(f"Processed K/9 v L for {hist_entry_name} on {hist_entry_date}: {k9_v_l_change_val}")
          
      if (player_thresholds.get('K/9 v R', {}).get('in_game_lower', 0) <= hist_entry_k_per_9_before <= player_thresholds.get('K/9 v R', {}).get('in_game_upper', 0) and player_thresholds.get('K9 v R', {}).get('irl_lower', 0) <= float(entry.get('K9 IRL', 0) or 0) <= player_thresholds.get('K9 v R', {}).get('irl_upper', 0)):
        k9_v_r_change_val = entry.get('K9 Change', 0)
        try:
          k_per_9_v_r_collector.append(int(k9_v_r_change_val) if k9_v_r_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          k_per_9_v_r_collector.append(0)
        # print(f"Processed K/9 v R for {hist_entry_name} on {hist_entry_date}: {k9_v_r_change_val}")
      if (player_thresholds.get('BB/9', {}).get('in_game_lower', 0) <= hist_entry_bb_per_9_before <= player_thresholds.get('BB/9', {}).get('in_game_upper', 0) and player_thresholds.get('BB9', {}).get('irl_lower', 0) <= float(entry.get('BB9 IRL', 0) or 0) <= player_thresholds.get('BB9', {}).get('irl_upper', 0)):
        bb9_change_val = entry.get('BB9 Change', 0)
        try:
          bb_per_9_collector.append(int(bb9_change_val) if bb9_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          bb_per_9_collector.append(0)
        # print(f"Processed BB/9 for {hist_entry_name} on {hist_entry_date}: {bb9_change_val}")
      if (player_thresholds.get('H/9 v L', {}).get('in_game_lower', 0) <= hist_entry_hit_per_9_before <= player_thresholds.get('H/9 v L', {}).get('in_game_upper', 0) and player_thresholds.get('H9 v L', {}).get('irl_lower', 0) <= float(entry.get('H9 IRL', 0) or 0) <= player_thresholds.get('H9 v L', {}).get('irl_upper', 0)):
        hit9_v_l_change_val = entry.get('H9 Change', 0)
        try:
          hit_per_9_v_l_collector.append(int(hit9_v_l_change_val) if hit9_v_l_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          hit_per_9_v_l_collector.append(0)
        # print(f"Processed H/9 v L for {hist_entry_name} on {hist_entry_date}: {hit9_v_l_change_val}")
      if (player_thresholds.get('H/9 v R', {}).get('in_game_lower', 0) <= hist_entry_hit_per_9_before <= player_thresholds.get('H/9 v R', {}).get('in_game_upper', 0) and player_thresholds.get('H9 v R', {}).get('irl_lower', 0) <= float(entry.get('H9 IRL', 0) or 0) <= player_thresholds.get('H9 v R', {}).get('irl_upper', 0)):
        hit9_v_r_change_val = entry.get('H9 Change', 0)
        try:
          hit_per_9_v_r_collector.append(int(hit9_v_r_change_val) if hit9_v_r_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          hit_per_9_v_r_collector.append(0)
        # print(f"Processed H/9 v R for {hist_entry_name} on {hist_entry_date}: {hit9_v_r_change_val}")
      if (player_thresholds.get('Pitching Clutch', {}).get('in_game_lower', 0) <= hist_entry_pitching_clutch_before <= player_thresholds.get('Pitching Clutch', {}).get('in_game_upper', 0) and player_thresholds.get('Opp BA with RISP', {}).get('irl_lower', 0) <= float(entry.get('OPP BA W RISP IRL', 0) or 0) <= player_thresholds.get('Opp BA with RISP', {}).get('irl_upper', 0)):
        pclt_change_val = entry.get('PCLT Change', 0)
        try:
          pitching_clutch_collector.append(int(pclt_change_val) if pclt_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          pitching_clutch_collector.append(0)
        # print(f"Processed Pitching Clutch for {hist_entry_name} on {hist_entry_date}: {pclt_change_val}")
      if (player_thresholds.get('Stamina', {}).get('in_game_lower', 0) <= hist_entry_stamina_before <= player_thresholds.get('Stamina', {}).get('in_game_upper', 0) and player_thresholds.get('IP Per Game', {}).get('irl_lower', 0) <= float(entry.get('InningsGame IRL', 0) or 0) <= player_thresholds.get('IP Per Game', {}).get('irl_upper', 0)):
        sta_change_val = entry.get('STA Change', 0)
        try:
          stamina_collector.append(int(sta_change_val) if sta_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          stamina_collector.append(0)
        # print(f"Processed Stamina for {hist_entry_name} on {hist_entry_date}: {sta_change_val}")
    
    # print(f"K/9 v L Collector: {k_per_9_v_l_collector}")
    # print(f"K/9 v R Collector: {k_per_9_v_r_collector}")
    # print(f"BB/9 Collector: {bb_per_9_collector}")
    # print(f"Hit/9 v L Collector: {hit_per_9_v_l_collector}")
    # print(f"Hit/9 v R Collector: {hit_per_9_v_r_collector}")
    # print(f"Pitching Clutch Collector: {pitching_clutch_collector}")
    # print(f"Stamina Collector: {stamina_collector}")
    
    k_per_9_v_l_change_avg = round(sum(k_per_9_v_l_collector) / len(k_per_9_v_l_collector)) if k_per_9_v_l_collector else 0
    k_per_9_v_r_change_avg = round(sum(k_per_9_v_r_collector) / len(k_per_9_v_r_collector)) if k_per_9_v_r_collector else 0
    bb_per_9_change_avg = round(sum(bb_per_9_collector) / len(bb_per_9_collector)) if bb_per_9_collector else 0
    hit_per_9_v_l_change_avg = round(sum(hit_per_9_v_l_collector) / len(hit_per_9_v_l_collector)) if hit_per_9_v_l_collector else 0
    hit_per_9_v_r_change_avg = round(sum(hit_per_9_v_r_collector) / len(hit_per_9_v_r_collector)) if hit_per_9_v_r_collector else 0
    pitching_clutch_change_avg = round(sum(pitching_clutch_collector) / len(pitching_clutch_collector)) if pitching_clutch_collector else 0
    stamina_change_avg = round(sum(stamina_collector) / len(stamina_collector)) if stamina_collector else 0
    
    # print(f"K/9 v L Change Avg: {k_per_9_v_l_change_avg}")
    # print(f"K/9 v R Change Avg: {k_per_9_v_r_change_avg}")
    # print(f"BB/9 Change Avg: {bb_per_9_change_avg}")
    # print(f"Hit/9 v L Change Avg: {hit_per_9_v_l_change_avg}")
    # print(f"Hit/9 v R Change Avg: {hit_per_9_v_r_change_avg}")
    # print(f"Pitching Clutch Change Avg: {pitching_clutch_change_avg}")
    # print(f"Stamina Change Avg: {stamina_change_avg}")
    
    player['K/9 v L Change Avg'] = k_per_9_v_l_change_avg
    player['K/9 v R Change Avg'] = k_per_9_v_r_change_avg
    player['BB/9 Change Avg'] = bb_per_9_change_avg
    player['H/9 v L Change Avg'] = hit_per_9_v_l_change_avg
    player['H/9 v R Change Avg'] = hit_per_9_v_r_change_avg
    player['Pitching Clutch Change Avg'] = pitching_clutch_change_avg
    player['Stamina Change Avg'] = stamina_change_avg
    # print(player)
    # time.sleep(1000)
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
      
      if (player_thresholds.get('Power R', {}).get('in_game_lower', 0) <= hist_entry_pow_r_before <= player_thresholds.get('Power R', {}).get('in_game_upper', 0) and player_thresholds.get('HR v Right normalized', {}).get('irl_lower', 0) <= float(entry.get('HR v Right normalized', 0) or 0) <= player_thresholds.get('HR v Right normalized', {}).get('irl_upper', 0)):
        # print(entry)
        pow_r_change_val = entry.get('POW R Change', 0)
        try:
          power_r_collector.append(int(pow_r_change_val) if pow_r_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          power_r_collector.append(0)
        # print(f"Processed Power R for {hist_entry_name} on {hist_entry_date}: {pow_r_change_val}")
      if (player_thresholds.get('Power L', {}).get('in_game_lower', 0) <= hist_entry_pow_l_before <= player_thresholds.get('Power L', {}).get('in_game_upper', 0) and player_thresholds.get('HR v Left normalized', {}).get('irl_lower', 0) <= float(entry.get('HR v Left normalized', 0) or 0) <= player_thresholds.get('HR v Left normalized', {}).get('irl_upper', 0)):
        pow_l_change_val = entry.get('POW L Change', 0)
        try:
          power_l_collector.append(int(pow_l_change_val) if pow_l_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          power_l_collector.append(0)
        # print(f"Processed Power L for {hist_entry_name} on {hist_entry_date}: {pow_l_change_val}")
      if (player_thresholds.get('Con R', {}).get('in_game_lower', 0) <= hist_entry_con_r_before <= player_thresholds.get('Con R', {}).get('in_game_upper', 0) and player_thresholds.get('BA vs Right', {}).get('irl_lower', 0) <= float(entry.get('BA vs Right IRL', 0) or 0) <= player_thresholds.get('BA vs Right', {}).get('irl_upper', 0)):
        con_r_change_val = entry.get('CON R Change', 0)
        try:
          contact_r_collector.append(int(con_r_change_val) if con_r_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          contact_r_collector.append(0)
        # print(f"Processed Contact R for {hist_entry_name} on {hist_entry_date}: {con_r_change_val}")
      if (player_thresholds.get('Con L', {}).get('in_game_lower', 0) <= hist_entry_con_l_before <= player_thresholds.get('Con L', {}).get('in_game_upper', 0) and player_thresholds.get('BA vs Left', {}).get('irl_lower', 0) <= float(entry.get('BA vs Left IRL', 0) or 0) <= player_thresholds.get('BA vs Left', {}).get('irl_upper', 0)):
        con_l_change_val = entry.get('CON L Change', 0)
        try:
          contact_l_collector.append(int(con_l_change_val) if con_l_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          contact_l_collector.append(0)
        # print(f"Processed Contact L for {hist_entry_name} on {hist_entry_date}: {con_l_change_val}")
      if (player_thresholds.get('Batting Clutch', {}).get('in_game_lower', 0) <= hist_entry_batting_clutch <= player_thresholds.get('Batting Clutch', {}).get('in_game_upper', 0) and player_thresholds.get('BA with RISP', {}).get('irl_lower', 0) <= float(entry.get('BA with RISP IRL', 0) or 0) <= player_thresholds.get('BA with RISP', {}).get('irl_upper', 0)):
        batting_clutch_change_val = entry.get('CLT Change', 0)
        try:
          batting_clutch_collector.append(int(batting_clutch_change_val) if batting_clutch_change_val not in (None, '', 'NA') else 0)
        except ValueError:
          batting_clutch_collector.append(0)
        # print(f"Processed Batting Clutch for {hist_entry_name} on {hist_entry_date}: {batting_clutch_change_val}")
    
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
    # print(player)
    # time.sleep(10)
    predicted_players.append(player)
    
# print(predicted_players)

## Get the True Overall Change for each player

website_sheet_output = []
calculation_sheet_output = []

print("Calculating True Overall Changes now")
# print(predicted_players[0])
# time.sleep(1000)
counter = 2

for player in predicted_players:
  # print(player)
  # time.sleep(100)
  if player['Original_Name'] == "Shohei Ohtani":
    player['In_Game_Position'] = "DH"
    
  print(f"Calculating True Overall for player: {player['Original_Name']}")
  player_before_stats = {
      "display_position": player.get('In_Game_Position'), 
      "hits_per_9_right": player.get('H9 V R'),
      "hits_per_9_left": player.get('H9 V L'),
      "k_per_9_right": player.get('K9 V R'),
      "k_per_9_left": player.get('K9 V L'),
      "stamina": player.get('Stamina'),
      "pitching_clutch": player.get('Pitching Clutch'),
      "pitch_control": player.get('Pitch Control'),
      "pitch_rating_1":0,
      "pitch_rating_2":0,
      "pitch_rating_3":0,
      "pitch_count":0,
      "contact_right":player.get('Contact Right'),
      "contact_left":player.get('Contact Left'),
      "power_right":player.get('Power Right'),
      "power_left":player.get('Power Left'),
      "plate_vision":player.get('Plate Vision'),
      "batting_clutch":player.get('Batting Clutch'),
      "bunting_ability":player.get('Bunting Ability'),
      "drag_bunting_ability":player.get('Drag Bunting'),
      "fielding_ability":player.get('Fielding'),
      "arm_strength":player.get('Arm Strength'),
      "arm_accuracy":player.get('Arm Accuracy'),
      "reaction_forward":player.get('Reaction Time'),
      "reaction_back":player.get('Reaction Time'),
      "reaction_right":player.get('Reaction Time'),
      "reaction_left":player.get('Reaction Time'),
      "blocking":player.get('Blocking'),
      "pop_time":0,
      "speed":player.get('Speed'),
      "base_stealing":0
    }
  
  player_after_stats = {
      "display_position": player.get('In_Game_Position'), 
      "hits_per_9_right": int(player.get('H9 V R')) + int(player.get('H9 V R Change Avg', 0)),
      "hits_per_9_left": int(player.get('H9 V L')) + int(player.get('H9 V L Change Avg', 0)),
      "k_per_9_right": int(player.get('K9 V R')) + int(player.get('K9 V R Change Avg', 0)),
      "k_per_9_left": int(player.get('K9 V L')) + int(player.get('K9 V L Change Avg', 0)),
      "stamina": int(player.get('Stamina')) + int(player.get('Stamina Change Avg', 0)),
      "pitching_clutch": int(player.get('Pitching Clutch')) + int(player.get('Pitching Clutch Change Avg', 0)),
      "pitch_control": int(player.get('BB Per 9')) + int(player.get('BB/9 Change Avg', 0)),
      "pitch_rating_1":0,
      "pitch_rating_2":0,
      "pitch_rating_3":0,
      "pitch_count":0,
      "contact_right": int(player.get('Contact Right')) + int(player.get('Contact R Change Avg', 0)),
      "contact_left": int(player.get('Contact Left')) + int(player.get('Contact L Change Avg', 0)),
      "power_right": int(player.get('Power Right')) + int(player.get('Power R Change Avg', 0)),
      "power_left": int(player.get('Power Left')) + int(player.get('Power L Change Avg', 0)),
      "plate_vision":player.get('Plate Vision'),
      "batting_clutch":player.get('Batting Clutch'),
      "bunting_ability":player.get('Bunting Ability'),
      "drag_bunting_ability":player.get('Drag Bunting'),
      "fielding_ability":player.get('Fielding'),
      "arm_strength":player.get('Arm Strength'),
      "arm_accuracy":player.get('Arm Accuracy'),
      "reaction_forward":player.get('Reaction Time'),
      "reaction_back":player.get('Reaction Time'),
      "reaction_right":player.get('Reaction Time'),
      "reaction_left":player.get('Reaction Time'),
      "blocking":player.get('Blocking'),
      "pop_time":0,
      "speed":player.get('Speed'),
      "base_stealing":0
    }

  
  # print(player_before_stats)
  # print(player_after_stats)
  
  if player.get('In_Game_Position') == 'SP':
    # print('SP')
    # print("Pitching Clutch:", player.get('Pitching Clutch'))
    # print("Pitching Clutch Change Avg:", player.get('Pitching Clutch Change Avg', 0))
    # print("H9 V L:", player.get('H9 V L'))
    # print("H/9 v L Change Avg:", player.get('H/9 v L Change Avg', 0))
    # print("H9 V R:", player.get('H9 V R'))
    # print("H/9 v R Change Avg:", player.get('H/9 v R Change Avg', 0))
    # print("K9 V L:", player.get('K9 V L'))
    # print("K/9 v L Change Avg:", player.get('K/9 v L Change Avg', 0))
    # print("K9 V R:", player.get('K9 V R'))
    # print("K/9 v R Change Avg:", player.get('K/9 v R Change Avg', 0))
    # print("BB Per 9:", player.get('BB Per 9'))
    # print("BB/9 Change Avg:", player.get('BB/9 Change Avg', 0))
    # print("Stamina:", player.get('Stamina'))
    # print("Stamina Change Avg:", player.get('Stamina Change Avg', 0))

    old_true_overall = (int(player.get('Pitching Clutch')) / 17) + (int(player.get('H9 V L')) / 7.5) + (int(player.get('H9 V R')) / 7.5) + (int(player.get('K9 V L')) / 7) + (int(player.get('K9 V R')) / 7) + (int(player.get('BB Per 9')) / 4) + (int(player.get('Stamina')) / 12)
    new_true_overall = ((int(player.get('Pitching Clutch')) + int(player.get('Pitching Clutch Change Avg', 0))) / 17) + ((int(player.get('H9 V L')) + int(player.get('H/9 v L Change Avg', 0))) / 7.5) + ((int(player.get('H9 V R')) + int(player.get('H/9 v R Change Avg', 0))) / 7.5) + ((int(player.get('K9 V L')) + int(player.get('K/9 v L Change Avg', 0))) / 7) + ((int(player.get('K9 V R')) + int(player.get('K/9 v R Change Avg', 0))) / 7) + ((int(player.get('BB Per 9')) + int(player.get('BB/9 Change Avg', 0))) / 4) + ((int(player.get('Stamina')) + int(player.get('Stamina Change Avg', 0))) / 12)
    print(f"Old True Overall: {old_true_overall}, New True Overall: {new_true_overall}")
    
    overall_change_float = (new_true_overall - old_true_overall) * 0.9
    # print(overall_change_float)
    overall_change_final = round(overall_change_float, 2)
    # print(overall_change_final)
    # time.sleep(1000)
    
  elif player.get('In_Game_Position') == 'RP' or player.get('In_Game_Position') == 'CP':
    # print('RP/CP')
    # print("Pitching Clutch:", player.get('Pitching Clutch'))
    # print("Pitching Clutch Change Avg:", player.get('Pitching Clutch Change Avg', 0))
    # print("H9 V L:", player.get('H9 V L'))
    # print("H9 V L Change Avg:", player.get('H9 V L Change Avg', 0))
    # print("H9 V R:", player.get('H9 V R'))
    # print("H9 V R Change Avg:", player.get('H9 V R Change Avg', 0))
    # print("K9 V L:", player.get('K9 V L'))
    # print("K9 V L Change Avg:", player.get('K9 V L Change Avg', 0))
    # print("K9 V R:", player.get('K9 V R'))
    # print("K9 V R Change Avg:", player.get('K9 V R Change Avg', 0))
    # print("BB Per 9:", player.get('BB Per 9'))
    # print("BB Per 9 Change Avg:", player.get('BB Per 9 Change Avg', 0))
    # print("Stamina:", player.get('Stamina'))
    # print("Stamina Change Avg:", player.get('Stamina Change Avg', 0))
    old_true_overall = (int(player.get('Pitching Clutch')) / 10) + (int(player.get('H9 V L')) / 7) + (int(player.get('H9 V R')) / 7) + (int(player.get('K9 V L')) / 6.5) + (int(player.get('K9 V R')) / 6.5) + (int(player.get('BB Per 9')) / 4) + (int(player.get('Stamina')) / 25)
    new_true_overall = ((int(player.get('Pitching Clutch')) + int(player.get('Pitching Clutch Change Avg', 0))) / 10) + ((int(player.get('H9 V L')) + int(player.get('H/9 v L Change Avg', 0))) / 7) + ((int(player.get('H9 V R')) + int(player.get('H/9 v R Change Avg', 0))) / 7) + ((int(player.get('K9 V L')) + int(player.get('K/9 v L Change Avg', 0))) / 6.5) + ((int(player.get('K9 V R')) + int(player.get('K/9 v R Change Avg', 0))) / 6.5) + ((int(player.get('BB Per 9')) + int(player.get('BB/9 Change Avg', 0))) / 4) + ((int(player.get('Stamina')) + int(player.get('Stamina Change Avg', 0))) / 25)
    print(f"Old True Overall: {old_true_overall}, New True Overall: {new_true_overall}")
    
    overall_change_float = (new_true_overall - old_true_overall) * 0.9
    # print(overall_change_float)
    overall_change_final = round(overall_change_float, 2)
    # print(overall_change_final)
    # time.sleep(5)
  else:
    # print('Hitter')
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1.2 Safari/601.7.7",
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
        "Referer": "https://showzone.gg/",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    session = requests.Session()
    max_retries = 5
    for attempt in range(1, max_retries + 1):
      try:
        response1 = session.post('https://data.showzone.gg/api/true-overall/calculate', json=player_before_stats, headers=headers)
        if response1.status_code == 502:
          print(f"502 Bad Gateway for player {player.get('Original_Name', 'Unknown')} (before stats), attempt {attempt}/{max_retries}")
          if attempt < max_retries:
            time.sleep(2)
            continue
          else:
            response1.raise_for_status()
        response1.raise_for_status()
        response2 = session.post('https://data.showzone.gg/api/true-overall/calculate', json=player_after_stats, headers=headers)
        if response2.status_code == 502:
          print(f"502 Bad Gateway for player {player.get('Original_Name', 'Unknown')} (after stats), attempt {attempt}/{max_retries}")
          if attempt < max_retries:
            time.sleep(2)
            continue
          else:
            response2.raise_for_status()
        response2.raise_for_status()
        break  # Success, exit retry loop
      except requests.exceptions.RequestException as e:
        if (isinstance(e, requests.exceptions.HTTPError) and hasattr(e.response, 'status_code') and e.response is not None and e.response.status_code == 502 and attempt < max_retries):
          print(f"502 Bad Gateway for player {player.get('Original_Name', 'Unknown')}, attempt {attempt}/{max_retries}")
          time.sleep(2)
          continue
        print(f"Error during True Overall API request for player {player.get('Original_Name', 'Unknown')}: {e}")
        player['Overall Change'] = None
        player['Before Stats'] = player_before_stats
        player['After Stats'] = player_after_stats
        player['Old True Overall'] = None
        player['New True Overall'] = None
        break
    
    old_true_overall = float(response1.json().get('True Overall Rating', 0))
    new_true_overall = float(response2.json().get('True Overall Rating', 0))
    
    print(f"Old True Overall: {old_true_overall}, New True Overall: {new_true_overall}")
    
    overall_change_float = new_true_overall - old_true_overall
    overall_change_final = round(overall_change_float, 2)
    time.sleep(2)
  
  # print(overall_change_float, overall_change_final)
  
  player['Overall Change'] = overall_change_final
  player['Before Stats'] = player_before_stats
  player['After Stats'] = player_after_stats
  player['Old True Overall'] = old_true_overall
  player['New True Overall'] = new_true_overall
  
  # print(player)
  # time.sleep(2)
  
  # Hitter
  website_sheet_output.append({
    'Name': player.get('Original_Name'),
    'Team': player['Team'],
    'Position': player['In_Game_Position'],
    'Current OVR': player.get('OVR'),
    'Predicted OVR': round(int(player.get('OVR')) + overall_change_final),
    'Overall Change': overall_change_final,
    'Current Stam': player.get('Stamina'),
    'Predicted Stam': int(player.get('Stamina')) + player.get('Stamina Change Avg', 0),
    'Stam Change': player.get('Stamina Change Avg', 0),
    'Current PCLT': player.get('Pitching Clutch'),
    'Predicted PCLT': int(player.get('Pitching Clutch')) + player.get('Pitching Clutch Change Avg', 0),
    'PCLT Change': player.get('Pitching Clutch Change Avg', 0),
    'Current H/9 v R': player.get('H9 V R'),
    'Predicted H/9 v R': int(player.get('H9 V R')) + player.get('H/9 v R Change Avg', 0),
    'H/9 v R Change': player.get('H/9 v R Change Avg', 0),
    'Current H/9 v L': player.get('H9 V L'),
    'Predicted H/9 v L': int(player.get('H9 V L')) + player.get('H/9 v L Change Avg', 0),
    'H/9 v L Change': player.get('H/9 v L Change Avg', 0),
    'Current K/9 v L': player.get('K9 V L'),
    'Predicted K/9 v L': int(player.get('K9 V L')) + player.get('K/9 v L Change Avg', 0),
    'K/9 v L Change': player.get('K/9 v L Change Avg', 0),
    'Current K/9 v R': player.get('K9 V R'),
    'Predicted K/9 v R': int(player.get('K9 V R')) + player.get('K/9 v R Change Avg', 0),
    'K/9 v R Change': player.get('K/9 v R Change Avg', 0),
    'Current BB/9': player.get('BB Per 9'),
    'Predicted BB/9': int(player.get('BB Per 9')) + player.get('BB/9 Change Avg', 0),
    'BB/9 Change': player.get('BB/9 Change Avg', 0),
    'Current Con R': player.get('Contact Right'),
    'Predicted Con R': int(player.get('Contact Right')) + player.get('Contact R Change Avg', 0),
    'Con R Change': player.get('Contact R Change Avg', 0),
    'Current Con L': player.get('Contact Left'),
    'Predicted Con L': int(player.get('Contact Left')) + player.get('Contact L Change Avg', 0),
    'Con L Change': player.get('Contact L Change Avg', 0),
    'Current Pow R': player.get('Power Right'),
    'Predicted Pow R': int(player.get('Power Right')) + player.get('Power R Change Avg', 0),
    'Pow R Change': player.get('Power R Change Avg', 0),
    'Current Pow L': player.get('Power Left'),
    'Predicted Pow L': int(player.get('Power Left')) + player.get('Power L Change Avg', 0),
    'Pow L Change': player.get('Power L Change Avg', 0),
    'Current Batting Clutch': player.get('Batting Clutch'),
    'Predicted Batting Clutch': int(player.get('Batting Clutch')) + player.get('Batting Clutch Change Avg', 0),
    'Batting Clutch Change': player.get('Batting Clutch Change Avg', 0),
    'Buy Now Price': f"=XLOOKUP(AU{counter}, Players_Prices!C:C,Players_Prices!K:K)",
    'Profit': f"=XLOOKUP(E{counter},'Quicksell Prices'!A:A,'Quicksell Prices'!B:B) - AW{counter}",
    'ROI': f"=(AR{counter} / AQ{counter}) * 100",
    'Card Art URL': f'https://cards.theshow.com/mlb26/{player.get("UUID")}-baked-sm.webp',
    'UUID': player.get('UUID'),
    'Fangraphs_Player_ID': player.get('FanGraphPlayerID'),
    'Sell Now Price': f"=XLOOKUP(AU{counter}, Players_Prices!C:C,Players_Prices!J:J)",
    'BA vs Left': player.get('BA vs Left'),
    'BA vs Right': player.get('BA vs Right'),
    'BA with RISP': player.get('BA with RISP'),
    'HR per AB vs Left': player.get('HR per AB vs Left'),
    'HR per AB vs Right': player.get('HR per AB vs Right'),
    'H/9 vs Left': player.get('H9 vs Left'),
    'H/9 vs Right': player.get('H9 vs Right'),
    'K/9 vs Left': player.get('K9 vs Left'),
    'K/9 vs Right': player.get('K9 vs Right'),
    'BB/9': player.get('BB9'),
    'IP Per Game': player.get('InningsGame'),
    'Opp BA with RISP': player.get('OPP BA W RISP')
  })
  counter += 1
  # print(website_sheet_output)
  # time.sleep(100)



############ FIX THIS
def col_letter(col_idx):
  letters = ''
  while col_idx > 0:
    col_idx, rem = divmod(col_idx - 1, 26)
    letters = chr(65 + rem) + letters
  return letters

headers = list(website_sheet_output[0].keys())
rows_for_website = [headers] + [[row.get(h, "") for h in headers] for row in website_sheet_output]
end_col = col_letter(len(headers))
end_row = len(rows_for_website)
website_output_sheet.clear()
website_output_sheet.update(f"A1:{end_col}{end_row}", rows_for_website, value_input_option="USER_ENTERED")
