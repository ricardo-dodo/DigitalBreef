#!/usr/bin/env python3
"""
Dynamic Form Parser for Ranch Scraper
Detects and extracts form fields and dropdown options at runtime
"""

from typing import List, Dict, Optional, Tuple
from playwright.async_api import Page
import re


class FormParser:
    """Dynamic form field detection and parsing"""
    
    def __init__(self):
        self.field_mappings = {
            'ranch_search_val': 'name',
            'ranch_search_city': 'city', 
            'ranch_search_id': 'member_id',
            'ranch_search_prefix': 'prefix',
            'search-member-location': 'location'
        }
    
    async def get_dropdown_options(self, page: Page, select_id: str) -> List[Dict[str, str]]:
        """
        Extract all options from a dropdown select element
        
        Args:
            page: Playwright page object
            select_id: ID of the select element
            
        Returns:
            List of dictionaries with 'value' and 'text' keys
        """
        try:
            options = await page.evaluate(f"""
                () => {{
                    const select = document.querySelector('#{select_id}');
                    if (!select) return [];
                    
                    const options = Array.from(select.options);
                    return options.map(option => ({{
                        value: option.value,
                        text: option.text.trim()
                    }}));
                }}
            """)
            
            return options
        except Exception as e:
            print(f"Error extracting dropdown options for {select_id}: {e}")
            return []
    
    async def find_input_fields(self, page: Page) -> Dict[str, str]:
        """
        Dynamically detect all input fields on the page
        
        Args:
            page: Playwright page object
            
        Returns:
            Dictionary mapping field names to their selectors
        """
        try:
            fields = await page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input, select, textarea');
                    const fields = {};
                    
                    inputs.forEach(input => {
                        const id = input.id;
                        const name = input.name;
                        const type = input.type || input.tagName.toLowerCase();
                        
                        if (id) {
                            fields[id] = {
                                selector: `#${id}`,
                                type: type,
                                name: name || id
                            };
                        }
                    });
                    
                    return fields;
                }
            """)
            
            return fields
        except Exception as e:
            print(f"Error finding input fields: {e}")
            return {}
    
    async def validate_required_fields(self, page: Page) -> Tuple[bool, List[str]]:
        """
        Validate that all required form fields are present
        
        Args:
            page: Playwright page object
            
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        required_fields = [
            'ranch_search_val',
            'ranch_search_city', 
            'ranch_search_id',
            'ranch_search_prefix',
            'search-member-location'
        ]
        
        missing_fields = []
        
        for field_id in required_fields:
            try:
                element = await page.query_selector(f'#{field_id}')
                if not element:
                    missing_fields.append(field_id)
            except Exception:
                missing_fields.append(field_id)
        
        return len(missing_fields) == 0, missing_fields
    
    async def get_search_button_info(self, page: Page) -> Dict[str, str]:
        """
        Detect search button and its trigger method
        
        Args:
            page: Playwright page object
            
        Returns:
            Dictionary with button info
        """
        try:
            button_info = await page.evaluate("""
                () => {
                    // Look for buttons with onclick containing doSearch_Ranch
                    const buttons = document.querySelectorAll('input[type="button"], button');
                    let searchButton = null;
                    let triggerMethod = null;
                    
                    for (const button of buttons) {
                        const onclick = button.getAttribute('onclick') || '';
                        const value = button.value || button.textContent || '';
                        
                        if (onclick.includes('doSearch_Ranch') || 
                            value.toLowerCase().includes('search')) {
                            searchButton = {
                                selector: button.tagName.toLowerCase() + 
                                    (button.id ? `#${button.id}` : '') +
                                    (button.name ? `[name="${button.name}"]` : '') +
                                    (button.value ? `[value="${button.value}"]` : ''),
                                onclick: onclick,
                                value: value
                            };
                            break;
                        }
                    }
                    
                    // Check if doSearch_Ranch function exists
                    const hasFunction = typeof doSearch_Ranch === 'function';
                    
                    return {
                        button: searchButton,
                        hasFunction: hasFunction,
                        triggerMethod: hasFunction ? 'function' : 'button'
                    };
                }
            """)
            
            return button_info
        except Exception as e:
            print(f"Error detecting search button: {e}")
            return {}
    
    async def map_location_input(self, page: Page, user_input: str) -> Optional[str]:
        """
        Dynamically map user location input to dropdown value
        
        Args:
            page: Playwright page object
            user_input: User's location input (e.g., "Texas", "TX")
            
        Returns:
            Matched dropdown value or None
        """
        options = await self.get_dropdown_options(page, 'search-member-location')
        
        if not options:
            return None
        
        # Normalize user input
        user_input = user_input.strip().upper()
        
        # Try exact value match first
        for option in options:
            if option['value'].strip().upper() == user_input:
                return option['value']
        
        # Try partial text match
        for option in options:
            option_text = option['text'].upper()
            if user_input in option_text or option_text in user_input:
                return option['value']
        
        # Try state code extraction
        if '|' in user_input:
            country, state = user_input.split('|', 1)
            state = state.strip()
            for option in options:
                if state in option['value']:
                    return option['value']
        
        return None
    
    async def get_form_structure(self, page: Page) -> Dict[str, any]:
        """
        Get complete form structure information
        
        Args:
            page: Playwright page object
            
        Returns:
            Dictionary with form structure info
        """
        try:
            structure = await page.evaluate("""
                () => {
                    const form = document.querySelector('form') || document;
                    const inputs = form.querySelectorAll('input, select, textarea');
                    const structure = {
                        fields: {},
                        dropdowns: {},
                        buttons: {}
                    };
                    
                    inputs.forEach(input => {
                        const id = input.id;
                        const name = input.name;
                        const type = input.type || input.tagName.toLowerCase();
                        const value = input.value;
                        
                        if (id) {
                            structure.fields[id] = {
                                type: type,
                                name: name || id,
                                value: value,
                                required: input.hasAttribute('required'),
                                placeholder: input.placeholder || ''
                            };
                            
                            // Special handling for dropdowns
                            if (type === 'select-one') {
                                const options = Array.from(input.options).map(opt => ({
                                    value: opt.value,
                                    text: opt.text.trim()
                                }));
                                structure.dropdowns[id] = options;
                            }
                        }
                    });
                    
                    // Find buttons
                    const buttons = form.querySelectorAll('input[type="button"], button');
                    buttons.forEach(button => {
                        const id = button.id;
                        const name = button.name;
                        const value = button.value || button.textContent;
                        const onclick = button.getAttribute('onclick') || '';
                        
                        if (id || name) {
                            structure.buttons[id || name] = {
                                value: value,
                                onclick: onclick,
                                type: button.type || 'button'
                            };
                        }
                    });
                    
                    return structure;
                }
            """)
            
            return structure
        except Exception as e:
            print(f"Error getting form structure: {e}")
            return {}
    
    def normalize_input(self, text: str) -> str:
        """
        Normalize user input for comparison
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Remove extra whitespace and convert to uppercase
        normalized = re.sub(r'\s+', ' ', text.strip()).upper()
        
        # Common abbreviations
        abbreviations = {
            'TX': 'TEXAS',
            'CA': 'CALIFORNIA',
            'NY': 'NEW YORK',
            'FL': 'FLORIDA',
            'IL': 'ILLINOIS',
            'PA': 'PENNSYLVANIA',
            'OH': 'OHIO',
            'GA': 'GEORGIA',
            'NC': 'NORTH CAROLINA',
            'MI': 'MICHIGAN'
        }
        
        return abbreviations.get(normalized, normalized) 