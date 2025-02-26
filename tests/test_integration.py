"""Integration tests for the tax report generator."""

import os
import pytest
from flask.testing import FlaskClient
from server import app
import pandas as pd
import xml.etree.ElementTree as ET

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = 'test_uploads'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.test_client() as client:
        yield client
    # Cleanup
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
    os.rmdir(app.config['UPLOAD_FOLDER'])

def test_home_page(client: FlaskClient):
    """Test that the home page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Tax Report Generator' in response.data

def test_upload_files(client: FlaskClient):
    """Test file upload and processing."""
    # Create test files
    transactions_df = pd.DataFrame({
        'Date': ['2024-01-03', '2024-02-17'],
        'Type': ['DIVIDEND', 'BUY'],
        'Ticker': ['AAPL', 'MSFT'],
        'Quantity': [100, 50],
        'Price per share': [0, 180.75],
        'Total Amount': [146, -9037.50],
        'Currency': ['USD', 'USD'],
        'FX Rate': [1.0918, 1.0799]
    })
    
    company_info_df = pd.DataFrame({
        'Symbol': ['AAPL', 'MSFT'],
        'Name': ['Apple Inc', 'Microsoft Corp'],
        'Address': ['One Apple Park Way', 'One Microsoft Way'],
        'CountryCode': ['US', 'US'],
        'ISIN': ['US0378331005', 'US5949181045']
    })
    
    # Save test files
    transactions_csv = 'test_transactions.csv'
    company_info_xlsx = 'test_company_info.xlsx'
    transactions_df.to_csv(transactions_csv, index=False)
    company_info_df.to_excel(company_info_xlsx, index=False)
    
    try:
        # Upload files
        with open(transactions_csv, 'rb') as transactions_file, \
             open(company_info_xlsx, 'rb') as company_info_file:
            response = client.post('/upload', data={
                'transactions': (transactions_file, 'transactions.csv'),
                'company_info': (company_info_file, 'company_info.xlsx'),
                'year': '2024',
                'tax_number': '12345678',
                'taxpayer_type': 'FO'
            })
        
        # Check response
        assert response.status_code == 200
        data = response.json
        
        # Check preview data
        assert 'kdvp' in data
        assert 'dividends' in data
        assert 'ifi' in data
        
        # Check dividend data
        assert len(data['dividends']) == 1
        dividend = data['dividends'][0]
        assert dividend['ticker'] == 'AAPL'
        assert dividend['amount'] == 146
        
        # Download and verify XML files
        response = client.get('/download/Doh-Div.xml')
        assert response.status_code == 200
        root = ET.fromstring(response.data)
        assert root.tag == 'Envelope'
        
    finally:
        # Cleanup test files
        os.remove(transactions_csv)
        os.remove(company_info_xlsx)

def test_error_handling(client: FlaskClient):
    """Test error handling for invalid uploads."""
    # Test missing files
    response = client.post('/upload', data={})
    assert response.status_code == 400
    assert b'Missing required files' in response.data
    
    # Test invalid file type
    with open('test.txt', 'w') as f:
        f.write('invalid data')
    try:
        with open('test.txt', 'rb') as f:
            response = client.post('/upload', data={
                'transactions': (f, 'test.txt'),
                'company_info': (f, 'test.txt')
            })
        assert response.status_code == 400
        assert b'Invalid file type' in response.data
    finally:
        os.remove('test.txt')