from typing import Dict, Optional
from playwright.async_api import Page
from .form_parser import FormParser
from .utils import normalize_string

class FormHandler:

    def __init__(self):
        self.form_parser = FormParser()
        self.field_mappings = {'name': 'ranch_search_val', 'city': 'ranch_search_city', 'member_id': 'ranch_search_id', 'prefix': 'ranch_search_prefix', 'location': 'search-member-location'}

    async def validate_form_structure(self, page: Page) -> bool:
        is_valid, missing_fields = await self.form_parser.validate_required_fields(page)
        if not is_valid:
            print(f'Missing required fields: {missing_fields}')
            return False
        return True

    async def fill_text_field(self, page: Page, field_id: str, value: str) -> bool:
        try:
            element = await page.wait_for_selector(f'#{field_id}', timeout=5000)
            await element.fill(value.upper())
            print(f'Filled {field_id}: {value}')
            return True
        except Exception as e:
            print(f'Error filling {field_id}: {e}')
            return False

    async def fill_dropdown_field(self, page: Page, field_id: str, value: str) -> bool:
        try:
            element = await page.wait_for_selector(f'#{field_id}', timeout=5000)
            mapped_value = await self.form_parser.map_location_input(page, value)
            if mapped_value:
                await element.select_option(value=mapped_value)
                print(f'Selected {field_id}: {value} -> {mapped_value}')
                return True
            else:
                print(f"Warning: Could not map '{value}' for {field_id}")
                return False
        except Exception as e:
            print(f'Error filling dropdown {field_id}: {e}')
            return False

    async def fill_form_fields(self, page: Page, params: Dict[str, str]) -> bool:
        success = True
        for param_name, value in params.items():
            if not value:
                continue
            field_id = self.field_mappings.get(param_name)
            if not field_id:
                print(f'Unknown parameter: {param_name}')
                continue
            try:
                if param_name == 'location':
                    if not await self.fill_dropdown_field(page, field_id, value):
                        success = False
                elif not await self.fill_text_field(page, field_id, value):
                    success = False
            except Exception as e:
                print(f'Error processing {param_name}: {e}')
                success = False
        return success

    async def get_form_info(self, page: Page) -> Dict:
        return await self.form_parser.get_form_structure(page)

    async def list_available_options(self, page: Page, field_id: str) -> list:
        return await self.form_parser.get_dropdown_options(page, field_id)

    def normalize_input(self, text: str) -> str:
        return normalize_string(text)
