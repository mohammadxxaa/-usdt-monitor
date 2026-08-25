from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import time
import threading
import os

app = Flask(__name__, static_folder='static')
CORS(app)

cache = {
    'buy': [],
    'sell': [],
    'last_update': 0,
    'spread': 0,
    'best_buy': 0,
    'best_sell': 0,
    'history': []
}

def fetch_price():
    try:
        # Binance public API - no blocking
        url = 'https://api.binance.com/api/v3/ticker/bookTicker?symbol=USDTJOD'
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return float(data['bidPrice']), float(data['askPrice'])
    except Exception as e:
        print(f"Error: {e}")
    return None, None

def update_cache():
    while True:
        try:
            bid, ask = fetch_price()
            if bid and ask:
                cache['best_buy'] = bid
                cache['best_sell'] = ask
                cache['spread'] = round(bid - ask, 4)
                cache['last_update'] = time.time()
                cache['history'].append({
                    'time': int(time.time() * 1000),
                    'spread': cache['spread'],
                    'buy': bid,
                    'sell': ask
                })
                if len(cache['history']) > 60:
                    cache['history'].pop(0)
                print(f"[{time.strftime('%H:%M:%S')}] Buy:{bid} Sell:{ask} Spread:{cache['spread']}")
            else:
                print("No data received")
        except Exception as e:
            print(f"Cache error: {e}")
        time.sleep(60)

@app.route('/api/prices')
def get_prices():
    return jsonify({
        'buy': [],
        'sell': [],
        'bestBuy': cache['best_buy'],
        'bestSell': cache['best_sell'],
        'spread': cache['spread'],
        'lastUpdate': cache['last_update'],
        'history': cache['history'][-20:]
    })

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    t = threading.Thread(target=update_cache, daemon=True)
    t.start()
    time.sleep(2)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
