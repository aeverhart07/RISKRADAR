from flask import Flask, render_template, request
import yfinance as yf
import plotly.graph_objects as go
import plotly.utils
import json

app = Flask(__name__)

def fetch_stock_data(ticker_symbol):
    try:
        stock_obj = yf.Ticker(ticker_symbol)
        stock_details = stock_obj.info
        price_history = stock_obj.history(period="1mo")

        if len(price_history) > 0:
            start_price = price_history['Close'][0]
            end_price = price_history['Close'][-1]
            pct_change = ((end_price - start_price) / start_price) * 100
            history_list = price_history['Close'].tolist()
        else:
            pct_change = 0
            history_list = []

        return {
            'name': stock_details.get('longName', ticker_symbol),
            'price': stock_details.get('currentPrice', 0),
            'change': pct_change,
            'history': history_list
        }
    except Exception as e:
        return {
            'name': ticker_symbol,
            'price': 0,
            'change': 0,
            'history': []
        }

def make_graph(stock_map):
    fig = go.Figure()

    for ticker_code, stock_info in stock_map.items():
        fig.add_trace(go.Scatter(
            y=stock_info['history'],
            name=ticker_code,
            mode='lines'
        ))

    fig.update_layout(
        title="30 Day Stock Performance",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@app.route('/')
def index():
    default_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'BRK-B']
    all_stocks = {}

    for sym in default_tickers:
        all_stocks[sym] = fetch_stock_data(sym)

    stock_chart = make_graph(all_stocks)
    return render_template('index.html', stock_data=all_stocks, graph_json=stock_chart)

@app.route('/analyze', methods=['POST'])
def analyze_portfolio():
    raw_input = request.form.get('portfolio', '')
    portfolio = {}
    total_value = 0

    lines = raw_input.strip().split('\n')

    for entry in lines:
        entry = entry.strip()
        if not entry:
            continue

        try:
            parts = entry.split(',')
            stock_sym = parts[0].strip().upper()
            share_count = float(parts[1].strip())

            stock_info = fetch_stock_data(stock_sym)
            stock_val = share_count * stock_info['price']

            portfolio[stock_sym] = {
                'shares': share_count,
                'price': stock_info['price'],
                'value': stock_val,
                'history': stock_info['history']
            }

            total_value += stock_val
        except:
            continue

    chart = make_graph(portfolio)
    return render_template('analysis.html', holdings=portfolio, total_value=round(total_value, 2), graph_json=chart)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
