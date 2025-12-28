"""Integration tests for revolut-edavki."""

import os
import tempfile
from pathlib import Path
import pytest
import pandas as pd
from flask import Flask


def test_flask_app_initialization():
    """Test that Flask app initializes correctly."""
    # Set environment variables for testing
    os.environ['DEBUG'] = 'false'
    os.environ['CORS_ORIGINS'] = 'http://localhost:3000'
    
    from server import app
    
    assert app is not None
    assert isinstance(app, Flask)
    assert app.config['DEBUG'] is False


def test_health_endpoint():
    """Test health check endpoint."""
    from server import app
    
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'revolut-edavki'
        assert 'version' in data


def test_index_endpoint():
    """Test index page loads."""
    from server import app
    
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200


def test_upload_missing_files():
    """Test upload endpoint with missing files."""
    from server import app
    
    with app.test_client() as client:
        response = client.post('/upload', data={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


def test_upload_invalid_file_type():
    """Test upload endpoint with invalid file type."""
    from server import app
    
    with app.test_client() as client:
        data = {
            'transactions': (tempfile.NamedTemporaryFile(suffix='.txt'), 'test.txt'),
            'company_info': (tempfile.NamedTemporaryFile(suffix='.txt'), 'test.txt'),
            'year': '2024',
            'tax_number': '12345678',
        }
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 400


def test_download_unauthorized_file():
    """Test download endpoint with unauthorized file."""
    from server import app
    
    with app.test_client() as client:
        response = client.get('/download/../../etc/passwd')
        assert response.status_code == 404


def test_allowed_file_validation():
    """Test file validation function."""
    from server import allowed_file
    
    # Valid files
    assert allowed_file('transactions.csv') is True
    assert allowed_file('company.xlsx') is True
    assert allowed_file('data.xml') is True
    
    # Invalid files
    assert allowed_file('script.py') is False
    assert allowed_file('../../../etc/passwd') is False
    assert allowed_file('file/with/path.csv') is False
    assert allowed_file('') is False
    assert allowed_file(None) is False


def test_converter_integration():
    """Test converter functions work together."""
    from revolut_edavki.converter import clean_amount
    
    # Test various amount formats
    assert clean_amount('$100.50', 1.1) == pytest.approx(91.36, rel=0.01)
    assert clean_amount('€50.00', 1.0) == 50.0
    assert clean_amount(100, 1.0) == 100.0


def test_security_utils_integration():
    """Test security utility functions."""
    from revolut_edavki.utils import hash_taxpayer_id, hash_filename, obscure_value
    
    # Test hashing
    tax_id = "12345678"
    hashed = hash_taxpayer_id(tax_id)
    assert len(hashed) == 12
    assert hashed != tax_id
    
    # Test filename hashing
    filename = "sensitive_data.csv"
    hashed_name = hash_filename(filename)
    assert hashed_name.endswith('.csv')
    assert 'sensitive_data' not in hashed_name
    
    # Test obscuring
    value = "secret123"
    obscured = obscure_value(value)
    assert obscured == "se***23"
    assert 'secret' not in obscured


def test_environment_configuration():
    """Test environment-based configuration."""
    from server import app
    
    # Test that app has configuration loaded
    assert 'DEBUG' in app.config
    assert 'MAX_CONTENT_LENGTH' in app.config
    assert 'UPLOAD_FOLDER' in app.config
    
    # Verify configuration is from environment or defaults
    assert isinstance(app.config['DEBUG'], bool)
    assert isinstance(app.config['MAX_CONTENT_LENGTH'], int)
    assert app.config['MAX_CONTENT_LENGTH'] > 0
