#!/usr/bin/env python3
"""
Interactive Prompt Module for Ranch Scraper
Handles user input collection with dynamic form validation
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from playwright.async_api import Page
from .form_parser import FormParser
from .utils import normalize_string, validate_search_params


class InteractivePrompt:
    """Interactive prompt handler with dynamic form validation"""
    
    def __init__(self):
        self.form_parser = FormParser()
        self.field_mappings = {
            'name': 'ranch_search_val',
            'city': 'ranch_search_city',
            'member_id': 'ranch_search_id',
            'prefix': 'ranch_search_prefix',
            'location': 'search-member-location'
        }
    
    async def get_available_dropdown_options(self, page: Page, field_id: str) -> List[Dict[str, str]]:
        """
        Get available dropdown options for a specific field
        
        Args:
            page: Playwright page object
            field_id: ID of the dropdown field
            
        Returns:
            List of dictionaries with 'value' and 'text' keys
        """
        return await self.form_parser.get_dropdown_options(page, field_id)
    
    async def validate_location_input(self, page: Page, user_input: str) -> Tuple[bool, Optional[str]]:
        """
        Validate location input against available dropdown options
        
        Args:
            page: Playwright page object
            user_input: User's location input
            
        Returns:
            Tuple of (is_valid, mapped_value)
        """
        if not user_input.strip():
            return True, None
        
        mapped_value = await self.form_parser.map_location_input(page, user_input)
        if mapped_value:
            return True, mapped_value
        else:
            return False, None
    
    async def prompt_for_field(self, field_name: str, field_id: str, page: Page = None) -> Optional[str]:
        """
        Prompt user for a specific field with validation
        
        Args:
            field_name: Human-readable field name
            field_id: Form field ID
            page: Playwright page object (for validation)
            
        Returns:
            User input or None if skipped
        """
        # Show available options for dropdowns
        if field_id == 'search-member-location' and page:
            options = await self.get_available_dropdown_options(page, field_id)
            if options:
                print(f"\nAvailable locations ({len(options)} total):")
                for i, option in enumerate(options[:10], 1):  # Show first 10
                    print(f"  {i}. {option['text']}")
                if len(options) > 10:
                    print(f"  ... and {len(options) - 10} more")
                print("  (You can enter location name, state code, or number from list)")
        
        # Get user input
        user_input = input(f"{field_name.title()}: ").strip()
        
        if not user_input:
            return None
        
        # Handle location input with number selection
        if field_id == 'search-member-location' and page:
            # Check if user entered a number
            try:
                location_num = int(user_input)
                if 1 <= location_num <= len(options):
                    selected_option = options[location_num - 1]
                    print(f"✓ Selected: {selected_option['text']} ({selected_option['value']})")
                    return selected_option['value']
                else:
                    print(f"⚠️  Warning: Number {location_num} is out of range (1-{len(options)})")
                    retry = input("Try again? (y/n): ").strip().lower()
                    if retry == 'y':
                        return await self.prompt_for_field(field_name, field_id, page)
                    else:
                        return None
            except ValueError:
                # Not a number, try text matching
                is_valid, mapped_value = await self.validate_location_input(page, user_input)
                if not is_valid:
                    print(f"⚠️  Warning: '{user_input}' not found in available locations")
                    retry = input("Try again? (y/n): ").strip().lower()
                    if retry == 'y':
                        return await self.prompt_for_field(field_name, field_id, page)
                    else:
                        return None
                elif mapped_value:
                    print(f"✓ Selected: {mapped_value}")
                    return mapped_value
        
        return user_input.upper() if field_id != 'search-member-location' else user_input
    
    async def collect_user_input(self, page: Page) -> Dict[str, str]:
        """
        Collect user input interactively with dynamic validation
        
        Args:
            page: Playwright page object for form validation
            
        Returns:
            Dictionary of search parameters
        """
        print("=== Ranch Scraper Interactive Mode ===")
        print("Enter search parameters (press Enter to skip):")
        print()
        
        params = {}
        
        # Collect input for each field
        fields = [
            ('ranch name', 'ranch_search_val'),
            ('city', 'ranch_search_city'),
            ('member ID', 'ranch_search_id'),
            ('herd prefix', 'ranch_search_prefix'),
            ('location', 'search-member-location')
        ]
        
        for field_name, field_id in fields:
            value = await self.prompt_for_field(field_name, field_id, page)
            if value:
                # Map field ID to parameter name
                param_name = next(k for k, v in self.field_mappings.items() if v == field_id)
                params[param_name] = value
        
        return params
    
    async def prompt_for_export(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Prompt user for export preferences
        
        Returns:
            Tuple of (export_format, filename)
        """
        print("\n=== Export Options ===")
        
        while True:
            export_choice = input("Export results to CSV, JSON, or skip? (csv/json/none): ").strip().lower()
            
            if export_choice in ['csv', 'json']:
                filename = input("Output filename (optional, press Enter for auto-generated): ").strip()
                if not filename:
                    filename = None
                return export_choice, filename
            elif export_choice in ['none', 'skip']:
                return None, None
            else:
                print("Invalid choice. Please enter 'csv', 'json', or 'none'.")
    
    def validate_collected_params(self, params: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Validate collected parameters
        
        Args:
            params: Collected search parameters
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return validate_search_params(params)
    
    async def run_interactive_mode(self, page: Page) -> Tuple[Dict[str, str], Optional[str], Optional[str]]:
        """
        Run complete interactive mode
        
        Args:
            page: Playwright page object
            
        Returns:
            Tuple of (search_params, export_format, filename)
        """
        # Collect search parameters
        params = await self.collect_user_input(page)
        
        # Validate parameters
        is_valid, errors = self.validate_collected_params(params)
        if not is_valid:
            print("\nValidation errors:")
            for error in errors:
                print(f"  - {error}")
            return {}, None, None
        
        if not params:
            print("\nNo search parameters provided. Exiting.")
            return {}, None, None
        
        # Collect export preferences
        export_format, filename = await self.prompt_for_export()
        
        return params, export_format, filename 