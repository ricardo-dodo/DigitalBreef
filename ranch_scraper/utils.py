import re
from typing import List, Dict, Any, Optional, Tuple

def normalize_string(text: str) -> str:
    if not text:
        return ''
    normalized = re.sub('\\s+', ' ', text.strip()).upper()
    return normalized

def truncate_text(text: str, max_length: int, suffix: str='..') -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def clean_table_data(data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    cleaned = []
    for row in data:
        cleaned_row = {}
        for key, value in row.items():
            if isinstance(value, str):
                cleaned_value = ' '.join(value.split())
                cleaned_row[key] = cleaned_value
            else:
                cleaned_row[key] = str(value) if value is not None else ''
        cleaned.append(cleaned_row)
    return cleaned

def detect_table_structure(table_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not table_data:
        return {}
    all_keys = set()
    for row in table_data:
        all_keys.update(row.keys())
    structure = {'columns': list(all_keys), 'row_count': len(table_data), 'column_types': {}, 'sample_data': table_data[0] if table_data else {}}
    for key in all_keys:
        values = [row.get(key, '') for row in table_data]
        non_empty = [v for v in values if v]
        if non_empty:
            try:
                [float(v) for v in non_empty]
                structure['column_types'][key] = 'numeric'
            except ValueError:
                if all((len(str(v)) <= 10 for v in non_empty)):
                    structure['column_types'][key] = 'code'
                else:
                    structure['column_types'][key] = 'text'
        else:
            structure['column_types'][key] = 'empty'
    return structure

def validate_search_params(params: Dict[str, str]) -> Tuple[bool, List[str]]:
    errors = []
    if not any(params.values()):
        errors.append('At least one search parameter must be provided')
    for key, value in params.items():
        if value:
            if len(value.strip()) < 1:
                errors.append(f'{key} cannot be empty')
            if any((char in value for char in ['<', '>', '"', "'", '&'])):
                errors.append(f'{key} contains invalid characters')
    return (len(errors) == 0, errors)

def format_table_output(data: List[Dict[str, str]], max_width: int=80) -> str:
    if not data:
        return 'No data to display'
    headers = list(data[0].keys())
    display_headers = [h for h in headers if h not in ['member_id_html', 'addresses', 'phones', 'contacts']]
    col_widths = {}
    for header in display_headers:
        max_width_for_col = len(header)
        for row in data:
            value = str(row.get(header, ''))
            max_width_for_col = max(max_width_for_col, len(value))
        col_widths[header] = min(max_width_for_col, 30)
    lines = []
    header_line = ' | '.join((f'{h:<{col_widths[h]}}' for h in display_headers))
    separator = '=' * len(header_line)
    lines.append(separator)
    lines.append(header_line)
    lines.append(separator)
    for row in data:
        row_values = []
        for header in display_headers:
            value = str(row.get(header, ''))
            truncated = truncate_text(value, col_widths[header])
            row_values.append(f'{truncated:<{col_widths[header]}}')
        lines.append(' | '.join(row_values))
    lines.append(separator)
    lines.append(f'Total results: {len(data)}')
    return '\n'.join(lines)

def parse_location_input(user_input: str) -> Dict[str, str]:
    if not user_input:
        return {}
    if '|' in user_input:
        parts = user_input.split('|', 1)
        return {'country': parts[0].strip(), 'state': parts[1].strip() if len(parts) > 1 else ''}
    state_abbreviations = {'TX': 'Texas', 'CA': 'California', 'NY': 'New York', 'FL': 'Florida', 'IL': 'Illinois', 'PA': 'Pennsylvania', 'OH': 'Ohio', 'GA': 'Georgia', 'NC': 'North Carolina', 'MI': 'Michigan'}
    normalized_input = user_input.strip().upper()
    if normalized_input in state_abbreviations:
        return {'state': state_abbreviations[normalized_input], 'state_code': normalized_input}
    return {'state': user_input.strip(), 'country': 'United States'}

def generate_filename(prefix: str='ranch_results', extension: str='csv') -> str:
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'{prefix}_{timestamp}.{extension}'

def sanitize_filename(filename: str) -> str:
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    filename = filename.strip('. ')
    if not filename:
        filename = 'ranch_results'
    return filename

async def parse_profile_table(page) -> Dict[str, str]:
    try:
        await page.wait_for_selector('#ajax_profile_details table', timeout=10000)
        profile_data = await page.evaluate('\n            () => {\n                const table = document.querySelector(\'#ajax_profile_details table\');\n                if (!table) return { breeder_type: \'\', profile_data: {} };\n                \n                const rows = table.querySelectorAll(\'tr\');\n                const data = {};\n                let breeder_type = \'\';\n                \n                for (const row of rows) {\n                    const cells = row.querySelectorAll(\'td\');\n                    \n                    // Check for breeder type in first row with colspan="2"\n                    if (cells.length === 1 && cells[0].getAttribute(\'colspan\') === \'2\') {\n                        breeder_type = cells[0].textContent.trim();\n                        console.log(\'Found breeder type:\', breeder_type);\n                        continue;\n                    }\n                    \n                    // Handle regular label-value pairs\n                    if (cells.length >= 2) {\n                        const label = cells[0].textContent.trim();\n                        const value = cells[1].textContent.trim();\n                        \n                        if (label && value) {\n                            data[label] = value;\n                            console.log(\'Found field:\', label, \'=\', value);\n                        }\n                    }\n                }\n                \n                console.log(\'Final breeder_type:\', breeder_type);\n                console.log(\'Final data:\', data);\n                return { breeder_type, profile_data: data };\n            }\n        ')
        result = {'breeder_type': profile_data.get('breeder_type', ''), 'profile_type': profile_data.get('profile_data', {}).get('Profile Type:', ''), 'profile_id': profile_data.get('profile_data', {}).get('Official Profile ID:', ''), 'profile_name': profile_data.get('profile_data', {}).get('Official Profile Name:', ''), 'dba': profile_data.get('profile_data', {}).get('DBA:', ''), 'herd_prefix': profile_data.get('profile_data', {}).get('Herd Prefix:', '')}
        return result
    except Exception as e:
        print(f'Error parsing profile table: {e}')
        return {'breeder_type': '', 'profile_type': '', 'profile_id': '', 'profile_name': '', 'dba': '', 'herd_prefix': ''}
