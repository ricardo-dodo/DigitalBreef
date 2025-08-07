#!/usr/bin/env python3
"""
CLI Interface for Ranch Scraper
Handles command line arguments and parameter mode
"""

import argparse
import asyncio
import sys
from typing import Dict, List, Optional
from playwright.async_api import Page
from .scraper import DynamicScraper
from .exporter import DynamicExporter
from .utils import validate_search_params, parse_location_input, sanitize_filename


class RanchScraperCLI:
    """Command line interface for ranch scraper"""
    
    def __init__(self):
        self.scraper = DynamicScraper()
        self.exporter = DynamicExporter()
        
    def parse_arguments(self) -> argparse.Namespace:
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description="Dynamic Ranch Scraper for Digital Beef Shorthorn",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python main.py --name "Red*" --city "Dallas" --location "Texas"
  python main.py --prefix "ZZZ" --export csv
  python main.py --location "TX" --output results.csv
  python main.py --list-locations
  python main.py (runs in interactive mode)
        """
        )
        
        # Search parameters
        parser.add_argument('--name', help='Ranch name filter')
        parser.add_argument('--city', help='City filter')
        parser.add_argument('--prefix', help='Herd prefix filter')
        parser.add_argument('--member_id', help='Member ID filter')
        parser.add_argument('--location', help='Location filter (supports multiple formats)')
        
        # Export options
        parser.add_argument('--export', choices=['csv', 'json'], help='Export format')
        parser.add_argument('--output', help='Output filename')
        
        # Info options
        parser.add_argument('--list-locations', action='store_true', help='List available locations')
        parser.add_argument('--form-info', action='store_true', help='Show form structure information')
        
        return parser.parse_args()
    
    def get_search_params_from_args(self, args: argparse.Namespace) -> Dict[str, str]:
        """Extract search parameters from arguments"""
        params = {}
        
        if args.name:
            params['name'] = args.name.strip()
        if args.city:
            params['city'] = args.city.strip()
        if args.prefix:
            params['prefix'] = args.prefix.strip()
        if args.member_id:
            params['member_id'] = args.member_id.strip()
        if args.location:
            params['location'] = args.location.strip()
        
        return params
    
    async def get_available_locations(self) -> List[Dict[str, str]]:
        """Get available locations from the website"""
        try:
            # Initialize browser
            browser, playwright = await self.scraper.init_browser()
            page = await browser.new_page()
            
            # Navigate and get locations
            await self.scraper.navigate_to_site(page)
            await self.scraper.wait_for_form_ready(page)
            locations = await self.scraper.get_available_locations(page)
            
            await browser.close()
            await playwright.stop()
            
            return locations
        except Exception as e:
            print(f"Error getting locations: {e}")
            return []
    
    async def list_locations(self):
        """List all available locations"""
        print("Fetching available locations...")
        locations = await self.get_available_locations()
        
        if not locations:
            print("No locations found or error occurred")
            return
        
        print(f"\nAvailable locations ({len(locations)} total):")
        print("=" * 60)
        
        for i, location in enumerate(locations, 1):
            print(f"{i:3d}. {location['text']:<40} ({location['value']})")
        
        print("=" * 60)
        print("Usage examples:")
        print("  --location 'Texas'")
        print("  --location 'TX'")
        print("  --location 'United States|TX'")
    
    async def show_form_info(self):
        """Show form structure information"""
        print("Fetching form information...")
        
        try:
            # Initialize browser
            browser, playwright = await self.scraper.init_browser()
            page = await browser.new_page()
            
            # Get form info
            form_info = await self.scraper.get_form_info(page)
            
            await browser.close()
            await playwright.stop()
            
            if form_info:
                print("\nForm Structure Information:")
                print("=" * 40)
                
                # Show available fields
                if 'form_structure' in form_info:
                    fields = form_info['form_structure'].get('fields', {})
                    print(f"Available fields ({len(fields)}):")
                    for field_id, field_info in fields.items():
                        print(f"  - {field_id}: {field_info.get('type', 'unknown')}")
                
                # Show search button info
                if 'search_button' in form_info:
                    button_info = form_info['search_button']
                    print(f"\nSearch button:")
                    print(f"  - Has function: {button_info.get('hasFunction', False)}")
                    if button_info.get('button'):
                        print(f"  - Button: {button_info['button'].get('value', 'N/A')}")
                
                # Show locations
                if 'available_locations' in form_info:
                    locations = form_info['available_locations']
                    print(f"\nAvailable locations: {len(locations)}")
                    for i, location in enumerate(locations[:5], 1):
                        print(f"  {i}. {location['text']}")
                    if len(locations) > 5:
                        print(f"  ... and {len(locations) - 5} more")
            else:
                print("Could not retrieve form information")
                
        except Exception as e:
            print(f"Error getting form info: {e}")
    
    async def run_scraper(self, search_params: Dict[str, str], 
                         export_format: Optional[str] = None,
                         output_filename: Optional[str] = None):
        """Run the scraper with given parameters"""
        print(f"\nSearching with parameters: {search_params}")
        
        # Run the scraper
        results = await self.scraper.scrape_ranches(search_params)
        
        if not results:
            print("No results found")
            return
        
        # Display results
        print("\n" + self.scraper.format_results(results))
        
        # Export if requested
        if export_format:
            if output_filename:
                exported_file = self.exporter.export_data(results, export_format, output_filename)
            else:
                exported_file = self.exporter.export_data(results, export_format)
            
            if exported_file:
                print(f"Results exported to: {exported_file}")
    
    async def main(self):
        """Main CLI entry point"""
        args = self.parse_arguments()
        
        # Handle special commands
        if args.list_locations:
            await self.list_locations()
            return
        
        if args.form_info:
            await self.show_form_info()
            return
        
        # Get search parameters
        search_params = self.get_search_params_from_args(args)
        
        # Validate parameters
        is_valid, errors = validate_search_params(search_params)
        if not is_valid:
            print("Validation errors:")
            for error in errors:
                print(f"  - {error}")
            print("\nUse --help for usage information")
            print("Run without arguments for interactive mode")
            sys.exit(1)
        
        # Run the scraper
        await self.run_scraper(search_params, args.export, args.output)
    
    async def main_with_page(self, page: Page):
        """Main entry point for use with existing page object"""
        try:
            # Wait for form to be ready
            if not await self.scraper.wait_for_form_ready(page):
                print("Failed to load search form")
                return
            
            # Run interactive mode since we have a page
            from .interactive_prompt import InteractivePrompt
            interactive_prompt = InteractivePrompt()
            
            # Run interactive prompt
            params, export_format, filename = await interactive_prompt.run_interactive_mode(page)
            
            if not params:
                print("No search parameters provided. Exiting.")
                return
            
            # Run the scraper with collected parameters
            results = await self.scraper.scrape_ranches(params)
            
            if not results:
                print("No results found")
                return
            
            # Display results
            print("\n" + self.scraper.format_results(results))
            
            # Export if requested
            if export_format:
                if filename:
                    exported_file = self.exporter.export_data(results, export_format, filename)
                else:
                    exported_file = self.exporter.export_data(results, export_format)
                
                if exported_file:
                    print(f"Results exported to: {exported_file}")
                    
        except Exception as e:
            print(f"Error in ranch scraper: {e}")


async def main():
    """Main entry point"""
    cli = RanchScraperCLI()
    await cli.main()


if __name__ == "__main__":
    asyncio.run(main()) 