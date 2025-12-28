"""Simple Flask server for tax report generation."""

import os
import logging
from pathlib import Path
from flask import Flask, render_template, request, send_file, jsonify
from flask_cors import CORS
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from revolut_edavki.converter import clean_amount, create_kdvp_xml, create_div_xml, create_ifi_xml

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='revolut_edavki/templates')

# Rate limiting configuration (optional, requires Flask-Limiter)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[os.getenv('RATE_LIMIT', '100 per hour')],
        storage_uri=os.getenv('RATE_LIMIT_STORAGE', 'memory://'),
    )
    logger.info('Rate limiting enabled')
except ImportError:
    limiter = None
    logger.warning('Flask-Limiter not installed. Rate limiting disabled. Install flask-limiter for production.')

# Environment-based CORS configuration
allowed_origins = os.getenv('CORS_ORIGINS', '*')
if allowed_origins == '*':
    logger.warning('CORS is configured to allow all origins. Set CORS_ORIGINS for production.')
    CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})
else:
    origins_list = [origin.strip() for origin in allowed_origins.split(',')]
    CORS(app, resources={r"/*": {"origins": origins_list}})
    logger.info(f'CORS configured for origins: {origins_list}')

# Configuration from environment
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_PATH', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 16 * 1024 * 1024))  # Default 16MB
app.config['DEBUG'] = os.getenv('DEBUG', 'false').lower() == 'true'

if app.config['DEBUG']:
    logger.warning('DEBUG mode is enabled. Disable for production!')

# Ensure upload directory exists with secure permissions
try:
    upload_path = Path(app.config['UPLOAD_FOLDER'])
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.info(f'Upload directory configured: {upload_path.absolute()}')
except Exception as e:
    logger.error(f'Failed to create upload directory: {e}')
    raise

def allowed_file(filename):
    """Validate file extension and check for path traversal."""
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f'Rejected suspicious filename: {filename}')
        return False
    
    allowed_extensions = {'csv', 'xlsx', 'xml'}
    has_extension = '.' in filename
    if has_extension:
        extension = filename.rsplit('.', 1)[1].lower()
        return extension in allowed_extensions
    return False

def get_bsrate():
    url = 'https://www.bsi.si/_data/tecajnice/dtecbs-l.xml'
    response = requests.get(url)
    if response.status_code == 200:
        # Save the file
        with open(os.path.join(app.config['UPLOAD_FOLDER'], 'bsrate.xml'), 'wb') as f:
            f.write(response.content)
        return True
    return False

def process_files(transactions_file, company_info_file, year, tax_number, taxpayer_type="FO"):
    try:
        # Save uploaded files
        transactions_path = os.path.join(app.config['UPLOAD_FOLDER'], 'transactions.csv')
        company_info_path = os.path.join(app.config['UPLOAD_FOLDER'], 'Company_info.xlsx')
        
        transactions_file.save(transactions_path)
        company_info_file.save(company_info_path)
        
        # Load data
        transactions = pd.read_csv(transactions_path)
        print(f"Loaded transactions: {len(transactions)} rows")
        
        transactions['Date'] = pd.to_datetime(transactions['Date'], format='mixed')
        print("Dates parsed successfully")
        
        company_info = pd.read_excel(company_info_path)
        print(f"Loaded company info: {len(company_info)} rows")
        
        # Validate company info columns
        required_columns = ['Symbol', 'Name', 'Address', 'CountryCode', 'ISIN']
        missing_columns = [col for col in required_columns if col not in company_info.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns in Company Info file: {', '.join(missing_columns)}")
        
        # Filter transactions for the selected year
        transactions_year = transactions[transactions['Date'].dt.year == year]
        print(f"Filtered transactions for {year}: {len(transactions_year)} rows")
        
        # Generate preview data
        preview = {
            'kdvp': [],
            'dividends': [],
            'ifi': []
        }
        
        # KDVP preview - only stocks with sells in target year
        stock_tx = transactions_year[
            (transactions_year['Type'].str.contains('BUY|SELL', na=False)) &
            (~transactions_year['Ticker'].isin(['VWCE']))
        ]
        print(f"Found {len(stock_tx)} stock transactions")
        
        # Get tickers with sells in target year
        sell_tickers = stock_tx[stock_tx['Type'].str.contains('SELL', na=False)]['Ticker'].unique()
        print(f"Found {len(sell_tickers)} tickers with sells: {', '.join(sell_tickers)}")
        
        for ticker in sell_tickers:
            ticker_tx = transactions[transactions['Ticker'] == ticker]
            buys = ticker_tx[ticker_tx['Type'].str.contains('BUY', na=False)]
            sells = ticker_tx[
                (ticker_tx['Type'].str.contains('SELL', na=False)) &
                (ticker_tx['Date'].dt.year == year)
            ]
            
            if len(sells) > 0:
                preview['kdvp'].append({
                    'ticker': ticker,
                    'buys': len(buys),
                    'sells': len(sells),
                    'last_buy': buys['Date'].max().strftime('%Y-%m-%d') if len(buys) > 0 else 'N/A',
                    'last_sell': sells['Date'].max().strftime('%Y-%m-%d')
                })
        
        # Dividends preview
        div_tx = transactions_year[
            (transactions_year['Type'] == 'DIVIDEND') &
            (~transactions_year['Ticker'].isin(['VWCE']))
        ]
        print(f"Found {len(div_tx)} dividend transactions")
        
        for _, tx in div_tx.iterrows():
            company_matches = company_info[company_info['Symbol'] == tx['Ticker']]
            if len(company_matches) > 0:
                company = company_matches.iloc[0]
                amount = abs(float(str(tx['Total Amount']).replace('$', '').replace('€', '').replace(',', '')))
                preview['dividends'].append({
                    'date': tx['Date'].strftime('%Y-%m-%d'),
                    'ticker': tx['Ticker'],
                    'company': company['Name'],
                    'amount': amount,
                    'fx_rate': tx['FX Rate']
                })
                print(f"Added dividend: {tx['Ticker']} - {amount} ({tx['Date'].strftime('%Y-%m-%d')})")
        
        # IFI preview
        ifi_tx = transactions_year[transactions_year['Ticker'] == 'VWCE']
        print(f"Found {len(ifi_tx)} IFI transactions")
        
        for _, tx in ifi_tx.iterrows():
            if 'BUY' in tx['Type'] or 'SELL' in tx['Type']:
                amount = abs(float(str(tx['Total Amount']).replace('€', '').replace(',', '')))
                preview['ifi'].append({
                    'date': tx['Date'].strftime('%Y-%m-%d'),
                    'type': 'Buy' if 'BUY' in tx['Type'] else 'Sell',
                    'amount': amount,
                    'shares': tx['Quantity']
                })
                print(f"Added IFI transaction: {'Buy' if 'BUY' in tx['Type'] else 'Sell'} - {amount} EUR ({tx['Date'].strftime('%Y-%m-%d')})")
        
        print("\nGenerating XML files...")
        create_kdvp_xml(transactions, year, tax_number, taxpayer_type)
        print("KDVP XML generated")
        create_div_xml(transactions_year, company_info, year, tax_number, taxpayer_type)
        print("Dividend XML generated")
        create_ifi_xml(transactions_year, year, tax_number, taxpayer_type)
        print("IFI XML generated")
        
        return preview
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        raise

@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'healthy',
        'service': 'revolut-edavki',
        'version': '1.0.0'
    }), 200

@app.route('/upload', methods=['POST'])
@limiter.limit('10 per hour') if limiter else lambda f: f
def upload():
    """Handle file upload and processing."""
    try:
        # Validate required files
        if 'transactions' not in request.files or 'company_info' not in request.files:
            logger.warning('Upload attempt with missing files')
            return jsonify({'error': 'Missing required files'}), 400
        
        transactions_file = request.files['transactions']
        company_info_file = request.files['company_info']
        
        # Validate filenames
        if not transactions_file.filename or not company_info_file.filename:
            logger.warning('Upload attempt with empty filenames')
            return jsonify({'error': 'Invalid file names'}), 400
        
        # Validate file types
        if not all(allowed_file(f.filename) for f in [transactions_file, company_info_file]):
            logger.warning(f'Invalid file types: {transactions_file.filename}, {company_info_file.filename}')
            return jsonify({'error': 'Invalid file type. Only CSV, XLSX, and XML files are allowed.'}), 400
        
        # Validate and parse parameters
        try:
            year = int(request.form.get('year', datetime.now().year))
            if year < 2000 or year > datetime.now().year + 1:
                return jsonify({'error': 'Invalid year'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid year format'}), 400
        
        tax_number = request.form.get('tax_number', '')
        taxpayer_type = request.form.get('taxpayer_type', 'FO')
        
        if taxpayer_type not in ['FO', 'SP', 'PO']:
            return jsonify({'error': 'Invalid taxpayer type'}), 400
        
        logger.info(f'Processing upload for year {year}, taxpayer type {taxpayer_type}')
        
        preview = process_files(transactions_file, company_info_file, year, tax_number, taxpayer_type)
        return jsonify(preview)
    
    except ValueError as e:
        logger.error(f'Validation error: {e}')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f'Upload processing error: {e}', exc_info=True)
        return jsonify({'error': 'An error occurred processing your files. Please check the format and try again.'}), 500

@app.route('/download/<filename>')
def download(filename):
    """Download generated report files."""
    # Whitelist of allowed files
    allowed_files = [
        'Doh-KDVP.xml', 'Doh-Div.xml', 'D-IFI.xml',
        'debug_dividends.csv', 'debug_kdvp.csv', 'debug_ifi.csv'
    ]
    
    # Strict filename validation
    if filename not in allowed_files:
        logger.warning(f'Attempt to download unauthorized file: {filename}')
        return jsonify({'error': 'File not found'}), 404
    
    # Check if file exists
    if not os.path.exists(filename):
        logger.warning(f'Requested file does not exist: {filename}')
        return jsonify({'error': 'File not found'}), 404
    
    try:
        logger.info(f'Downloading file: {filename}')
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logger.error(f'Error downloading file {filename}: {e}')
        return jsonify({'error': 'Error downloading file'}), 500

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=59855)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    args = parser.parse_args()
    app.run(host=args.host, port=args.port)