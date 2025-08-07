#!/usr/bin/env python3
"""
EPD Form Parser
Handles parsing and validation of EPD search form
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from playwright.async_api import Page


class EPDFormParser:
    """Parser for EPD search form structure"""
    
    def __init__(self):
        self.epd_fields = {
            'CE Direct': {
                'min': 'minced',
                'max': 'maxced', 
                'acc': 'mincedacc',
                'sort': 'epd_ce'
            },
            'Birth Weight': {
                'min': 'minbwt',
                'max': 'maxbwt',
                'acc': 'minbwtacc', 
                'sort': 'epd_bw'
            },
            'Weaning Weight': {
                'min': 'minwwt',
                'max': 'maxwwt',
                'acc': 'minwwtacc',
                'sort': 'epd_ww'
            },
            'Yearling Weight': {
                'min': 'minywt',
                'max': 'maxywt',
                'acc': 'minywtacc',
                'sort': 'epd_yw'
            },
            'Milk': {
                'min': 'minmilk',
                'max': 'maxmilk',
                'acc': 'minmilkacc',
                'sort': 'epd_milk'
            },
            'CE Maternal': {
                'min': 'mincem',
                'max': 'maxcem',
                'acc': 'mincemacc',
                'sort': 'epd_cem'
            },
            'Stayability': {
                'min': 'minst',
                'max': 'maxst',
                'acc': 'minstacc',
                'sort': 'epd_stay'
            },
            'Yield Grade': {
                'min': 'minyg',
                'max': 'maxyg',
                'acc': 'minygacc',
                'sort': 'epd_yg'
            },
            'Carcass Weight': {
                'min': 'mincw',
                'max': 'maxcw',
                'acc': 'mincwacc',
                'sort': 'epd_cw'
            },
            'Ribeye Area': {
                'min': 'minrea',
                'max': 'maxrea',
                'acc': 'minreaacc',
                'sort': 'epd_rea'
            },
            'Fat Thickness': {
                'min': 'minft',
                'max': 'maxft',
                'acc': 'minftacc',
                'sort': 'epd_bf'
            },
            'Marbling': {
                'min': 'minmarb',
                'max': 'maxmarb',
                'acc': 'minmarbacc',
                'sort': 'epd_ms'
            },
            '$CEZ': {
                'min': 'mincez',
                'max': 'maxcez',
                'acc': None,
                'sort': 'cez_index'
            },
            '$BMI': {
                'min': 'minbmi',
                'max': 'maxbmi',
                'acc': None,
                'sort': 'bmi_index'
            },
            '$CPI': {
                'min': 'mincpi',
                'max': 'maxcpi',
                'acc': None,
                'sort': 'cpi_index'
            },
            '$F': {
                'min': 'minf',
                'max': 'maxf',
                'acc': None,
                'sort': 'f_index'
            }
        }
    
    async def get_form_structure(self, page: Page) -> Dict[str, Any]:
        """
        Get EPD form structure
        
        Args:
            page: Playwright page object
            
        Returns:
            Dictionary with form structure information
        """
        try:
            # Wait for EPD form to be available
            await page.wait_for_selector('#epd_search', timeout=10000)
            
            # Get form fields
            form_data = await page.evaluate("""
                () => {
                    const form = document.querySelector('#epd_search');
                    if (!form) return {};
                    
                    const fields = {};
                    const inputs = form.querySelectorAll('input');
                    
                    for (const input of inputs) {
                        if (input.type === 'hidden') {
                            fields[input.name] = input.value;
                        } else if (input.type === 'text') {
                            fields[input.name] = {
                                type: 'text',
                                value: input.value,
                                maxlength: input.maxLength,
                                size: input.size
                            };
                        } else if (input.type === 'radio') {
                            if (!fields[input.name]) {
                                fields[input.name] = [];
                            }
                            fields[input.name].push({
                                type: 'radio',
                                value: input.value,
                                checked: input.checked
                            });
                        }
                    }
                    
                    return fields;
                }
            """)
            
            return {
                'form_id': 'epd_search',
                'fields': form_data,
                'epd_traits': list(self.epd_fields.keys())
            }
            
        except Exception as e:
            print(f"Error getting EPD form structure: {e}")
            return {}
    
    async def validate_required_fields(self, page: Page) -> Tuple[bool, List[str]]:
        """
        Validate that EPD form has required fields
        
        Args:
            page: Playwright page object
            
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        try:
            # Check for basic form elements
            required_selectors = [
                '#epd_search',
                'input[name="search_sex"]'
            ]
            
            missing_fields = []
            for selector in required_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                except:
                    missing_fields.append(selector)
            
            # Check for search button
            try:
                await page.wait_for_selector('input[name="btnsubmit"][value="Search..."]', timeout=5000)
            except:
                missing_fields.append('Search button')
            
            # Check for at least one EPD trait field
            has_epd_fields = await page.evaluate("""
                () => {
                    const form = document.querySelector('#epd_search');
                    if (!form) return false;
                    
                    const epdInputs = form.querySelectorAll('input[name*="min"], input[name*="max"]');
                    return epdInputs.length > 0;
                }
            """)
            
            if not has_epd_fields:
                missing_fields.append('EPD trait fields')
            
            return len(missing_fields) == 0, missing_fields
            
        except Exception as e:
            print(f"Error validating EPD form: {e}")
            return False, [str(e)]
    
    def get_epd_traits(self) -> List[str]:
        """
        Get list of available EPD traits
        
        Returns:
            List of EPD trait names
        """
        return list(self.epd_fields.keys())
    
    def get_trait_fields(self, trait_name: str) -> Dict[str, str]:
        """
        Get field names for a specific EPD trait
        
        Args:
            trait_name: Name of the EPD trait
            
        Returns:
            Dictionary with field names for the trait
        """
        return self.epd_fields.get(trait_name, {})
    
    async def fill_epd_form(self, page: Page, search_params: Dict[str, str]) -> bool:
        """
        Fill EPD search form with parameters
        
        Args:
            page: Playwright page object
            search_params: Search parameters to fill
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add hidden search_type field if it doesn't exist
            await page.evaluate("""
                () => {
                    const form = document.querySelector('#epd_search');
                    if (form) {
                        let searchTypeInput = form.querySelector('input[name="search_type"]');
                        if (!searchTypeInput) {
                            searchTypeInput = document.createElement('input');
                            searchTypeInput.type = 'hidden';
                            searchTypeInput.name = 'search_type';
                            searchTypeInput.value = '21';
                            form.appendChild(searchTypeInput);
                        }
                    }
                }
            """)
            
            # Fill EPD trait fields
            for trait_name, trait_fields in self.epd_fields.items():
                trait_key = trait_name.lower().replace(' ', '_').replace('$', '')
                
                # Fill min value
                if f'{trait_key}_min' in search_params:
                    min_field = trait_fields['min']
                    if min_field:
                        await page.fill(f'#{min_field}', search_params[f'{trait_key}_min'])
                
                # Fill max value
                if f'{trait_key}_max' in search_params:
                    max_field = trait_fields['max']
                    if max_field:
                        await page.fill(f'#{max_field}', search_params[f'{trait_key}_max'])
                
                # Fill accuracy value
                if f'{trait_key}_acc' in search_params and trait_fields['acc']:
                    acc_field = trait_fields['acc']
                    await page.fill(f'#{acc_field}', search_params[f'{trait_key}_acc'])
            
            # Set sort field
            if 'sort_field' in search_params:
                sort_value = search_params['sort_field']
                await page.click(f'input[name="sort_fld"][value="{sort_value}"]')
            
            # Set sex filter
            if 'search_sex' in search_params:
                sex_value = search_params['search_sex']
                await page.click(f'input[name="search_sex"][value="{sex_value}"]')
            
            return True
            
        except Exception as e:
            print(f"Error filling EPD form: {e}")
            return False 