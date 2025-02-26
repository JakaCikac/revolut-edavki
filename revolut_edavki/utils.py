"""Utility functions for revolut-edavki."""

import hashlib
import os
from pathlib import Path
from typing import Optional


def hash_taxpayer_id(tax_id: str) -> str:
    """Hash taxpayer ID using SHA-256 with salt.

    Args:
        tax_id: Taxpayer identification number
    Returns:
        str: First 12 characters of the hashed value
    """
    salt = os.environ.get("TAX_SALT", "default_salt_change_in_production")
    hash_obj = hashlib.sha256(f"{tax_id}{salt}".encode())
    return hash_obj.hexdigest()[:12]


def hash_filename(filename: str) -> str:
    """Hash filename while preserving extension.

    Args:
        filename: Original filename
    Returns:
        str: Hashed filename with original extension
    """
    name = Path(filename).stem
    ext = Path(filename).suffix
    hash_obj = hashlib.sha256(name.encode())
    return f"{hash_obj.hexdigest()[:12]}{ext}"


def obscure_value(value: str) -> str:
    """Obscure a value for logging/display.

    Args:
        value: Value to obscure
    Returns:
        str: Obscured value (first 2 chars + *** + last 2 chars)
    """
    if not value or len(value) < 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"
