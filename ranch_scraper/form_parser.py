from typing import List, Dict, Optional, Tuple
from playwright.async_api import Page
import re

class FormParser:

    def __init__(self):
        self.field_mappings = {'ranch_search_val': 'name', 'ranch_search_city': 'city', 'ranch_search_id': 'member_id', 'ranch_search_prefix': 'prefix', 'search-member-location': 'location'}

    async def get_dropdown_options(self, page: Page, select_id: str) -> List[Dict[str, str]]:
        try:
            options = await page.evaluate(f"\n                () => {{\n                    const select = document.querySelector('#{select_id}');\n                    if (!select) return [];\n                    \n                    const options = Array.from(select.options);\n                    return options.map(option => ({{\n                        value: option.value,\n                        text: option.text.trim()\n                    }})).filter(option => option.value && option.value.trim() !== '|');\n                }}\n            ")
            return options
        except Exception as e:
            print(f'Error extracting dropdown options for {select_id}: {e}')
            return []

    async def find_input_fields(self, page: Page) -> Dict[str, str]:
        try:
            fields = await page.evaluate("\n                () => {\n                    const inputs = document.querySelectorAll('input, select, textarea');\n                    const fields = {};\n                    \n                    inputs.forEach(input => {\n                        const id = input.id;\n                        const name = input.name;\n                        const type = input.type || input.tagName.toLowerCase();\n                        \n                        if (id) {\n                            fields[id] = {\n                                selector: `#${id}`,\n                                type: type,\n                                name: name || id\n                            };\n                        }\n                    });\n                    \n                    return fields;\n                }\n            ")
            return fields
        except Exception as e:
            print(f'Error finding input fields: {e}')
            return {}

    async def validate_required_fields(self, page: Page) -> Tuple[bool, List[str]]:
        required_fields = ['ranch_search_val', 'ranch_search_city', 'ranch_search_id', 'ranch_search_prefix', 'search-member-location']
        missing_fields = []
        for field_id in required_fields:
            try:
                element = await page.query_selector(f'#{field_id}')
                if not element:
                    missing_fields.append(field_id)
            except Exception:
                missing_fields.append(field_id)
        return (len(missing_fields) == 0, missing_fields)

    async def get_search_button_info(self, page: Page) -> Dict[str, str]:
        try:
            button_info = await page.evaluate('\n                () => {\n                    // Look for buttons with onclick containing doSearch_Ranch\n                    const buttons = document.querySelectorAll(\'input[type="button"], button\');\n                    let searchButton = null;\n                    let triggerMethod = null;\n                    \n                    for (const button of buttons) {\n                        const onclick = button.getAttribute(\'onclick\') || \'\';\n                        const value = button.value || button.textContent || \'\';\n                        \n                        if (onclick.includes(\'doSearch_Ranch\') || \n                            value.toLowerCase().includes(\'search\')) {\n                            searchButton = {\n                                selector: button.tagName.toLowerCase() + \n                                    (button.id ? `#${button.id}` : \'\') +\n                                    (button.name ? `[name="${button.name}"]` : \'\') +\n                                    (button.value ? `[value="${button.value}"]` : \'\'),\n                                onclick: onclick,\n                                value: value\n                            };\n                            break;\n                        }\n                    }\n                    \n                    // Check if doSearch_Ranch function exists\n                    const hasFunction = typeof doSearch_Ranch === \'function\';\n                    \n                    return {\n                        button: searchButton,\n                        hasFunction: hasFunction,\n                        triggerMethod: hasFunction ? \'function\' : \'button\'\n                    };\n                }\n            ')
            return button_info
        except Exception as e:
            print(f'Error detecting search button: {e}')
            return {}

    async def map_location_input(self, page: Page, user_input: str) -> Optional[str]:
        options = await self.get_dropdown_options(page, 'search-member-location')
        if not options:
            return None
        user_input = user_input.strip().upper()
        valid_options = [opt for opt in options if opt['value'].strip() and opt['value'].strip() != '|']
        for option in valid_options:
            if option['value'].strip().upper() == user_input:
                return option['value']
        for option in valid_options:
            option_text = option['text'].upper()
            if user_input in option_text:
                return option['value']
        for option in valid_options:
            option_value = option['value'].upper()
            if user_input in option_value:
                return option['value']
        for option in valid_options:
            option_text = option['text'].upper()
            if user_input in option_text:
                return option['value']
        return None

    async def get_form_structure(self, page: Page) -> Dict[str, any]:
        try:
            structure = await page.evaluate('\n                () => {\n                    const form = document.querySelector(\'form\') || document;\n                    const inputs = form.querySelectorAll(\'input, select, textarea\');\n                    const structure = {\n                        fields: {},\n                        dropdowns: {},\n                        buttons: {}\n                    };\n                    \n                    inputs.forEach(input => {\n                        const id = input.id;\n                        const name = input.name;\n                        const type = input.type || input.tagName.toLowerCase();\n                        const value = input.value;\n                        \n                        if (id) {\n                            structure.fields[id] = {\n                                type: type,\n                                name: name || id,\n                                value: value,\n                                required: input.hasAttribute(\'required\'),\n                                placeholder: input.placeholder || \'\'\n                            };\n                            \n                            // Special handling for dropdowns\n                            if (type === \'select-one\') {\n                                const options = Array.from(input.options).map(opt => ({\n                                    value: opt.value,\n                                    text: opt.text.trim()\n                                }));\n                                structure.dropdowns[id] = options;\n                            }\n                        }\n                    });\n                    \n                    // Find buttons\n                    const buttons = form.querySelectorAll(\'input[type="button"], button\');\n                    buttons.forEach(button => {\n                        const id = button.id;\n                        const name = button.name;\n                        const value = button.value || button.textContent;\n                        const onclick = button.getAttribute(\'onclick\') || \'\';\n                        \n                        if (id || name) {\n                            structure.buttons[id || name] = {\n                                value: value,\n                                onclick: onclick,\n                                type: button.type || \'button\'\n                            };\n                        }\n                    });\n                    \n                    return structure;\n                }\n            ')
            return structure
        except Exception as e:
            print(f'Error getting form structure: {e}')
            return {}

    def normalize_input(self, text: str) -> str:
        if not text:
            return ''
        normalized = re.sub('\\s+', ' ', text.strip()).upper()
        abbreviations = {'TX': 'TEXAS', 'CA': 'CALIFORNIA', 'NY': 'NEW YORK', 'FL': 'FLORIDA', 'IL': 'ILLINOIS', 'PA': 'PENNSYLVANIA', 'OH': 'OHIO', 'GA': 'GEORGIA', 'NC': 'NORTH CAROLINA', 'MI': 'MICHIGAN'}
        return abbreviations.get(normalized, normalized)
