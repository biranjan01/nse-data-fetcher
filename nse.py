"""
NSE Data Fetcher — uses nsefetch (curl_cffi) to bypass Akamai bot detection.
Fetches option chain data for all F&O stocks and saves compact JSON.
"""
import json
import os
import time
from datetime import datetime, timezone
from nsefetch.config import load_settings
from nsefetch.client import NSEHttpClient

# All F&O stocks
FNO_STOCKS = [
    "TCS", "LTIM", "TECHM", "HCLTECH", "INFY", "WIPRO", "IRCTC", "PERSISTENT", "COFORGE", "BSOFT",
    "AARTIIND", "MPHASIS", "MGL", "NATIONALUM", "TATACOMM", "MARICO", "ASTRAL", "AUBANK",
    "HINDPETRO", "JSWSTEEL", "MANAPPURAM", "SBILIFE", "SONACOMS", "BAJAJFINSV", "UPL",
    "LT", "BRITANNIA", "MUTHOOTFIN", "BHARTIARTL", "BAJFINANCE", "TATACONSUM", "HINDUNILVR",
    "ATGL", "NYKAA", "ONGC", "HDFCLIFE", "LICI", "HEROMOTOCO", "TATAMOTORS", "NESTLEIND",
    "KEI", "ZYDUSLIFE", "HDFCBANK", "BPCL", "BAJAJ-AUTO", "RELIANCE", "ICICIPRULI",
    "GODREJCP", "ABFRL", "DELHIVERY", "MARUTI", "DABUR", "TRENT", "ETERNAL", "ICICIBANK",
    "COALINDIA", "APOLLOHOSP", "JSL", "CONCOR", "ABB", "DRREDDY", "CIPLA", "DIXON", "MFSL",
    "NAUKRI", "M&M", "IOC", "ICICIGI", "DIVISLAB", "PIIND", "SBICARD", "INDIGO", "JUBLFOOD",
    "ASIANPAINT", "TITAN", "ITC", "M&MFIN", "JINDALSTEL", "HINDCOPPER", "BHARATFORG",
    "EICHERMOT", "VEDL", "BSE", "VBL", "BALKRISIND", "TATASTEEL", "ADANIPORTS", "NHPC",
    "TORNTPHARM", "KOTAKBANK", "ASHOKLEY", "IGL", "TVSMOTOR", "EXIDEIND", "GAIL",
    "POWERGRID", "PRESTIGE", "HAVELLS", "PAGEIND", "SYNGENE", "PIDILITIND", "GRANULES",
    "ACC", "SAIL", "GRASIM", "INDIANB", "AXISBANK", "SBIN", "BANKBARODA", "LODHA",
    "SUNPHARMA", "PETRONET", "CHAMBLFERT", "COLPAL", "IDEA", "ALKEM", "POONAWALLA",
    "RBLBANK", "SIEMENS", "INDHOTEL", "OFSS", "APLAPOLLO", "FEDERALBNK", "HINDALCO",
    "ADANIENSOL", "HDFCAMC", "AMBUJACEM", "OIL", "GMRAIRPORT", "UNITDSPR", "LUPIN", "NCC",
    "MOTHERSON", "NMDC", "SUPREMEIND", "JSWENERGY", "HAL", "YESBANK", "POLYCAB", "BIOCON",
    "JIOFIN", "CHOLAFIN", "IEX", "DMART", "SRF", "CYIENT", "CAMS", "LICHSGFIN",
    "IDFCFIRSTB", "ANGELONE", "BOSCHLTD", "CROMPTON", "TIINDIA", "IRFC", "TATAPOWER",
    "CANBK", "BANDHANBNK", "TATACHEM", "PNB", "ADANIGREEN", "INDUSTOWER", "GLENMARK",
    "LTF", "ABCAPITAL", "SJVN", "ULTRACEMCO", "VOLTAS", "DLF", "POLICYBZR", "BEL", "MCX",
    "NTPC", "CUMMINSIND", "PEL", "AUROPHARMA", "ADANIENT", "DALBHARAT", "CGPOWER", "HFCL",
    "PFC", "UNIONBANK", "INDUSINDBK", "GODREJPROP", "BANKINDIA", "CESC", "LAURUSLABS",
    "IRB", "KPITTECH", "MAXHEALTH", "CDSL", "PAYTM", "SHRIRAMFIN", "OBEROIRLTY", "HUDCO",
    "KALYANKJIL", "BHEL", "RECLTD", "TATAELXSI", "SOLARINDS", "PATANJALI", "PHOENIXLTD",
    "NBCC", "IREDA", "TATATECH", "IIFL", "TORNTPOWER", "TITAGARH", "INOXWIND",
    "PNBHOUSING", "HINDZINC", "UNOMINDA", "RVNL", "PPLPHARMA", "MAZDOCK", "MANKIND",
    "KAYNES", "FORTIS", "BLUESTARCO", "BDL"
]

OUTPUT_DIR = "docs"


def fetch_one(client, symbol):
    """Fetch option chain for a single symbol using nsefetch."""
    try:
        # Get expiry dates
        contract_info = client.request_json(
            "GET", "/api/option-chain-contract-info", params={"symbol": symbol}
        )
        expiry_dates = contract_info.get("expiryDates", [])
        if not expiry_dates:
            return symbol, None

        nearest_expiry = expiry_dates[0]

        # Determine type (Indices vs Equity)
        is_index = symbol in {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50"}
        chain_type = "Indices" if is_index else "Equity"

        # Fetch option chain
        data = client.request_json(
            "GET",
            "/api/option-chain-v3",
            params={"type": chain_type, "symbol": symbol, "expiry": nearest_expiry},
        )

        if not data or "records" not in data:
            return symbol, None

        records = data["records"]
        underlying = records.get("underlyingValue")
        raw = records.get("data", [])

        # Filter to nearest expiry only (v3 uses "expiryDates" plural)
        filtered = [r for r in raw if r.get("expiryDates") == nearest_expiry]

        # Extract compact data
        strikes = []
        for row in filtered:
            ce = row.get("CE", {})
            pe = row.get("PE", {})
            strikes.append({
                "strike": row.get("strikePrice"),
                "ce_oi": ce.get("openInterest", 0),
                "ce_change_oi": ce.get("changeinOpenInterest", 0),
                "ce_vol": ce.get("totalTradedVolume", 0),
                "pe_oi": pe.get("openInterest", 0),
                "pe_change_oi": pe.get("changeinOpenInterest", 0),
                "pe_vol": pe.get("totalTradedVolume", 0),
            })

        return symbol, {
            "ltp": underlying,
            "expiry": nearest_expiry,
            "strikes": strikes,
        }

    except Exception as e:
        print(f"  FAIL {symbol}: {e}")
        return symbol, None


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    settings = load_settings()
    client = NSEHttpClient(settings=settings)

    print(f"Bootstrapping NSE session...")
    client.bootstrap_session()
    print(f"Session OK. Fetching {len(FNO_STOCKS)} stocks...")

    results = {}
    success = 0
    fail = 0

    for i, symbol in enumerate(FNO_STOCKS):
        sym, data = fetch_one(client, symbol)
        if data:
            results[sym] = data
            success += 1
        else:
            fail += 1

        # Progress every 20 stocks
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i + 1}/{len(FNO_STOCKS)} (ok={success}, fail={fail})")

        # Small delay to avoid rate limiting
        time.sleep(0.3)

    client.close()

    output = {
        "timestamp": timestamp,
        "count": len(results),
        "stocks": results,
    }

    path = os.path.join(OUTPUT_DIR, "nse_data.json")
    with open(path, "w") as f:
        json.dump(output, f)

    print(f"\nDone! Saved {len(results)} stocks to {path}")
    print(f"Success: {success}, Failed: {fail}")
    print(f"Timestamp: {timestamp}")
