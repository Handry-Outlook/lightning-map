# scrape_and_plot.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import json
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime, timedelta
import os

# Scrape strikes
def scrape_strikes():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    
    url = "https://map.blitzortung.org/"
    driver.get(url)
    print(f"[{datetime.now()}] Loading map, waiting for strikes...")
    time.sleep(30)
    
    script = """
        var strikes = [];
        try {
            if (typeof window.Strikes !== 'undefined') {
                strikes = window.Strikes;
            } else if (typeof map !== 'undefined') {
                if (typeof map.getStyle === 'function') {
                    var sources = map.getStyle().sources;
                    for (var key in sources) {
                        if (sources[key].type === 'geojson' && sources[key].data) {
                            strikes = sources[key].data.features || [];
                            break;
                        }
                    }
                }
            }
        } catch (e) {
            console.log('Error:', e);
        }
        return JSON.stringify(strikes);
    """
    try:
        strikes_data = driver.execute_script(script)
        strikes = json.loads(strikes_data) if strikes_data else []
        print(f"[{datetime.now()}] Scraped {len(strikes)} strikes")
    except Exception as e:
        print(f"[{datetime.now()}] Script error: {e}")
        strikes = []
    
    driver.quit()
    return strikes

# Load existing strikes
data_file = "strikes.json"
if os.path.exists(data_file):
    with open(data_file, "r") as f:
        all_strikes = json.load(f)
else:
    all_strikes = []

# Scrape new strikes
new_strikes = scrape_strikes()
now = datetime.now()
for strike in new_strikes:
    try:
        lon, lat = strike["geometry"]["coordinates"]
        if -44 <= lat <= -10 and 113 <= lon <= 154:  # Australia bounds
            strike_data = {
                "lat": lat,
                "lon": lon,
                "time": strike["properties"].get("time", now.isoformat())
            }
            if not any(s["lat"] == lat and s["lon"] == lon and s["time"] == strike_data["time"] for s in all_strikes):
                all_strikes.append(strike_data)
    except (KeyError, TypeError) as e:
        print(f"[{datetime.now()}] Skipping malformed strike: {e}")

# Filter for last 24 hours
cutoff = now - timedelta(hours=24)
all_strikes = [s for s in all_strikes if datetime.fromisoformat(s["time"]) > cutoff]
print(f"[{datetime.now()}] Total Australia strikes (last 24h): {len(all_strikes)}")

# Save updated strikes
with open(data_file, "w") as f:
    json.dump(all_strikes, f)

# Plot
plt.figure(figsize=(10, 10))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([113, 154, -44, -10], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.COASTLINE)
ax.add_feature(cfeature.BORDERS)

for strike in all_strikes:
    plt.plot(strike["lon"], strike["lat"], 'ro', markersize=5, transform=ccrs.PlateCarree())

plt.title(f"Australia Lightning Strikes - Last 24 Hours ({now.strftime('%Y-%m-%d %H:%M')})")
plt.savefig("australia_lightning_24h.png", dpi=300, bbox_inches="tight")
plt.close()
print("PNG saved as 'australia_lightning_24h.png'")