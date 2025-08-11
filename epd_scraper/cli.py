import asyncio
from typing import Dict, List, Optional, Set
from playwright.async_api import Page
from .scraper import EPDSearchScraper
from ranch_scraper.exporter import DynamicExporter

# semantic imports
from nlp.query_parser import classify_intent, parse_query_for_epd
from nlp.summarizer import summarize_epd_results

class EPDSearchCLI:

    def __init__(self):
        self.scraper = EPDSearchScraper()
        self.exporter = DynamicExporter()

    def _print_numbered_list(self, items: List[str]):
        for i, item in enumerate(items, 1):
            print(f'{i:2d}. {item}')

    def _parse_selection_tokens(self, token_str: str, traits: List[str]) -> Set[int]:
        selections: Set[int] = set()
        tokens = [t.strip() for t in token_str.split(',') if t.strip()]
        trait_upper = [t.upper() for t in traits]
        for token in tokens:
            if token.lower() in ['a', 'all']:
                selections.update(range(1, len(traits) + 1))
                continue
            if '-' in token:
                try:
                    start, end = token.split('-', 1)
                    start_i = int(start)
                    end_i = int(end)
                    if start_i <= end_i:
                        for i in range(start_i, end_i + 1):
                            if 1 <= i <= len(traits):
                                selections.add(i)
                except ValueError:
                    # Ignore invalid range, try substring matching instead
                    pass
                continue
            # Try numeric index
            try:
                idx = int(token)
                if 1 <= idx <= len(traits):
                    selections.add(idx)
                    continue
            except ValueError:
                pass
            # Try substring match
            token_up = token.upper()
            for i, name_up in enumerate(trait_upper, 1):
                if token_up in name_up:
                    selections.add(i)
        return selections

    def _prompt_trait_selection(self, traits: List[str]) -> List[str]:
        print('Available EPD traits:')
        self._print_numbered_list(traits)
        print('\nTips:')
        print("- Enter numbers or ranges (e.g., '1,3-5,12')")
        print("- Or type parts of names (e.g., 'weight, milk')")
        print("- Use 'all' to select all, or press Enter to skip")
        raw = input('\nChoose traits to filter (optional): ').strip()
        if not raw:
            return []
        selected_indexes = self._parse_selection_tokens(raw, traits)
        if not selected_indexes:
            print('No valid selection detected. Skipping trait filters.')
            return []
        selected_sorted = sorted(selected_indexes)
        chosen = [traits[i - 1] for i in selected_sorted]
        print('\nSelected traits:')
        for name in chosen:
            print(f'- {name}')
        return chosen

    async def collect_epd_parameters(self, page: Page) -> Dict[str, str]:
        print('=== EPD Search Interactive Mode ===')
        print('Enter EPD search parameters (press Enter to skip).')
        print()
        params: Dict[str, str] = {}
        traits = self.scraper.form_parser.get_epd_traits()

        # Step 1: choose which traits to fill
        chosen_traits = self._prompt_trait_selection(traits)

        # Step 2: prompt only for chosen traits
        for trait in chosen_traits:
            trait_key = trait.lower().replace(' ', '_').replace('$', '')
            print(f'\n--- {trait} ---')
            min_val = input(f'Minimum {trait} (Press Enter to skip): ').strip()
            if min_val:
                params[f'{trait_key}_min'] = min_val
            max_val = input(f'Maksimum {trait} (Press Enter to skip): ').strip()
            if max_val:
                params[f'{trait_key}_max'] = max_val
            trait_fields = self.scraper.form_parser.get_trait_fields(trait)
            if trait_fields.get('acc'):
                acc_val = input(f'Akurasi minimum untuk {trait} (Press Enter to skip): ').strip()
                if acc_val:
                    params[f'{trait_key}_acc'] = acc_val

        # Step 3: sort option (choice list)
        print('\n--- Sort Options ---')
        sort_options: List[tuple] = []
        for trait in traits:
            trait_fields = self.scraper.form_parser.get_trait_fields(trait)
            sort_value = trait_fields.get('sort')
            if sort_value:
                sort_options.append((trait, sort_value))
        default_sort = 'epd_ww'
        print('Available sort fields:')
        for i, (label, value) in enumerate(sort_options, 1):
            default_marker = ' (default)' if value == default_sort else ''
            print(f'{i:2d}. {label} -> {value}{default_marker}')
        sort_raw = input("Choose sort number (or type value), press Enter for default 'epd_ww': ").strip()
        if not sort_raw:
            params['sort_field'] = default_sort
        else:
            try:
                sort_idx = int(sort_raw)
                if 1 <= sort_idx <= len(sort_options):
                    params['sort_field'] = sort_options[sort_idx - 1][1]
                else:
                    print('Sort number out of range. Using default.')
                    params['sort_field'] = default_sort
            except ValueError:
                # assume user typed value
                params['sort_field'] = sort_raw

        # Step 4: sex filter
        print('\n--- Sex Filter ---')
        print('1. Bulls (B)')
        print('2. Females (C)')
        print('3. Both (default)')
        sex_choice = input('Enter choice (1-3, press Enter for Both): ').strip()
        if sex_choice == '1':
            params['search_sex'] = 'B'
        elif sex_choice == '2':
            params['search_sex'] = 'C'
        else:
            params['search_sex'] = ''
        return params

    async def main_with_page(self, page: Page):
        try:
            if not await self.scraper.wait_for_epd_form_ready(page):
                print('Failed to load EPD search form')
                return
            # semantic quick entry: let users type a query
            try:
                use_quick = input('Type a search in your own words? (y/N): ').strip().lower() == 'y'
            except Exception:
                use_quick = False
            params: Dict[str, str] = {}
            if use_quick:
                q = input('Describe what you’re looking for: ').strip()
                if q:
                    intent = classify_intent(q)
                    if intent != 'epd':
                        pass
                    params = parse_query_for_epd(q)
                    print('Okay, I’ll search for:')
                    for k, v in params.items():
                        print(f'  - {k}: {v}')
            if not params:
                params = await self.collect_epd_parameters(page)
            if not params:
                print('No search parameters provided. Exiting.')
                return
            results = await self.scraper.scrape_epd(params)
            if not results:
                print('No EPD results found')
                return
            print('\nHow would you like to display the results?')
            print('1. Detailed format (organized by categories)')
            print('2. Table format (simple table)')
            format_choice = input('\nEnter your choice (1-2, default 1): ').strip()
            if format_choice == '2':
                formatted_results = self.scraper.format_results_table(results)
            else:
                formatted_results = self.scraper.format_results(results)
            print('\n' + formatted_results)
            # summary option
            try:
                if input('Show summary? (y/N): ').strip().lower() == 'y':
                    print('\nSummary:')
                    print(summarize_epd_results(results))
            except Exception:
                pass
            await self._show_follow_up_menu(page, results)
        except Exception as e:
            print(f'Error in EPD scraper: {e}')

    async def _show_follow_up_menu(self, page: Page, data: List[Dict[str, str]]):
        while True:
            print('\nWhat would you like to do next?')
            print('1. Export results to CSV')
            print('2. Export results to JSON')
            print('3. View animal details')
            print('4. New search')
            print('5. Return to main menu')
            try:
                choice = input('\nEnter your choice (1-5): ').strip()
                if choice == '1':
                    filename = input("Enter CSV filename (or press Enter for 'epd_results.csv'): ").strip()
                    if not filename:
                        filename = 'epd_results.csv'
                    exported_file = self.exporter.export_to_csv(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                elif choice == '2':
                    filename = input("Enter JSON filename (or press Enter for 'epd_results.json'): ").strip()
                    if not filename:
                        filename = 'epd_results.json'
                    exported_file = self.exporter.export_to_json(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                elif choice == '3':
                    updated = await self._view_animal_details(page, data)
                    if isinstance(updated, list) and updated:
                        data = updated
                        print('\n' + self.scraper.format_results_table(data))
                elif choice == '4':
                    # Run a new EPD search in-place
                    if not await self.scraper.wait_for_epd_form_ready(page):
                        print('Failed to load EPD search form')
                        continue
                    params = await self.collect_epd_parameters(page)
                    if not params:
                        print('No search parameters provided.')
                        continue
                    new_results = await self.scraper.scrape_epd(params)
                    if not new_results:
                        print('No EPD results found')
                        continue
                    data = new_results
                    print('\n' + self.scraper.format_results_table(data))
                elif choice == '5':
                    print('Returning to main menu...')
                    break
                else:
                    print('Invalid choice. Please enter 1, 2, 3, 4, or 5.')
            except KeyboardInterrupt:
                print('\nOperation cancelled.')
                break
            except Exception as e:
                print(f'Error: {e}')
                # keep looping

    async def _view_animal_details(self, page: Page, data: List[Dict[str, str]]):
        if not data:
            print('No data available for viewing details.')
            return data
        print(f'\nFound {len(data)} animals. Which one would you like to view details for?')
        for i, animal in enumerate(data, 1):
            registration = animal.get('registration', 'Unknown')
            name = animal.get('name', 'Unknown')
            print(f'{i}. {registration} - {name}')
        print(f'{len(data) + 1}. View all animals details')
        print(f'{len(data) + 2}. Cancel')
        try:
            choice = input(f'\nEnter your choice (1-{len(data) + 2}): ').strip()
            if not choice.isdigit():
                print('Invalid input. Please enter a number.')
                return data
            choice_num = int(choice)
            if choice_num == len(data) + 1:
                return await self._view_all_animal_details(page, data)
            elif choice_num == len(data) + 2:
                print('Cancelled.')
                return data
            elif 1 <= choice_num <= len(data):
                selected_index = choice_num - 1
                selected_animal = data[selected_index]
                registration_url = selected_animal.get('registration_url')
                if not registration_url:
                    print('No detail URL available for this animal.')
                    return data
                print(f"\nFetching details for {selected_animal.get('registration', 'Unknown')}...")
                try:
                    self.scraper.browser, self.scraper.playwright = await self.scraper.init_browser()
                    detail_page = await self.scraper.browser.new_page()
                    details = await self.scraper.extract_animal_detail(detail_page, registration_url)
                    if details:
                        formatted_details = self.scraper.format_animal_detail(details)
                        print('\n' + formatted_details)
                        updated = selected_animal.copy()
                        updated.update(details)
                        new_data = data.copy()
                        new_data[selected_index] = updated
                        return new_data
                    else:
                        print('Failed to extract animal details.')
                        return data
                except Exception as e:
                    print(f'Error viewing animal details: {e}')
                    return data
                finally:
                    if self.scraper.browser:
                        try:
                            await self.scraper.browser.close()
                        except Exception:
                            pass
                    if self.scraper.playwright:
                        try:
                            await self.scraper.playwright.stop()
                        except Exception:
                            pass
            else:
                print('Invalid choice.')
                return data
        except KeyboardInterrupt:
            print('\nOperation cancelled.')
            return data
        except Exception as e:
            print(f'Error: {e}')
            return data

    async def _view_all_animal_details(self, page: Page, data: List[Dict[str, str]]):
        print(f'\nFetching details for all {len(data)} animals...')
        try:
            self.scraper.browser, self.scraper.playwright = await self.scraper.init_browser()
            detail_page = await self.scraper.browser.new_page()
            all_details = []
            for i, animal in enumerate(data, 1):
                registration_url = animal.get('registration_url')
                if not registration_url:
                    print(f"Skipping {animal.get('registration', 'Unknown')} - no URL available")
                    all_details.append(animal)
                    continue
                print(f"Processing {i}/{len(data)}: {animal.get('registration', 'Unknown')}")
                try:
                    details = await self.scraper.extract_animal_detail(detail_page, registration_url)
                    merged_data = animal.copy()
                    merged_data.update(details)
                    all_details.append(merged_data)
                except Exception as e:
                    print(f"Error processing {animal.get('registration', 'Unknown')}: {e}")
                    all_details.append(animal)
                    continue
            print('\nExtraction complete.')
            print('\n' + self.scraper.format_results_table(all_details))
            await self._show_export_menu(all_details)
            return all_details
        except Exception as e:
            print(f'Error viewing all animal details: {e}')
            return data
        finally:
            if self.scraper.browser:
                try:
                    await self.scraper.browser.close()
                except Exception:
                    pass
            if self.scraper.playwright:
                try:
                    await self.scraper.playwright.stop()
                except Exception:
                    pass

    async def _show_export_menu(self, data: List[Dict[str, str]]):
        while True:
            print('\nWould you like to export the detailed results?')
            print('1. Export to CSV')
            print('2. Export to JSON')
            print('3. Skip export')
            try:
                choice = input('\nEnter your choice (1-3): ').strip()
                if choice == '1':
                    filename = input("Enter CSV filename (or press Enter for 'epd_detailed_results.csv'): ").strip()
                    if not filename:
                        filename = 'epd_detailed_results.csv'
                    exported_file = self.exporter.export_to_csv(data, filename)
                    if exported_file:
                        print(f'Detailed results exported to: {exported_file}')
                    break
                elif choice == '2':
                    filename = input("Enter JSON filename (or press Enter for 'epd_detailed_results.json'): ").strip()
                    if not filename:
                        filename = 'epd_detailed_results.json'
                    exported_file = self.exporter.export_to_json(data, filename)
                    if exported_file:
                        print(f'Detailed results exported to: {exported_file}')
                    break
                elif choice == '3':
                    print('Skipping export.')
                    break
                else:
                    print('Invalid choice. Please enter 1, 2, or 3.')
            except KeyboardInterrupt:
                print('\nOperation cancelled.')
                break
            except Exception as e:
                print(f'Error: {e}')
                break

async def main():
    cli = EPDSearchCLI()
    await cli.main()
if __name__ == '__main__':
    asyncio.run(main())
