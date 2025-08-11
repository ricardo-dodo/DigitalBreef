import asyncio
from typing import Dict, Optional, List
from playwright.async_api import Page
from .scraper import AnimalSearchScraper
from ranch_scraper.exporter import DynamicExporter

# semantic imports
from nlp.query_parser import classify_intent, parse_query_for_animal
from nlp.summarizer import summarize_animal_results

class AnimalSearchCLI:

    def __init__(self):
        self.scraper = AnimalSearchScraper()
        self.exporter = DynamicExporter()

    def _prompt_sex(self) -> str:
        print('\n--- Search For ---')
        print('1. Bulls (B)')
        print('2. Females (C)')
        print('3. Both (default)')
        choice = input('Enter choice (1-3, press Enter for Both): ').strip()
        if choice == '1':
            return 'B'
        if choice == '2':
            return 'C'
        return ''

    def _prompt_field(self) -> str:
        print('\n--- Search Field ---')
        fields = [('Reg #', 'animal_registration'), ('Tattoo', 'animal_private_herd_id'), ('Name', 'animal_name'), ('EID', 'eid')]
        for i, (label, value) in enumerate(fields, 1):
            print(f'{i}. {label}')
        raw = input("Choose field (1-4), press Enter for 'Reg #': ").strip()
        if not raw:
            return 'animal_registration'
        try:
            idx = int(raw)
            if 1 <= idx <= len(fields):
                return fields[idx - 1][1]
        except ValueError:
            pass
        # allow direct value entry
        if raw in [v for _, v in fields]:
            return raw
        print('Invalid choice. Using default Reg #.')
        return 'animal_registration'

    def _prompt_value(self) -> str:
        print('\n--- Search Value ---')
        print('Use an asterisk (*) as a wildcard')
        return input('Value: ').strip()

    async def main_with_page(self, page: Page):
        try:
            # Always navigate to the site to ensure fresh state when re-entering from menu
            if not await self.scraper.navigate_to_site(page):
                print('Failed to load Digital Beef website')
                return
            if not await self.scraper.wait_for_form_ready(page):
                print('Failed to load Animal search form')
                return
            # semantic quick entry
            try:
                use_quick = input('Type a search in your own words? (y/N): ').strip().lower() == 'y'
            except Exception:
                use_quick = False
            params: Dict[str, str] = {}
            if use_quick:
                q = input('Describe what you’re looking for: ').strip()
                if q:
                    intent = classify_intent(q)
                    if intent != 'animal':
                        pass
                    params = parse_query_for_animal(q)
                    print('Okay, I’ll search for:')
                    for k, v in params.items():
                        print(f'  - {k}: {v}')
            if not params:
                sex = self._prompt_sex()
                field = self._prompt_field()
                value = self._prompt_value()
                params = {'sex': sex, 'field': field, 'value': value}
            results = await self.scraper.scrape_animals(params)
            if not results:
                print('No animal results found')
                return
            print('\n' + self.scraper.format_results(results))
            try:
                if input('Show summary? (y/N): ').strip().lower() == 'y':
                    print('\nSummary:')
                    print(summarize_animal_results(results))
            except Exception:
                pass
            await self._show_follow_up_menu(page, results)
        except Exception as e:
            print(f'Error in Animal scraper: {e}')

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
                    filename = input("Enter CSV filename (or press Enter for 'animal_results.csv'): ").strip()
                    if not filename:
                        filename = 'animal_results.csv'
                    exported_file = self.exporter.export_to_csv(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                    # continue showing the menu
                elif choice == '2':
                    filename = input("Enter JSON filename (or press Enter for 'animal_results.json'): ").strip()
                    if not filename:
                        filename = 'animal_results.json'
                    exported_file = self.exporter.export_to_json(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                    # continue showing the menu
                elif choice == '3':
                    # view details may enrich data; keep updated list in memory so user can export afterwards
                    data = await self._view_animal_details(data)
                    # reprint the (possibly enriched) table for convenience
                    print('\n' + self.scraper.format_results(data))
                    # continue showing the menu
                elif choice == '4':
                    # New search within Animal module
                    if not await self.scraper.navigate_to_site(page):
                        print('Failed to load Digital Beef website')
                        continue
                    if not await self.scraper.wait_for_form_ready(page):
                        print('Failed to load Animal search form')
                        continue
                    sex = self._prompt_sex()
                    field = self._prompt_field()
                    value = self._prompt_value()
                    params: Dict[str, str] = {'sex': sex, 'field': field, 'value': value}
                    new_results = await self.scraper.scrape_animals(params)
                    if not new_results:
                        print('No animal results found')
                        continue
                    data = new_results
                    print('\n' + self.scraper.format_results(data))
                    # continue showing the menu with new data
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
                # keep the loop running; user can try again

    async def _view_animal_details(self, data: List[Dict[str, str]]):
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
                print(f'\nFetching details for all {len(data)} animals...')
                enriched_results: List[Dict[str, str]] = []
                for i, animal in enumerate(data, 1):
                    print(f"\nProcessing animal {i}/{len(data)}: {animal.get('registration', 'Unknown')}")
                    registration_url = animal.get('registration_url')
                    if not registration_url:
                        print('  Skipping: No detail URL available')
                        enriched_results.append(animal)
                        continue
                    try:
                        self.scraper.browser, self.scraper.playwright = await self.scraper.init_browser()
                        page = await self.scraper.browser.new_page()
                        details = await self.scraper.extract_animal_detail(page, registration_url)
                        enriched = animal.copy()
                        enriched.update(details)
                        enriched_results.append(enriched)
                    except Exception as e:
                        print(f'  Error: {e}')
                        enriched_results.append(animal)
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
                return enriched_results
            elif choice_num == len(data) + 2:
                print('Cancelled.')
                return data
            elif 1 <= choice_num <= len(data):
                selected_index = choice_num - 1
                selected_animal = data[selected_index]
                registration = selected_animal.get('registration')
                registration_url = selected_animal.get('registration_url')
                if not registration_url:
                    print('No detail URL available for this animal.')
                    return data
                print(f"\nFetching details for {registration}...")
                try:
                    self.scraper.browser, self.scraper.playwright = await self.scraper.init_browser()
                    page = await self.scraper.browser.new_page()
                    details = await self.scraper.extract_animal_detail(page, registration_url)
                    if details:
                        formatted_details = self.scraper.format_animal_detail(details)
                        print('\n' + formatted_details)
                        # update the selected animal with details so user can export later
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

async def main():
    cli = AnimalSearchCLI()
    await cli.main()
if __name__ == '__main__':
    asyncio.run(main()) 