"""
Tests for encryption/decryption utilities

Critical security functionality - encrypts sensitive patient data.
"""
import pytest
from app.utils.encryption import (
    encrypt_field,
    decrypt_field,
    encrypt_document,
    decrypt_document,
    create_searchable_query,
    generate_search_hash
)


class TestEncryption:
    """Test encryption and decryption functions"""

    def test_encrypt_decrypt_field(self):
        """Test basic field encryption and decryption"""
        original = "1234567890"
        encrypted = encrypt_field("mrn", original)

        # Encrypted should be different from original
        assert encrypted != original
        assert encrypted is not None

        # Decryption should return original
        decrypted = decrypt_field("mrn", encrypted)
        assert decrypted == original

    def test_encrypt_none_field(self):
        """Test that None values are not encrypted"""
        encrypted = encrypt_field("mrn", None)
        assert encrypted is None

        decrypted = decrypt_field("mrn", None)
        assert decrypted is None

    def test_encrypt_empty_string(self):
        """Test that empty strings are not encrypted"""
        encrypted = encrypt_field("mrn", "")
        assert encrypted == ""

    def test_encrypt_document(self):
        """Test encrypting a full patient document"""
        patient = {
            "patient_id": "TEST01",
            "mrn": "12345678",
            "nhs_number": "9876543210",
            "demographics": {
                "date_of_birth": "1975-03-15",
                "postcode": "SW1A 1AA"
            }
        }

        encrypted = encrypt_document(patient.copy())

        # Sensitive fields should be encrypted
        assert encrypted["mrn"] != patient["mrn"]
        assert encrypted["nhs_number"] != patient["nhs_number"]

        # Non-sensitive fields should be unchanged
        assert encrypted["patient_id"] == patient["patient_id"]

        # Search hashes should be generated
        assert "mrn_hash" in encrypted
        assert "nhs_number_hash" in encrypted

    def test_decrypt_document(self):
        """Test decrypting a full patient document"""
        patient = {
            "patient_id": "TEST01",
            "mrn": "12345678",
            "nhs_number": "9876543210",
            "demographics": {
                "date_of_birth": "1975-03-15",
                "postcode": "SW1A 1AA"
            }
        }

        encrypted = encrypt_document(patient.copy())
        decrypted = decrypt_document(encrypted)

        # All fields should match original
        assert decrypted["mrn"] == patient["mrn"]
        assert decrypted["nhs_number"] == patient["nhs_number"]

    def test_search_hash_consistency(self):
        """Test that search hashes are consistent for same input"""
        value = "12345678"
        hash1 = generate_search_hash("mrn", value)
        hash2 = generate_search_hash("mrn", value)

        assert hash1 == hash2
        assert len(hash1) > 0

    def test_searchable_query(self):
        """Test creating searchable query for encrypted field"""
        mrn = "12345678"
        query = create_searchable_query("mrn", mrn)

        assert "mrn_hash" in query
        assert query["mrn_hash"] == generate_search_hash("mrn", mrn)

    def test_encryption_produces_different_ciphertexts(self):
        """
        Test that same plaintext produces different ciphertexts
        (due to IV randomization in AES).
        This is important for security.
        """
        original = "test_value_123"
        encrypted1 = encrypt_field("mrn", original)  # Use a real encrypted field
        encrypted2 = encrypt_field("mrn", original)  # Use a real encrypted field

        # Different ciphertexts
        assert encrypted1 != encrypted2

        # Both decrypt to same value
        assert decrypt_field("mrn", encrypted1) == original
        assert decrypt_field("mrn", encrypted2) == original
