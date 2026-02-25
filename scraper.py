import pandas as pd
import requests
import os
from datetime import datetime
import time

# --- CONFIGURATION ---
API_KEY = os.environ.get("TCG_API_KEY")
INVENTORY_FILE = "master_inventory.csv"
HISTORY_FILE = "ev_history.csv"
API_URL = "https://api.pokemontcg.io/v2/cards/"

# Final verified mapping for 2026 API database
SET_ID_MAP = {
    "me01": "me1",
    "me02": "me2",
    "sv8pt5": "sv8pt5" 
}

def get_market_price(csv_card_id):
    """
    Translates IDs and extracts the 'market' price from TCGPlayer data.
    """
    try:
        prefix, num = csv_card_id.split('-')
        api_prefix = SET_ID_MAP.get(prefix, prefix)
        # API requires integer-based IDs (no leading zeros)
        api_id = f"{api_prefix}-{int(num)}"
    except Exception:
        return 0

    headers = {"X-Api-Key": API_KEY} if API_KEY else {}
    
    try:
        response = requests.get(f"{API_URL}{api_id}", headers=headers)
        if response.status_code == 200:
            data = response.json().get('data', {})
            prices = data.get('tcgplayer', {}).get('prices', {})
            
            # The 'Market Price System': prioritizes standard market values
            for category in ['normal', 'holofoil', 'reverseHolofoil']:
                if category in prices:
                    val = prices[category].get('market')
                    if val:
                        return float(val)
        return 0
    except Exception:
        return 0

def main():
    if not os.path.exists(INVENTORY_FILE):
        print("Error: master_inventory.csv not found.")
        return

    df = pd.read_csv(INVENTORY_FILE)
    print(f"Fetching market prices for {len(df)} cards...")

    # Fetch daily prices
    current_prices = []
    for idx, row in df.iterrows():
        price = get_market_price(row['card_id'])
        current_prices.append(price)
        
        # Batch logging for progress
        if (idx + 1) % 50 == 0:
            print(f"Progress: {idx + 1}/{len(df)} cards...")
        
        # Safety sleep for rate limits
        if not API_KEY:
            time.sleep(0.1)

    df['market_price'] = current_prices
    df['ev_contribution'] = df['market_price'] * df['pull_rate']
    
    # Expected Value Calculation
    summary = df.groupby('set_name')['ev_contribution'].sum().reset_index()
    summary.columns = ['set_name', 'expected_value']
    summary['date'] = datetime.now().strftime("%Y-%m-%d")
    
    # Save to ev_history.csv
    if os.path.exists(HISTORY_FILE):
        history = pd.read_csv(HISTORY_FILE)
        today = datetime.now().strftime("%Y-%m-%d")
        # Overwrite if re-running on the same day
        history = history[history['date'] != today]
        final_df = pd.concat([history, summary], ignore_index=True)
    else:
        final_df = summary
        
    final_df.to_csv(HISTORY_FILE, index=False)
    print(f"Success. EV History updated for {datetime.now().strftime('%Y-%m-%d')}.")

if __name__ == "__main__":
    main()

