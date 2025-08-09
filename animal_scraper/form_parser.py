from typing import Dict, Any, Tuple, List
from playwright.async_api import Page

class AnimalFormParser:

    def __init__(self):
        # Known field ids/names from the provided HTML snippet
        self.search_sex_name = 'animal_search_sex'
        self.search_field_name = 'animal_search_fld'
        self.search_value_id = 'animal_search_val'
        self.submit_button_id = 'btnAnimalSubmit'

        # Radio values
        self.sex_values = {'Bulls': 'B', 'Females': 'C', 'Both': ''}
        self.field_values = {
            'Reg #': 'animal_registration',
            'Tattoo': 'animal_private_herd_id',
            'Name': 'animal_name',
            'EID': 'eid',
        }

    async def validate_required_fields(self, page: Page) -> Tuple[bool, List[str]]:
        missing: List[str] = []
        try:
            # container exists
            await page.wait_for_selector('#tbl_animal_search', timeout=10000)
        except Exception:
            missing.append('#tbl_animal_search')
        try:
            await page.wait_for_selector(f'input[name="{self.search_sex_name}"]', timeout=5000)
        except Exception:
            missing.append(self.search_sex_name)
        try:
            await page.wait_for_selector(f'input[name="{self.search_field_name}"]', timeout=5000)
        except Exception:
            missing.append(self.search_field_name)
        try:
            await page.wait_for_selector(f'#{self.search_value_id}', timeout=5000)
        except Exception:
            missing.append(self.search_value_id)
        try:
            await page.wait_for_selector(f'#{self.submit_button_id}', timeout=5000)
        except Exception:
            missing.append(self.submit_button_id)
        return (len(missing) == 0, missing)

    async def ensure_form_defaults(self, page: Page) -> None:
        # Keep defaults as per snippet: Both sex checked, Reg# field checked
        try:
            await page.evaluate(
                f"""
                () => {{
                    const both = document.querySelector('input[name="{self.search_sex_name}"][value=""]');
                    if (both) both.checked = true;
                    const reg = document.querySelector('input[name="{self.search_field_name}"][value="animal_registration"]');
                    if (reg) reg.checked = true;
                }}
                """
            )
        except Exception:
            pass

    async def fill_form(self, page: Page, params: Dict[str, str]) -> bool:
        try:
            sex = params.get('sex', '')  # 'B', 'C', or ''
            field = params.get('field', 'animal_registration')
            value = params.get('value', '')

            if sex in ['B', 'C', '']:
                await page.click(f'input[name="{self.search_sex_name}"][value="{sex}"]')
            if field:
                await page.click(f'input[name="{self.search_field_name}"][value="{field}"]')
            if value is not None:
                await page.fill(f'#{self.search_value_id}', value)
            return True
        except Exception as e:
            print(f'Error filling Animal form: {e}')
            return False

    async def trigger_search(self, page: Page) -> bool:
        try:
            # Prefer JS function if present, else click button
            has_func = await page.evaluate('typeof doSearch_Animal === "function"')
            if has_func:
                await page.evaluate("doSearch_Animal('');")
                return True
            await page.click(f'#{self.submit_button_id}')
            return True
        except Exception as e:
            print(f'Error triggering Animal search: {e}')
            return False 