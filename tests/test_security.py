import os
import pytest
from revolut_edavki.utils import hash_taxpayer_id, hash_filename, obscure_value


def test_hash_taxpayer_id():
    """Test taxpayer ID hashing"""
    tax_id = "12345678"
    hashed = hash_taxpayer_id(tax_id)
    assert len(hashed) == 12
    assert hashed.isalnum()
    # Same input should produce same hash
    assert hash_taxpayer_id(tax_id) == hashed


def test_hash_taxpayer_id_with_salt():
    """Test that different salts produce different hashes"""
    tax_id = "12345678"
    os.environ["TAX_SALT"] = "salt1"
    hash1 = hash_taxpayer_id(tax_id)
    os.environ["TAX_SALT"] = "salt2"
    hash2 = hash_taxpayer_id(tax_id)
    assert hash1 != hash2


def test_hash_filename():
    """Test filename hashing"""
    filename = "transactions.csv"
    hashed = hash_filename(filename)
    assert hashed.endswith(".csv")
    assert len(hashed) > 4
    assert hashed != filename


def test_hash_filename_preserves_extension():
    """Test that filename hashing preserves extension"""
    filenames = ["file.txt", "data.csv", "report.xlsx", "test.file.xml"]
    for filename in filenames:
        hashed = hash_filename(filename)
        assert hashed.endswith(os.path.splitext(filename)[1])


def test_obscure_value():
    """Test value obscuring"""
    assert obscure_value("12345678") == "12***78"
    assert obscure_value("test") == "te***st"
    assert obscure_value("a") == "****"


def test_obscure_value_short():
    """Test obscuring short values"""
    assert obscure_value("") == "****"
    assert obscure_value("a") == "****"
    assert obscure_value("ab") == "****"
    assert obscure_value("abc") == "****"
