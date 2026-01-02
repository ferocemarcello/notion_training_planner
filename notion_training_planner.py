import requests
import time
import sys
import argparse
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---

# Database IDs (Extracted from your prompt)
DB_WEEKLY_CHART = "2bcb920210da80128f0fd33399395d02"
DB_DAILY_PLANS = "2bcb920210da807796d1e828db3e031e"
DB_HR_ZONES = "2abb920210da80f8a30fdf2d15f36e3e"
DB_PHYSIO_STATS = "2c1b920210da80b8b5a7cd95de9d25ba"

# Headers for all requests (Populated in main)
HEADERS = {}

# --- HELPER FUNCTIONS ---

def find_page_by_property(db_id,property_name = "Name", property_value=None, index=0):
    """Query a database to find a page ID where property 'Name' equals specific value."""
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {}
    if property_value is not None:
        payload = {
            "filter": {
                "property": property_name,
                "title": {
                    "equals": property_value
                }
            }
        }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    # Handle API errors during query
    if response.status_code != 200:
        print(f"Error querying database {db_id}: {response.text}")
        return None
        
    data = response.json()
    if data["results"]:
        # We only return the ID of the specific index (defaults to the first result)
        if index < len(data["results"]):
            return data["results"][index]["id"]
    return None

def create_page(payload):
    """Raw wrapper to create a page."""
    url = "https://api.notion.com/v1/pages"
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code != 200:
        print(f"Error creating page: {response.text}")
        return None
    return response.json()["id"]

# --- MAIN LOGIC ---

def main():
    # 0. SETUP AND VALIDATION
    parser = argparse.ArgumentParser(description="Notion Training Planner")
    parser.add_argument("--token", required=True, help="Notion Integration Token")
    parser.add_argument("--start-date", required=True, help="First Monday (YYYY-MM-DD)")
    parser.add_argument("--weeks", type=int, required=True, help="Number of weeks")
    
    args = parser.parse_args()
    
    global HEADERS
    HEADERS.update({
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    })
    
    INPUT_FIRST_MONDAY = args.start_date
    INPUT_NUM_WEEKS = args.weeks

    try:
        # Parse input to datetime object at 00:00 UTC
        first_monday_dt = datetime.strptime(INPUT_FIRST_MONDAY, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"ERROR: Invalid date format. Use YYYY-MM-DD for INPUT_FIRST_MONDAY.")
        sys.exit(1)

    # 🚨 VALIDATION 1: Verify that INPUT_FIRST_MONDAY is a Monday (weekday() returns 0 for Monday)
    if first_monday_dt.weekday() != 0:
        print(f"ERROR: INPUT_FIRST_MONDAY ('{INPUT_FIRST_MONDAY}') is not a Monday. It is a {first_monday_dt.strftime('%A')}.")
        sys.exit(1)
    
    print(f"--- Starting Automation for {INPUT_NUM_WEEKS} weeks starting {first_monday_dt.date()} ---")

    # ---------------------------------------------------------
    # PRE-FETCHING IDs (Optimization & Strict Validation)
    # ---------------------------------------------------------
    print("Fetching IDs for HR Zones and Stats...")
    
    hr_map = {}
    
    # 🚨 VALIDATION 2: Check all required HR Zone IDs
    for zone in ["Z2", "Z3", "Z4", "Z5"]:
        p_id = find_page_by_property(DB_HR_ZONES, property_name="Zone", property_value=zone)
        if not p_id:
            print(f"CRITICAL ERROR: Could not find HR Zone page '{zone}' in DB {DB_HR_ZONES}")
            sys.exit(1)
        hr_map[zone] = p_id

    # 🚨 VALIDATION 3: Check Physiological Stats ID
    stats_id = find_page_by_property(DB_PHYSIO_STATS, property_name="Metric", property_value="Weight")
    if not stats_id:
        print(f"CRITICAL ERROR: Could not find Physiological Stats page 'Weight' in DB {DB_PHYSIO_STATS}")
        sys.exit(1)

    # ---------------------------------------------------------
    # PHASE 1: WEEKLY CHART
    # ---------------------------------------------------------
    print("\n--- Phase 1: Generating Weekly Charts ---")
    
    current_monday = first_monday_dt
    previous_week_id = None
    weeks_id_map = {} 

    for i in range(INPUT_NUM_WEEKS):
        # Calculate dates
        sunday = current_monday + timedelta(days=6)
        
        # Calculate Name: "Week <num> <year>"
        iso_year, iso_week, _ = current_monday.isocalendar()
        week_name = f"Week {iso_week} {iso_year}"
        
        # Format dates for Notion (ISO 8601)
        start_str = current_monday.strftime("%Y-%m-%d")
        end_str = sunday.strftime("%Y-%m-%d")

        print(f"Creating: {week_name} ({start_str} to {end_str})")

        # Construct Properties
        props = {
            "Name": {"title": [{"text": {"content": week_name}}]},
            "Week Start": {"date": {"start": start_str}}, 
            "Week End": {"date": {"start": end_str}},
            # 💡 NEW REQUIREMENT: Add Personal Data relation to Weekly Chart
            "Weight": {"relation": [{"id": stats_id}]}, 
        }
        
        # Handle "Previous Week" relation
        if previous_week_id:
            props["Previous Week"] = {"relation": [{"id": previous_week_id}]}

        # API Payload
        payload = {
            "parent": {"database_id": DB_WEEKLY_CHART},
            "properties": props
        }

        # Create Page
        new_page_id = create_page(payload)
        
        if new_page_id:
            # Store ID for Phase 2 mapping
            weeks_id_map[start_str] = new_page_id
            # Update previous_week for next iteration
            previous_week_id = new_page_id
        else:
            print(f"CRITICAL ERROR: Failed to create Weekly Chart page for {week_name}. Aborting Phase 1.")
            sys.exit(1)
        
        # Advance loop
        current_monday += timedelta(days=7)

    # ---------------------------------------------------------
    # PHASE 2: DAILY PLANS
    # ---------------------------------------------------------
    print("\n--- Phase 2: Generating Daily Plans ---")

    num_days = INPUT_NUM_WEEKS * 7
    current_day = first_monday_dt
    
    for j in range(num_days):
        day_str = current_day.strftime("%Y-%m-%d")
        
        # Calculate the Monday corresponding to this day to find the Linked Week
        monday_of_this_week = current_day - timedelta(days=current_day.weekday())
        monday_str = monday_of_this_week.strftime("%Y-%m-%d")
        
        linked_week_id = weeks_id_map.get(monday_str)

        if not linked_week_id:
            print(f"CRITICAL ERROR: Could not find parent week ID for day {day_str}. Aborting Phase 2.")
            sys.exit(1)

        # Formatting Change: DD.MM.YYYY
        day_name_str = current_day.strftime("%d.%m.%Y")
        
        print(f"Creating Day: {day_name_str}")

        # Construct Properties
        props = {
            # Use new DD.MM.YYYY format for the Title property
            "Name": {"title": [{"text": {"content": day_name_str}}]}, 
            "Date": {"date": {"start": day_str}}, 
            "Z2": {"relation": [{"id": hr_map["Z2"]}]},
            "Z3": {"relation": [{"id": hr_map["Z3"]}]},
            "Z4": {"relation": [{"id": hr_map["Z4"]}]},
            "Z5": {"relation": [{"id": hr_map["Z5"]}]},
            "Weight": {"relation": [{"id": stats_id}]},
            "Linked Week": {"relation": [{"id": linked_week_id}]}
        }
        
        payload = {
            "parent": {"database_id": DB_DAILY_PLANS},
            "properties": props
        }
        
        if not create_page(payload):
            print(f"CRITICAL ERROR: Failed to create Daily Plan page for {day_name_str}. Aborting Phase 2.")
            sys.exit(1)
        
        # Advance loop
        current_day += timedelta(days=1)
        
        # Sleep briefly to respect Notion API rate limits
        time.sleep(0.35) 

    print("\n--- Completed Successfully ---")

if __name__ == "__main__":
    main()
