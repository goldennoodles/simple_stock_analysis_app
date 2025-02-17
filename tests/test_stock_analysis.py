import pytest
from app import get_stock_data, calculate_technical_indicators
import pandas as pd

def test_get_stock_data_valid():
    df = get_stock_data('AAPL')
    assert not df.empty
    assert 'Close' in df.columns

def test_get_stock_data_invalid():
    df = get_stock_data('INVALIDSTOCK')
    assert df.empty

def test_technical_indicators():
    test_df = pd.DataFrame({
        'Close': [100, 101, 102, 103, 104] * 10
    })
    result_df = calculate_technical_indicators(test_df)
    assert '20_MA' in result_df.columns
    assert '50_MA' in result_df.columns
    assert not result_df['20_MA'].isnull().all()

def test_web_route(client):
    response = client.post('/', data={'symbol': 'AAPL'})
    assert response.status_code == 200
    assert b'AAPL Metrics' in response.data

def test_invalid_symbol(client):
    response = client.post('/', data={'symbol': 'INVALID'})
    assert b'Error fetching data' in response.data