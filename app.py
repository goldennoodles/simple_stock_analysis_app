from flask import Flask, render_template, request
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd

app = Flask(__name__)

def get_stock_data(symbol, period='1y'):
    stock = yf.Ticker(symbol)
    hist = stock.history(period=period)
    if hist.empty:
        raise ValueError("No data found for the given symbol.")
    return hist

def calculate_technical_indicators(df):
    df['20_MA'] = df['Close'].rolling(window=20).mean()
    df['50_MA'] = df['Close'].rolling(window=50).mean()

    df['Prediction'] = ['Uptrend' if ma20 > ma50 else 'Downtrend' 
                        for ma20, ma50 in zip(df['20_MA'], df['50_MA'])]

    return df


def create_plot(df, symbol):
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['Open'],
                                 high=df['High'],
                                 low=df['Low'],
                                 close=df['Close'],
                                 name='Candlestick'))
    fig.add_trace(go.Scatter(x=df.index, y=df['20_MA'], name='20 Day MA', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['50_MA'], name='50 Day MA', line=dict(color='red')))
    
    fig.update_layout(
        title=f'{symbol} Stock Price Analysis',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        template='plotly_dark'
    )
    return fig.to_html(full_html=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        symbol = request.form["symbol"].upper()
        period = request.form.get('period', '1y')
        
        try:
            df = get_stock_data(symbol, period)
            df = calculate_technical_indicators(df)
            
            if df.isna().all().any():
                raise ValueError("Insufficient data for analysis.")
            
            plot_html = create_plot(df, symbol)
            
            latest_close = df['Close'].iloc[-1]
            previous_close = df['Close'].iloc[-2]
            percent_change = round(((latest_close - previous_close) / previous_close) * 100, 2)
            price_change = round(latest_close - previous_close, 2)
            
            metrics = {
                "symbol": symbol,
                "current_price": latest_close,
                "price_change": price_change,
                "percent_change": percent_change,
                "ma_20": round(df['20_MA'].iloc[-1], 2) if not pd.isna(df['20_MA'].iloc[-1]) else None,
                "ma_50": round(df['50_MA'].iloc[-1], 2) if not pd.isna(df['50_MA'].iloc[-1]) else None,
                "prediction": df['Prediction'].iloc[-1]  # Last row's prediction
            }

            
            return render_template('index.html', plot_html=plot_html, metrics=metrics, error=None)
        
        except (KeyError, ValueError, yf.YFinanceError) as e:
            return render_template('index.html', plot_html=None, metrics=None, error=f"Error: {str(e)}")
    
    return render_template('index.html', plot_html=None, metrics=None, error=None)

if __name__ == '__main__':
    app.run(debug=True)
