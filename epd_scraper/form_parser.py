import asyncio
from typing import Dict, List, Any, Optional, Tuple
from playwright.async_api import Page

class EPDFormParser:

    def __init__(self):
        self.epd_fields = {'CE Direct': {'min': 'minced', 'max': 'maxced', 'acc': 'mincedacc', 'sort': 'epd_ce'}, 'Birth Weight': {'min': 'minbwt', 'max': 'maxbwt', 'acc': 'minbwtacc', 'sort': 'epd_bw'}, 'Weaning Weight': {'min': 'minwwt', 'max': 'maxwwt', 'acc': 'minwwtacc', 'sort': 'epd_ww'}, 'Yearling Weight': {'min': 'minywt', 'max': 'maxywt', 'acc': 'minywtacc', 'sort': 'epd_yw'}, 'Milk': {'min': 'minmilk', 'max': 'maxmilk', 'acc': 'minmilkacc', 'sort': 'epd_milk'}, 'CE Maternal': {'min': 'mincem', 'max': 'maxcem', 'acc': 'mincemacc', 'sort': 'epd_cem'}, 'Stayability': {'min': 'minst', 'max': 'maxst', 'acc': 'minstacc', 'sort': 'epd_stay'}, 'Yield Grade': {'min': 'minyg', 'max': 'maxyg', 'acc': 'minygacc', 'sort': 'epd_yg'}, 'Carcass Weight': {'min': 'mincw', 'max': 'maxcw', 'acc': 'mincwacc', 'sort': 'epd_cw'}, 'Ribeye Area': {'min': 'minrea', 'max': 'maxrea', 'acc': 'minreaacc', 'sort': 'epd_rea'}, 'Fat Thickness': {'min': 'minft', 'max': 'maxft', 'acc': 'minftacc', 'sort': 'epd_bf'}, 'Marbling': {'min': 'minmarb', 'max': 'maxmarb', 'acc': 'minmarbacc', 'sort': 'epd_ms'}, '$CEZ': {'min': 'mincez', 'max': 'maxcez', 'acc': None, 'sort': 'cez_index'}, '$BMI': {'min': 'minbmi', 'max': 'maxbmi', 'acc': None, 'sort': 'bmi_index'}, '$CPI': {'min': 'mincpi', 'max': 'maxcpi', 'acc': None, 'sort': 'cpi_index'}, '$F': {'min': 'minf', 'max': 'maxf', 'acc': None, 'sort': 'f_index'}}

    async def get_form_structure(self, page: Page) -> Dict[str, Any]:
        try:
            await page.wait_for_selector('#epd_search', timeout=10000)
            form_data = await page.evaluate("\n                () => {\n                    const form = document.querySelector('#epd_search');\n                    if (!form) return {};\n                    \n                    const fields = {};\n                    const inputs = form.querySelectorAll('input');\n                    \n                    for (const input of inputs) {\n                        if (input.type === 'hidden') {\n                            fields[input.name] = input.value;\n                        } else if (input.type === 'text') {\n                            fields[input.name] = {\n                                type: 'text',\n                                value: input.value,\n                                maxlength: input.maxLength,\n                                size: input.size\n                            };\n                        } else if (input.type === 'radio') {\n                            if (!fields[input.name]) {\n                                fields[input.name] = [];\n                            }\n                            fields[input.name].push({\n                                type: 'radio',\n                                value: input.value,\n                                checked: input.checked\n                            });\n                        }\n                    }\n                    \n                    return fields;\n                }\n            ")
            return {'form_id': 'epd_search', 'fields': form_data, 'epd_traits': list(self.epd_fields.keys())}
        except Exception as e:
            print(f'Error getting EPD form structure: {e}')
            return {}

    async def validate_required_fields(self, page: Page) -> Tuple[bool, List[str]]:
        try:
            required_selectors = ['#epd_search', 'input[name="search_sex"]']
            missing_fields = []
            for selector in required_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                except:
                    missing_fields.append(selector)
            try:
                await page.wait_for_selector('input[name="btnsubmit"][value="Search..."]', timeout=5000)
            except:
                missing_fields.append('Search button')
            has_epd_fields = await page.evaluate('\n                () => {\n                    const form = document.querySelector(\'#epd_search\');\n                    if (!form) return false;\n                    \n                    const epdInputs = form.querySelectorAll(\'input[name*="min"], input[name*="max"]\');\n                    return epdInputs.length > 0;\n                }\n            ')
            if not has_epd_fields:
                missing_fields.append('EPD trait fields')
            return (len(missing_fields) == 0, missing_fields)
        except Exception as e:
            print(f'Error validating EPD form: {e}')
            return (False, [str(e)])

    def get_epd_traits(self) -> List[str]:
        return list(self.epd_fields.keys())

    def get_trait_fields(self, trait_name: str) -> Dict[str, str]:
        return self.epd_fields.get(trait_name, {})

    async def fill_epd_form(self, page: Page, search_params: Dict[str, str]) -> bool:
        try:
            await page.evaluate('\n                () => {\n                    const form = document.querySelector(\'#epd_search\');\n                    if (form) {\n                        let searchTypeInput = form.querySelector(\'input[name="search_type"]\');\n                        if (!searchTypeInput) {\n                            searchTypeInput = document.createElement(\'input\');\n                            searchTypeInput.type = \'hidden\';\n                            searchTypeInput.name = \'search_type\';\n                            searchTypeInput.value = \'21\';\n                            form.appendChild(searchTypeInput);\n                        }\n                    }\n                }\n            ')
            for trait_name, trait_fields in self.epd_fields.items():
                trait_key = trait_name.lower().replace(' ', '_').replace('$', '')
                if f'{trait_key}_min' in search_params:
                    min_field = trait_fields['min']
                    if min_field:
                        await page.fill(f'#{min_field}', search_params[f'{trait_key}_min'])
                if f'{trait_key}_max' in search_params:
                    max_field = trait_fields['max']
                    if max_field:
                        await page.fill(f'#{max_field}', search_params[f'{trait_key}_max'])
                if f'{trait_key}_acc' in search_params and trait_fields['acc']:
                    acc_field = trait_fields['acc']
                    await page.fill(f'#{acc_field}', search_params[f'{trait_key}_acc'])
            if 'sort_field' in search_params:
                sort_value = search_params['sort_field']
                await page.click(f'input[name="sort_fld"][value="{sort_value}"]')
            if 'search_sex' in search_params:
                sex_value = search_params['search_sex']
                await page.click(f'input[name="search_sex"][value="{sex_value}"]')
            return True
        except Exception as e:
            print(f'Error filling EPD form: {e}')
            return False
