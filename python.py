from flask import Flask, render_template, jsonify
from flask_cors import CORS
import yfinance as yf
import plotly.graph_objects as go
import json

app = Flask(__name__)
CORS(app)

def calculate_metrics(history):
    import numpy as np

    returns = np.diff(history['Close']) / history['Close'][:-1]

    rfr = 0.03 / 252
    excess = returns - rfr

    sharpe = 0
    if len(returns) > 0:
        avg_return = np.mean(excess)
        std_dev = np.std(returns)
        sharpe = np.sqrt(252) * (avg_return / std_dev) if std_dev != 0 else 0

    downside = returns[returns < 0]
    d_std = np.std(downside) if len(downside) > 0 else np.std(returns)
    sortino = np.sqrt(252) * (np.mean(excess) / d_std) if d_std != 0 else 0

    return {
        'sharpe_ratio': round(sharpe, 2),
        'sortino_ratio': round(sortino, 2)
    }

def get_stock_data():
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'BRK-B', 'LLY', 'TSM', 'V']
    result = {}

    for sym in tickers:
        t = yf.Ticker(sym)
        i = t.info
        h = t.history(period='1mo')
        m = calculate_metrics(h)

        result[sym] = {
            'name': i.get('longName', sym),
            'price': i.get('currentPrice', 0),
            'change': i.get('regularMarketChangePercent', 0),
            'sharpe_ratio': m['sharpe_ratio'],
            'sortino_ratio': m['sortino_ratio'],
            'history': {
                'dates': h.index.strftime('%Y-%m-%d').tolist(),
                'prices': h['Close'].tolist()
            }
        }

    return result

@app.route('/')
def home():
    data = get_stock_data()
    return render_template('index.html', stock_data=data)

@app.route('/api/stock-data')
def get_stocks():
    return jsonify(get_stock_data())

@app.route('/api/analyze-portfolio', methods=['POST'])
def analyze_portfolio():
    from flask import request
    try:
        raw = request.json.get('portfolio', '')
        parsed = {}
        for line in raw.strip().split('\n'):
            if line.strip():
                s = line.strip().split(',')
                parsed[s[0].upper()] = float(s[1])

        val_total = 0
        metrics = {}

        for sym, qty in parsed.items():
            stock = yf.Ticker(sym)
            price = stock.info.get('currentPrice', 0)
            position = qty * price
            val_total += position

            hist = stock.history(period='1mo')
            met = calculate_metrics(hist)

            metrics[sym] = {
                'shares': qty,
                'value': position,
                'weight': 0,
                'metrics': met
            }

        port_sharpe = 0
        port_sortino = 0

        for sym in metrics:
            w = metrics[sym]['value'] / val_total
            metrics[sym]['weight'] = w
            port_sharpe += w * metrics[sym]['metrics']['sharpe_ratio']
            port_sortino += w * metrics[sym]['metrics']['sortino_ratio']

        return jsonify({
            'status': 'success',
            'total_value': round(val_total, 2),
            'holdings': metrics,
            'portfolio_sharpe': round(port_sharpe, 2),
            'portfolio_sortino': round(port_sortino, 2)
        })
    except Exception as err:
        return jsonify({
            'status': 'error',
            'message': str(err)
        }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
