#!/usr/bin/env python3
"""
Utility functions for Ranch Scraper
Shared helpers for string normalization, validation, etc.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


def normalize_string(text: str) -> str:
    """
    Normalize string for comparison and display
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and convert to uppercase
    normalized = re.sub(r'\s+', ' ', text.strip()).upper()
    return normalized


def truncate_text(text: str, max_length: int, suffix: str = "..") -> str:
    """
    Truncate text to specified length with suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_table_data(data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Clean and normalize table data
    
    Args:
        data: Raw table data
        
    Returns:
        Cleaned table data
    """
    cleaned = []
    
    for row in data:
        cleaned_row = {}
        for key, value in row.items():
            if isinstance(value, str):
                # Remove extra whitespace and normalize
                cleaned_value = ' '.join(value.split())
                cleaned_row[key] = cleaned_value
            else:
                cleaned_row[key] = str(value) if value is not None else ""
        cleaned.append(cleaned_row)
    
    return cleaned


def detect_table_structure(table_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect table structure from data
    
    Args:
        table_data: Table data to analyze
        
    Returns:
        Dictionary with structure information
    """
    if not table_data:
        return {}
    
    # Get all unique keys
    all_keys = set()
    for row in table_data:
        all_keys.update(row.keys())
    
    # Analyze data types and patterns
    structure = {
        'columns': list(all_keys),
        'row_count': len(table_data),
        'column_types': {},
        'sample_data': table_data[0] if table_data else {}
    }
    
    # Analyze column types
    for key in all_keys:
        values = [row.get(key, '') for row in table_data]
        non_empty = [v for v in values if v]
        
        if non_empty:
            # Check if all values are numeric
            try:
                [float(v) for v in non_empty]
                structure['column_types'][key] = 'numeric'
            except ValueError:
                # Check if all values are short (likely codes)
                if all(len(str(v)) <= 10 for v in non_empty):
                    structure['column_types'][key] = 'code'
                else:
                    structure['column_types'][key] = 'text'
        else:
            structure['column_types'][key] = 'empty'
    
    return structure


def validate_search_params(params: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validate search parameters
    
    Args:
        params: Search parameters to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check if at least one parameter is provided
    if not any(params.values()):
        errors.append("At least one search parameter must be provided")
    
    # Validate specific parameters
    for key, value in params.items():
        if value:
            # Check for minimum length
            if len(value.strip()) < 1:
                errors.append(f"{key} cannot be empty")
            
            # Check for special characters that might cause issues
            if any(char in value for char in ['<', '>', '"', "'", '&']):
                errors.append(f"{key} contains invalid characters")
    
    return len(errors) == 0, errors


def format_table_output(data: List[Dict[str, str]], max_width: int = 80) -> str:
    """
    Format data as a table string
    
    Args:
        data: Data to format
        max_width: Maximum width for the table
        
    Returns:
        Formatted table string
    """
    if not data:
        return "No data to display"
    
    # Get column headers from first row
    headers = list(data[0].keys())
    
    # Calculate column widths
    col_widths = {}
    for header in headers:
        max_width_for_col = len(header)
        for row in data:
            value = str(row.get(header, ''))
            max_width_for_col = max(max_width_for_col, len(value))
        col_widths[header] = min(max_width_for_col, 30)  # Cap at 30 chars
    
    # Build table
    lines = []
    
    # Header
    header_line = " | ".join(f"{h:<{col_widths[h]}}" for h in headers)
    separator = "=" * len(header_line)
    lines.append(separator)
    lines.append(header_line)
    lines.append(separator)
    
    # Data rows
    for row in data:
        row_values = []
        for header in headers:
            value = str(row.get(header, ''))
            truncated = truncate_text(value, col_widths[header])
            row_values.append(f"{truncated:<{col_widths[header]}}")
        lines.append(" | ".join(row_values))
    
    lines.append(separator)
    lines.append(f"Total results: {len(data)}")
    
    return "\n".join(lines)


def parse_location_input(user_input: str) -> Dict[str, str]:
    """
    Parse location input into components
    
    Args:
        user_input: User's location input
        
    Returns:
        Dictionary with parsed components
    """
    if not user_input:
        return {}
    
    # Handle format like "United States|TX"
    if '|' in user_input:
        parts = user_input.split('|', 1)
        return {
            'country': parts[0].strip(),
            'state': parts[1].strip() if len(parts) > 1 else ''
        }
    
    # Handle state abbreviations
    state_abbreviations = {
        'TX': 'Texas', 'CA': 'California', 'NY': 'New York',
        'FL': 'Florida', 'IL': 'Illinois', 'PA': 'Pennsylvania',
        'OH': 'Ohio', 'GA': 'Georgia', 'NC': 'North Carolina',
        'MI': 'Michigan'
    }
    
    normalized_input = user_input.strip().upper()
    
    # Check if it's a state abbreviation
    if normalized_input in state_abbreviations:
        return {
            'state': state_abbreviations[normalized_input],
            'state_code': normalized_input
        }
    
    # Assume it's a state name
    return {
        'state': user_input.strip(),
        'country': 'United States'  # Default assumption
    }


def generate_filename(prefix: str = "ranch_results", extension: str = "csv") -> str:
    """
    Generate a filename with timestamp
    
    Args:
        prefix: Filename prefix
        extension: File extension
        
    Returns:
        Generated filename
    """
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file operations
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Ensure it's not empty
    if not filename:
        filename = "ranch_results"
    
    return filename 