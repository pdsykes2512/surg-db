"""
Field-Level Encryption Utility

Provides AES-256 encryption for sensitive patient data fields.
Complies with UK GDPR Article 32 (Security of Processing) and Caldicott Principles.

Usage:
    from app.utils.encryption import encrypt_field, decrypt_field

    # Encrypt
    encrypted_nhs = encrypt_field('nhs_number', '1234567890')

    # Decrypt
    nhs_number = decrypt_field('nhs_number', encrypted_nhs)

Sensitive Fields (UK GDPR Article 32 + Caldicott Principles):
    - nhs_number: NHS patient identifier
    - mrn: Medical record number (PAS number)
    - hospital_number: Legacy hospital identifier
    - first_name: Patient given name
    - last_name: Patient surname
    - date_of_birth: Patient DOB (quasi-identifier)
    - deceased_date: Date of death
    - postcode: Geographic identifier (partial)
"""

import os
import base64
import logging
from typing import Optional, Any
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Load environment variables
load_dotenv()

# Configuration
ENCRYPTION_KEY_FILE = Path(os.getenv('ENCRYPTION_KEY_FILE', '/root/.field-encryption-key'))
SALT_FILE = Path(os.getenv('ENCRYPTION_SALT_FILE', '/root/.field-encryption-salt'))

# Sensitive fields that require encryption (UK GDPR Article 32 + Caldicott Principles)
ENCRYPTED_FIELDS = {
    # Direct identifiers
    'nhs_number',           # National identifier
    'mrn',                  # Medical record number (PAS number)
    'hospital_number',      # Legacy hospital identifier

    # Personal identifiers
    'first_name',          # Given name
    'last_name',           # Surname/family name

    # Sensitive dates
    'date_of_birth',       # DOB is quasi-identifier
    'deceased_date',       # Date of death

    # Geographic identifiers
    'postcode'             # UK postcode (partial identifier)
}

# Encryption prefix to identify encrypted values
ENCRYPTION_PREFIX = 'ENC:'

# Logger
logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Custom exception for encryption errors"""
    pass


class DecryptionError(Exception):
    """Custom exception for decryption errors"""
    pass


def _get_or_create_encryption_key() -> Fernet:
    """
    Get or create encryption key for field-level encryption
    Uses PBKDF2 key derivation with AES-256

    Returns:
        Fernet cipher instance
    """
    # Check if key already exists
    if ENCRYPTION_KEY_FILE.exists() and SALT_FILE.exists():
        with open(ENCRYPTION_KEY_FILE, 'rb') as f:
            password = f.read()
        with open(SALT_FILE, 'rb') as f:
            salt = f.read()
        logger.debug("Loaded existing encryption key")
    else:
        # Generate new key and salt
        logger.warning("Generating new field encryption key - this should only happen once!")
        password = Fernet.generate_key()
        salt = os.urandom(16)

        # Create directory if it doesn't exist
        ENCRYPTION_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Save key and salt securely
        ENCRYPTION_KEY_FILE.write_bytes(password)
        ENCRYPTION_KEY_FILE.chmod(0o600)  # Read/write only by owner

        SALT_FILE.write_bytes(salt)
        SALT_FILE.chmod(0o600)

        logger.info(f"Encryption key created: {ENCRYPTION_KEY_FILE}")
        logger.info(f"Salt created: {SALT_FILE}")
        logger.warning("⚠️  IMPORTANT: Backup these files to a secure offline location!")

    # Derive encryption key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for AES-256
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password)

    # Return Fernet cipher with base64-encoded key
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


# Initialize cipher (singleton pattern)
_cipher = None


def _get_cipher() -> Fernet:
    """Get or create cipher instance (singleton)"""
    global _cipher
    if _cipher is None:
        _cipher = _get_or_create_encryption_key()
    return _cipher


def encrypt_field(field_name: str, value: Any) -> Optional[str]:
    """
    Encrypt a field value if it's a sensitive field

    Args:
        field_name: Name of the field (e.g., 'nhs_number')
        value: Value to encrypt

    Returns:
        Encrypted value with prefix, or original value if not sensitive

    Example:
        >>> encrypt_field('nhs_number', '1234567890')
        'ENC:gAAAAABh...'
        >>> encrypt_field('name', 'John Smith')
        'John Smith'  # Not encrypted (not a sensitive field)
    """
    # Skip if None or empty
    if value is None or value == '':
        return value

    # Only encrypt designated sensitive fields
    if field_name not in ENCRYPTED_FIELDS:
        return value

    # Check if already encrypted
    if isinstance(value, str) and value.startswith(ENCRYPTION_PREFIX):
        logger.debug(f"Field {field_name} already encrypted")
        return value

    try:
        # Convert to string and encode
        plaintext = str(value).encode('utf-8')

        # Encrypt
        cipher = _get_cipher()
        ciphertext = cipher.encrypt(plaintext)

        # Return with prefix
        encrypted = ENCRYPTION_PREFIX + base64.urlsafe_b64encode(ciphertext).decode('utf-8')
        logger.debug(f"Encrypted field: {field_name}")
        return encrypted

    except Exception as e:
        logger.error(f"Failed to encrypt field {field_name}: {e}")
        raise EncryptionError(f"Failed to encrypt {field_name}") from e


def decrypt_field(field_name: str, value: Any) -> Optional[str]:
    """
    Decrypt a field value if it's encrypted

    Args:
        field_name: Name of the field (e.g., 'nhs_number')
        value: Value to decrypt (should have ENC: prefix)

    Returns:
        Decrypted plaintext value, or original value if not encrypted

    Example:
        >>> decrypt_field('nhs_number', 'ENC:gAAAAABh...')
        '1234567890'
        >>> decrypt_field('name', 'John Smith')
        'John Smith'  # Not encrypted, return as-is
    """
    # Skip if None or empty
    if value is None or value == '':
        return value

    # Only process encrypted fields
    if not isinstance(value, str) or not value.startswith(ENCRYPTION_PREFIX):
        return value

    try:
        # Remove prefix
        encrypted_value = value[len(ENCRYPTION_PREFIX):]

        # Decode from base64
        ciphertext = base64.urlsafe_b64decode(encrypted_value.encode('utf-8'))

        # Decrypt
        cipher = _get_cipher()
        plaintext = cipher.decrypt(ciphertext)

        # Return decoded string
        decrypted = plaintext.decode('utf-8')
        logger.debug(f"Decrypted field: {field_name}")
        return decrypted

    except InvalidToken as e:
        logger.error(f"Invalid token when decrypting {field_name}: {e}")
        raise DecryptionError(f"Invalid encryption token for {field_name}") from e
    except Exception as e:
        logger.error(f"Failed to decrypt field {field_name}: {e}")
        raise DecryptionError(f"Failed to decrypt {field_name}") from e


def encrypt_document(document: dict) -> dict:
    """
    Encrypt all sensitive fields in a MongoDB document

    Args:
        document: MongoDB document (dict)

    Returns:
        Document with encrypted fields

    Example:
        >>> doc = {'nhs_number': '1234567890', 'name': 'John Smith'}
        >>> encrypt_document(doc)
        {'nhs_number': 'ENC:gAAAAABh...', 'name': 'John Smith'}
    """
    if not isinstance(document, dict):
        return document

    encrypted_doc = document.copy()

    for field_name in ENCRYPTED_FIELDS:
        if field_name in encrypted_doc:
            encrypted_doc[field_name] = encrypt_field(field_name, encrypted_doc[field_name])

    return encrypted_doc


def decrypt_document(document: dict) -> dict:
    """
    Decrypt all encrypted fields in a MongoDB document (recursively handles nested dicts)

    Args:
        document: MongoDB document (dict)

    Returns:
        Document with decrypted fields (including nested fields)

    Example:
        >>> doc = {
        ...     'nhs_number': 'ENC:gAAAAABh...',
        ...     'demographics': {'first_name': 'ENC:gAAAAABh...'},
        ...     'name': 'John Smith'
        ... }
        >>> decrypt_document(doc)
        {
            'nhs_number': '1234567890',
            'demographics': {'first_name': 'John'},
            'name': 'John Smith'
        }
    """
    if not isinstance(document, dict):
        return document

    decrypted_doc = {}

    for field_name, value in document.items():
        # Handle nested dictionaries recursively
        if isinstance(value, dict):
            decrypted_doc[field_name] = decrypt_document(value)
        # Handle encrypted string values
        elif isinstance(value, str) and value.startswith(ENCRYPTION_PREFIX):
            decrypted_doc[field_name] = decrypt_field(field_name, value)
        # Pass through all other values unchanged
        else:
            decrypted_doc[field_name] = value

    return decrypted_doc


def is_encrypted(value: Any) -> bool:
    """
    Check if a value is encrypted

    Args:
        value: Value to check

    Returns:
        True if value is encrypted (has ENC: prefix)
    """
    return isinstance(value, str) and value.startswith(ENCRYPTION_PREFIX)


def migrate_to_encrypted(collection, field_name: str, batch_size: int = 100):
    """
    Migrate an existing MongoDB collection to use encrypted fields

    Args:
        collection: pymongo Collection instance
        field_name: Name of field to encrypt
        batch_size: Number of documents to process at once

    Example:
        >>> from pymongo import MongoClient
        >>> client = MongoClient('mongodb://localhost:27017/')
        >>> db = client['surgical_outcomes']
        >>> migrate_to_encrypted(db.patients, 'nhs_number')
    """
    if field_name not in ENCRYPTED_FIELDS:
        logger.warning(f"Field {field_name} is not designated as encrypted")
        return

    logger.info(f"Starting migration for field: {field_name}")

    # Find all documents where field is not encrypted
    query = {
        field_name: {'$exists': True, '$not': {'$regex': f'^{ENCRYPTION_PREFIX}'}}
    }

    total = collection.count_documents(query)
    logger.info(f"Found {total} documents to encrypt")

    if total == 0:
        logger.info("No documents need encryption")
        return

    processed = 0
    cursor = collection.find(query).batch_size(batch_size)

    for doc in cursor:
        if field_name in doc and doc[field_name]:
            encrypted_value = encrypt_field(field_name, doc[field_name])

            collection.update_one(
                {'_id': doc['_id']},
                {'$set': {field_name: encrypted_value}}
            )

            processed += 1
            if processed % batch_size == 0:
                logger.info(f"Progress: {processed}/{total} documents encrypted")

    logger.info(f"Migration complete: {processed} documents encrypted")


def migrate_from_encrypted(collection, field_name: str, batch_size: int = 100):
    """
    Rollback: Decrypt an encrypted field in a MongoDB collection

    Args:
        collection: pymongo Collection instance
        field_name: Name of field to decrypt
        batch_size: Number of documents to process at once

    WARNING: Only use this for testing or rollback purposes!
    """
    logger.warning(f"Decrypting field {field_name} - this reduces security!")

    # Find all documents where field is encrypted
    query = {
        field_name: {'$regex': f'^{ENCRYPTION_PREFIX}'}
    }

    total = collection.count_documents(query)
    logger.info(f"Found {total} encrypted documents")

    if total == 0:
        logger.info("No encrypted documents found")
        return

    processed = 0
    cursor = collection.find(query).batch_size(batch_size)

    for doc in cursor:
        if field_name in doc and is_encrypted(doc[field_name]):
            decrypted_value = decrypt_field(field_name, doc[field_name])

            collection.update_one(
                {'_id': doc['_id']},
                {'$set': {field_name: decrypted_value}}
            )

            processed += 1
            if processed % batch_size == 0:
                logger.info(f"Progress: {processed}/{total} documents decrypted")

    logger.info(f"Decryption complete: {processed} documents processed")


# Query helper for encrypted fields
def create_encrypted_query(field_name: str, value: Any) -> dict:
    """
    Create a MongoDB query for an encrypted field

    Args:
        field_name: Name of the field
        value: Value to search for (plaintext)

    Returns:
        MongoDB query dict

    Example:
        >>> query = create_encrypted_query('nhs_number', '1234567890')
        >>> patients = collection.find(query)
    """
    if field_name in ENCRYPTED_FIELDS:
        encrypted_value = encrypt_field(field_name, value)
        return {field_name: encrypted_value}
    else:
        return {field_name: value}


# Pseudonymization helper (for audit logs)
def pseudonymize_for_logging(document: dict) -> dict:
    """
    Remove sensitive fields from a document for safe logging

    Args:
        document: Document to pseudonymize

    Returns:
        Document with sensitive fields replaced with [REDACTED]

    Example:
        >>> doc = {'nhs_number': '1234567890', 'name': 'John Smith', 'patient_id': 'P001'}
        >>> pseudonymize_for_logging(doc)
        {'nhs_number': '[REDACTED]', 'name': '[REDACTED]', 'patient_id': 'P001'}
    """
    safe_doc = document.copy()

    # Redact encrypted fields
    for field in ENCRYPTED_FIELDS:
        if field in safe_doc:
            safe_doc[field] = '[REDACTED]'

    # Redact other PII
    pii_fields = ['name', 'first_name', 'last_name', 'address', 'phone', 'email']
    for field in pii_fields:
        if field in safe_doc:
            safe_doc[field] = '[REDACTED]'

    return safe_doc


if __name__ == '__main__':
    # Self-test
    print("Testing field-level encryption...")

    test_cases = [
        ('nhs_number', '1234567890'),
        ('mrn', 'MRN12345'),
        ('postcode', 'SW1A 1AA'),
        ('date_of_birth', '1990-01-01'),
        ('name', 'John Smith')  # Not encrypted
    ]

    for field, value in test_cases:
        encrypted = encrypt_field(field, value)
        decrypted = decrypt_field(field, encrypted)

        if field in ENCRYPTED_FIELDS:
            assert encrypted.startswith(ENCRYPTION_PREFIX), f"Failed: {field} not encrypted"
            assert decrypted == value, f"Failed: {field} decryption mismatch"
            print(f"✓ {field}: {value} → {encrypted[:20]}... → {decrypted}")
        else:
            assert encrypted == value, f"Failed: {field} should not be encrypted"
            print(f"✓ {field}: {value} (not encrypted)")

    # Test document encryption
    doc = {
        'nhs_number': '9876543210',
        'mrn': 'MRN99999',
        'name': 'Jane Doe',
        'patient_id': 'P001'
    }

    encrypted_doc = encrypt_document(doc)
    decrypted_doc = decrypt_document(encrypted_doc)

    assert encrypted_doc['nhs_number'].startswith(ENCRYPTION_PREFIX)
    assert encrypted_doc['mrn'].startswith(ENCRYPTION_PREFIX)
    assert encrypted_doc['name'] == 'Jane Doe'  # Not encrypted
    assert decrypted_doc == doc

    print("\n✅ All tests passed!")
    print(f"\nEncryption key: {ENCRYPTION_KEY_FILE}")
    print(f"Salt file: {SALT_FILE}")
