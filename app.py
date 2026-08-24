from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import requests
import time
import threading
import os

app = Flask(__name__, static_folder='static')
CORS(app)

cache = {
    'buy': [], 'sell': [],
    'last_update': 0, 'spread': 0,
    'best_buy': 0, 'best_sell': 0, 'history': []
}

HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://p2p.binance.com',
    'Referer': 'https://p2p.binance.com/'
}

def fetch_p2p(trade_type, rows=10):
    url = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
    payload = {"fiat":"JOD","page":1,"rows":rows,"tradeType":trade_type,"asset":"USDT","countries":[],"proMerchantAds":False,"shieldMerchantAds":False,"filterType":"all","periods":[],"additionalKycVerifyFilter":0,"publisherType":None,"payTypes":[],"classifies":["mass","profession"]}
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            return res.json().get('data', [])
    except Exception as e:
        print(f"Error: {e}")
    return []

def update_cache():
    while True:
        try:
            buy_ads = fetch_p2p('BUY', 10)
            sell_ads = fetch_p2p('SELL', 10)
            cache['buy'] = buy_ads
            cache['sell'] = sell_ads
            cache['last_update'] = time.time()
            if buy_ads and sell_ads:
                best_buy = float(buy_ads[0]['adv']['price'])
                best_sell = float(sell_ads[0]['adv']['price'])
                spread = round(best_buy - best_sell, 4)
                cache['best_buy'] = best_buy
                cache['best_sell'] = best_sell
                cache['spread'] = spread
                cache['history'].append({'time': int(time.time()*1000), 'spread': spread, 'buy': best_buy, 'sell': best_sell})
                if len(cache['history']) > 60:
                    cache['history'].pop(0)
            print(f"[{time.strftime('%H:%M:%S')}] Buy:{cache['best_buy']} Sell:{cache['best_sell']} Spread:{cache['spread']}")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(60)

@app.route('/api/prices')
def get_prices():
    def fmt(item):
        adv = item['adv']
        m = item['advertiser']
        return {'price': float(adv['price']), 'minAmount': float(adv['minSingleTransAmount']), 'maxAmount': float(adv['maxSingleTransAmount']), 'merchant': m.get('nickName','Unknown'), 'monthOrderCount': m.get('monthOrderCount',0), 'monthFinishRate': m.get('monthFinishRate',0)}
    return jsonify({'buy': [fmt(a) for a in cache['buy']], 'sell': [fmt(a) for a in cache['sell']], 'bestBuy': cache['best_buy'], 'bestSell': cache['best_sell'], 'spread': cache['spread'], 'lastUpdate': cache['last_update'], 'history': cache['history'][-20:]})

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    t = threading.Thread(target=update_cache, daemon=True)
    t.start()
    time.sleep(2)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
