"""Search and sanitization utilities for preventing NoSQL injection."""
import re


def sanitize_search_input(search: str) -> str:
    """
    Sanitize search input to prevent NoSQL injection via regex.

    This function removes spaces and escapes regex special characters
    to ensure safe use in MongoDB regex queries.

    Args:
        search: Raw search string from user input

    Returns:
        Escaped search string safe for use in MongoDB regex queries

    Example:
        >>> sanitize_search_input("A12 3456")
        'A123456'
        >>> sanitize_search_input("test[]*+")
        'test\\[\\]\\*\\+'
    """
    # Remove spaces and escape regex special characters
    return re.escape(search.replace(" ", ""))
