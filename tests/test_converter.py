import pytest
import pandas as pd
from datetime import datetime
from revolut_edavki.converter import clean_amount, create_kdvp_xml, create_div_xml, create_ifi_xml

# Test data
@pytest.fixture
def test_tax_info():
    """Test taxpayer information"""
    return {
        'tax_number': '12345678',
        'taxpayer_type': 'FO'
    }

@pytest.fixture
def sample_transactions():
    data = {
        'Date': [
            '2024-01-03', '2024-02-17', '2024-03-15', '2024-04-05',
            '2024-01-15', '2024-02-01', '2024-03-01', '2024-04-01',
            '2023-12-15', '2024-05-15', '2025-01-15'
        ],
        'Type': [
            'DIVIDEND', 'BUY', 'SELL', 'DIVIDEND',
            'BUY', 'SELL', 'DIVIDEND', 'BUY',
            'SELL', 'BUY', 'SELL'
        ],
        'Ticker': [
            'GRMN', 'AAPL', 'MSFT', 'GRMN',
            'NVDA', 'NVDA', 'AAPL', 'VWCE',
            'AAPL', 'MSFT', 'MSFT'
        ],
        'Quantity': [
            100, 50, 30, 100,
            20, 10, 50, 5,
            25, 40, 20
        ],
        'Price per share': [
            0, 180.75, 420.25, 0,
            450.25, 550.75, 0, 95.25,
            175.50, 390.25, 425.75
        ],
        'Total Amount': [
            1.46, -9037.50, 12607.50, 1.46,
            -9005.00, 5507.50, 1.43, -476.25,
            4387.50, -15610.00, 8515.00
        ],
        'Currency': [
            'USD', 'USD', 'USD', 'USD',
            'USD', 'USD', 'USD', 'EUR',
            'USD', 'USD', 'USD'
        ],
        'FX Rate': [
            1.0700, 1.0800, 1.0900, 1.0750,
            1.0850, 1.0950, 1.0800, 1.0000,
            1.0750, 1.0900, 1.1000
        ]
    }
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date'])
    return df

@pytest.fixture
def sample_company_info():
    data = {
        'Symbol': ['GRMN', 'AAPL', 'MSFT', 'NVDA', 'VWCE'],
        'Name': [
            'Garmin Ltd',
            'Apple Inc',
            'Microsoft Corporation',
            'NVIDIA Corporation',
            'Vanguard FTSE All-World UCITS ETF'
        ],
        'Address': [
            'Mühlentalstrasse 2, 8200 Schaffhausen, Switzerland',
            'One Apple Park Way, Cupertino, CA 95014, USA',
            'One Microsoft Way, Redmond, WA 98052, USA',
            '2788 San Tomas Expressway, Santa Clara, CA 95051, USA',
            '70 Sir John Rogerson\'s Quay, Dublin 2, Ireland'
        ],
        'CountryCode': ['USA', 'USA', 'USA', 'USA', 'IRL'],
        'ISIN': [
            'CH0114405324',
            'US0378331005',
            'US5949181045',
            'US67066G1040',
            'IE00BK5BQT80'
        ]
    }
    return pd.DataFrame(data)

# Test currency conversion
def test_clean_amount_eur():
    """Test EUR amount (no conversion needed)"""
    orig, eur, rate = clean_amount(100.50, fx_rate=1.0, return_details=True)
    assert orig == 100.50
    assert eur == 100.50
    assert rate == 1.0

def test_clean_amount_usd():
    """Test USD to EUR conversion"""
    orig, eur, rate = clean_amount(1.46, fx_rate=1.0700, return_details=True)
    assert orig == 1.46
    assert pytest.approx(eur, 0.01) == 1.36
    assert rate == 1.0700

def test_clean_amount_with_currency_symbols():
    """Test amount cleaning with currency symbols"""
    orig, eur, rate = clean_amount('$1,234.56', fx_rate=1.0800, return_details=True)
    assert orig == 1234.56
    assert pytest.approx(eur, 0.01) == 1143.11
    assert rate == 1.0800

def test_clean_amount_negative():
    """Test negative amount conversion"""
    orig, eur, rate = clean_amount(-525.75, fx_rate=1.0900, return_details=True)
    assert orig == -525.75
    assert pytest.approx(eur, 0.01) == -482.34
    assert rate == 1.0900

def test_clean_amount_zero():
    """Test zero amount"""
    orig, eur, rate = clean_amount(0, fx_rate=1.0700, return_details=True)
    assert orig == 0
    assert eur == 0
    assert rate == 1.0700

def test_clean_amount_nan():
    """Test NaN handling"""
    orig, eur, rate = clean_amount(float('nan'), fx_rate=1.0700, return_details=True)
    assert orig == 0
    assert eur == 0
    assert rate == 1.0700

# Test KDVP processing
def test_kdvp_sell_filtering(sample_transactions, sample_company_info, test_tax_info):
    """Test that only stocks with sells in target year are included"""
    create_kdvp_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_kdvp_buy_inclusion(sample_transactions, sample_company_info, test_tax_info):
    """Test that all buys are included for stocks with sells"""
    create_kdvp_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_kdvp_sell_year_filtering(sample_transactions, sample_company_info, test_tax_info):
    """Test that only sells from target year are included"""
    create_kdvp_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_kdvp_running_quantity(sample_transactions, sample_company_info, test_tax_info):
    """Test running quantity calculation"""
    create_kdvp_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_kdvp_currency_conversion(sample_transactions, sample_company_info, test_tax_info):
    """Test currency conversion in KDVP"""
    create_kdvp_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

# Test dividend processing
def test_dividend_year_filtering(sample_transactions, sample_company_info, test_tax_info):
    """Test that only dividends from target year are included"""
    create_div_xml(sample_transactions, sample_company_info, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_dividend_currency_conversion(sample_transactions, sample_company_info, test_tax_info):
    """Test currency conversion in dividends"""
    create_div_xml(sample_transactions, sample_company_info, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_dividend_company_info(sample_transactions, sample_company_info, test_tax_info):
    """Test company info inclusion in dividends"""
    create_div_xml(sample_transactions, sample_company_info, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_dividend_amount_format(sample_transactions, sample_company_info, test_tax_info):
    """Test dividend amount formatting"""
    create_div_xml(sample_transactions, sample_company_info, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_dividend_date_format(sample_transactions, sample_company_info, test_tax_info):
    """Test dividend date formatting"""
    create_div_xml(sample_transactions, sample_company_info, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

# Test IFI processing
def test_ifi_filtering(sample_transactions, sample_company_info, test_tax_info):
    """Test that only IFI transactions are included"""
    create_ifi_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_ifi_currency_conversion(sample_transactions, sample_company_info, test_tax_info):
    """Test currency conversion in IFI"""
    create_ifi_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_ifi_date_format(sample_transactions, sample_company_info, test_tax_info):
    """Test IFI date formatting"""
    create_ifi_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_ifi_amount_format(sample_transactions, sample_company_info, test_tax_info):
    """Test IFI amount formatting"""
    create_ifi_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_ifi_type_values(sample_transactions, sample_company_info, test_tax_info):
    """Test IFI transaction type values"""
    create_ifi_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

# Test edge cases
def test_empty_transactions(test_tax_info):
    """Test handling of empty transaction list"""
    empty_df = pd.DataFrame(columns=['Date', 'Type', 'Ticker', 'Quantity', 'Price per share', 'Total Amount', 'Currency', 'FX Rate'])
    create_kdvp_xml(empty_df, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_missing_company_info(sample_transactions, test_tax_info):
    """Test handling of missing company info"""
    empty_company_info = pd.DataFrame(columns=['Symbol', 'Name', 'Address', 'CountryCode', 'ISIN'])
    create_div_xml(sample_transactions, empty_company_info, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_invalid_dates(sample_transactions, sample_company_info, test_tax_info):
    """Test handling of invalid dates"""
    sample_transactions.loc[0, 'Date'] = None
    create_kdvp_xml(sample_transactions, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_invalid_amounts(sample_transactions, sample_company_info, test_tax_info):
    """Test handling of invalid amounts"""
    sample_transactions.loc[0, 'Total Amount'] = 'invalid'
    create_div_xml(sample_transactions, sample_company_info, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation

def test_invalid_fx_rates(sample_transactions, sample_company_info, test_tax_info):
    """Test handling of invalid FX rates"""
    sample_transactions.loc[0, 'FX Rate'] = 0
    create_div_xml(sample_transactions, sample_company_info, 2024, test_tax_info['tax_number'], test_tax_info['taxpayer_type'])
    # TODO: Add XML validation