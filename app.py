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

    # Calculate RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Calculate MACD
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Calculate Bollinger Bands
    df['Middle_Band'] = df['Close'].rolling(window=20).mean()
    df['Upper_Band'] = df['Middle_Band'] + 2 * df['Close'].rolling(window=20).std()
    df['Lower_Band'] = df['Middle_Band'] - 2 * df['Close'].rolling(window=20).std()

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
    
    # RSI
    # fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')))

    # # MACD and Signal Line
    # fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='orange')))
    # fig.add_trace(go.Scatter(x=df.index, y=df['Signal_Line'], name='Signal Line', line=dict(color='green')))

    # # Bollinger Bands
    # fig.add_trace(go.Scatter(x=df.index, y=df['Upper_Band'], name='Upper Bollinger Band', line=dict(color='grey', dash='dash')))
    # fig.add_trace(go.Scatter(x=df.index, y=df['Lower_Band'], name='Lower Bollinger Band', line=dict(color='grey', dash='dash')))

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
                "prediction": df['Prediction'].iloc[-1],  # Last row's prediction
                "rsi": round(df['RSI'].iloc[-1], 2) if not pd.isna(df['RSI'].iloc[-1]) else None,
                "macd": round(df['MACD'].iloc[-1], 2) if not pd.isna(df['MACD'].iloc[-1]) else None,
                "signal_line": round(df['Signal_Line'].iloc[-1], 2) if not pd.isna(df['Signal_Line'].iloc[-1]) else None,
                "upper_band": round(df['Upper_Band'].iloc[-1], 2) if not pd.isna(df['Upper_Band'].iloc[-1]) else None,
                "lower_band": round(df['Lower_Band'].iloc[-1], 2) if not pd.isna(df['Lower_Band'].iloc[-1]) else None
            }

            
            return render_template('index.html', plot_html=plot_html, metrics=metrics, error=None)
        
        except (KeyError, ValueError, yf.YFinanceError) as e:
            return render_template('index.html', plot_html=None, metrics=None, error=f"Error: {str(e)}")
    
    return render_template('index.html', plot_html=None, metrics=None, error=None)

if __name__ == '__main__':
    app.run(debug=True)
