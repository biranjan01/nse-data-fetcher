"""
Pure NSE data fetcher — NO processing, NO calculations.
Just fetches raw option chain JSON from NSE and saves it.
All processing happens in Vercel (JavaScript).
"""
import nsepythonserver
from concurrent.futures import ThreadPoolExecutor
import json
import os
from datetime import datetime, timezone

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


def fetch_one(symbol):
    """Fetch raw option chain JSON from NSE — no processing."""
    try:
        data = nsepythonserver.nse_optionchain_scrapper(symbol)
        if data and data.get("records") and data["records"].get("expiryDates"):
            return symbol, data
    except Exception as e:
        print(f"  FAIL {symbol}: {e}")
    return symbol, None


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()

    print(f"Fetching {len(FNO_STOCKS)} stocks from NSE...")
    results = {}

    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(fetch_one, s): s for s in FNO_STOCKS}
        for f in futures:
            sym, data = f.result()
            if data:
                # Extract only what Vercel needs — minimize file size
                records = data.get("records", {})
                nearest_expiry = records.get("expiryDates", [None])[0]
                raw = records.get("data", [])
                ltp = records.get("underlyingValue")

                # Filter to nearest expiry only
                filtered = [r for r in raw if r.get("expiryDate") == nearest_expiry]

                # Extract compact data for each strike
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

                results[sym] = {
                    "ltp": ltp,
                    "expiry": nearest_expiry,
                    "strikes": strikes,
                }

    output = {
        "timestamp": timestamp,
        "count": len(results),
        "stocks": results,
    }

    path = os.path.join(OUTPUT_DIR, "nse_data.json")
    with open(path, "w") as f:
        json.dump(output, f)

    print(f"\nSaved {len(results)} stocks to {path}")
    print(f"Timestamp: {timestamp}")
