from flask import Flask, render_template, request
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
from plotly.subplots import make_subplots


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

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))


    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()


    df['Middle_Band'] = df['Close'].rolling(window=20).mean()
    df['Upper_Band'] = df['Middle_Band'] + 2 * df['Close'].rolling(window=20).std()
    df['Lower_Band'] = df['Middle_Band'] - 2 * df['Close'].rolling(window=20).std()

    # Stochastic Oscillator
    df['L14'] = df['Low'].rolling(window=14).min()
    df['H14'] = df['High'].rolling(window=14).max()
    df['%K'] = 100 * ((df['Close'] - df['L14']) / (df['H14'] - df['L14']))
    df['%D'] = df['%K'].rolling(window=3).mean()

    # Average True Range (ATR)
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()

    df['Prediction'] = [
        'Uptrend' if (rsi > 50 and macd > signal and close > middle_band) else 'Downtrend'
        for rsi, macd, signal, close, middle_band in zip(df['RSI'], df['MACD'], df['Signal_Line'], df['Close'], df['Middle_Band'])
    ]

    return df


def create_indicator_plot(df, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.3, subplot_titles=('Candlestick Chart', 'Technical Indicators'))

    # Candlestick chart
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['Open'],
                                 high=df['High'],
                                 low=df['Low'],
                                 close=df['Close'],
                                 name='Candlestick'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['20_MA'], name='20 Day MA', line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['50_MA'], name='50 Day MA', line=dict(color='red')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Upper_Band'], name='Upper Bollinger Band', line=dict(color='grey', dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Band'], name='Lower Bollinger Band', line=dict(color='grey', dash='dash')), row=1, col=1)


    # Technical Indicators
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='orange')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], name='Signal Line', line=dict(color='green')), row=2, col=1)

    # Stochastic Oscillator
    fig.add_trace(go.Scatter(x=df.index, y=df['%K'], name='%K', line=dict(color='cyan')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['%D'], name='%D', line=dict(color='magenta')), row=2, col=1)

    # Average True Range (ATR)
    fig.add_trace(go.Scatter(x=df.index, y=df['ATR'], name='ATR', line=dict(color='yellow')), row=2, col=1)

    fig.update_layout(
        title=f'{symbol} Stock Analysis',
        xaxis_title='Date',
        template='plotly_dark',
        height=800
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
            
            indicator_plot_html = create_indicator_plot(df, symbol)
            
            latest_close = df['Close'].iloc[-1]
            previous_close = df['Close'].iloc[-2]
            percent_change = round(((latest_close - previous_close) / previous_close) * 100, 2)
            price_change = round(latest_close - previous_close, 2)
            
            metrics = {
                "symbol": symbol,
                "current_price": round(latest_close, 2),
                "price_change": price_change,
                "percent_change": percent_change,
                "ma_20": round(df['20_MA'].iloc[-1], 2) if not pd.isna(df['20_MA'].iloc[-1]) else None,
                "ma_50": round(df['50_MA'].iloc[-1], 2) if not pd.isna(df['50_MA'].iloc[-1]) else None,
                "prediction": df['Prediction'].iloc[-1],
                "rsi": round(df['RSI'].iloc[-1], 2) if not pd.isna(df['RSI'].iloc[-1]) else None,
                "macd": round(df['MACD'].iloc[-1], 2) if not pd.isna(df['MACD'].iloc[-1]) else None,
                "signal_line": round(df['Signal_Line'].iloc[-1], 2) if not pd.isna(df['Signal_Line'].iloc[-1]) else None,
                "upper_band": round(df['Upper_Band'].iloc[-1], 2) if not pd.isna(df['Upper_Band'].iloc[-1]) else None,
                "lower_band": round(df['Lower_Band'].iloc[-1], 2) if not pd.isna(df['Lower_Band'].iloc[-1]) else None,
                "k": round(df['%K'].iloc[-1], 2) if not pd.isna(df['%K'].iloc[-1]) else None,
                "d": round(df['%D'].iloc[-1], 2) if not pd.isna(df['%D'].iloc[-1]) else None,
                "atr": round(df['ATR'].iloc[-1], 2) if not pd.isna(df['ATR'].iloc[-1]) else None
            }

            
            return render_template('index.html', indicator_plot_html=indicator_plot_html, metrics=metrics, error=None, symbol=symbol, period=period)
        
        except (KeyError, ValueError, yf.YFinanceError) as e:
            return render_template('index.html', plot_html=None, metrics=None, error=f"Error: {str(e)}", symbol=symbol, period=period)
    
    return render_template('index.html', plot_html=None, metrics=None, error=None, symbol='', period='1y')

if __name__ == '__main__':
    app.run(debug=True)
