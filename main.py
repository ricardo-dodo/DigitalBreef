#!/usr/bin/env python3
"""
Main Entry Point for Ranch Scraper
Handles both parameter mode and interactive mode with automatic switching
"""

import asyncio
import sys
from typing import Dict, Optional, Tuple
from ranch_scraper.cli import RanchScraperCLI
from ranch_scraper.interactive_prompt import InteractivePrompt
from ranch_scraper.scraper import DynamicScraper
from ranch_scraper.exporter import DynamicExporter
from ranch_scraper.utils import validate_search_params


class RanchScraperMain:
    """Main application handler with mode switching"""
    
    def __init__(self):
        self.cli = RanchScraperCLI()
        self.interactive_prompt = InteractivePrompt()
        self.scraper = DynamicScraper()
        self.exporter = DynamicExporter()
    
    def has_search_parameters(self, args) -> bool:
        """
        Check if any search parameters are provided
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            True if any search parameters are present
        """
        search_params = [
            args.name, args.city, args.prefix, 
            args.member_id, args.location
        ]
        return any(param for param in search_params)
    
    async def run_parameter_mode(self, args) -> None:
        """
        Run scraper in parameter mode (automated)
        
        Args:
            args: Parsed command line arguments
        """
        # Extract search parameters from CLI arguments
        search_params = self.cli.get_search_params_from_args(args)
        
        # Validate parameters
        is_valid, errors = validate_search_params(search_params)
        if not is_valid:
            print("Validation errors:")
            for error in errors:
                print(f"  - {error}")
            print("\nUse --help for usage information")
            sys.exit(1)
        
        # Run the scraper
        await self.cli.run_scraper(search_params, args.export, args.output)
    
    async def run_interactive_mode(self) -> None:
        """
        Run scraper in interactive mode (user input)
        """
        try:
            # Initialize browser
            browser, playwright = await self.scraper.init_browser()
            page = await browser.new_page()
            
            # Navigate to site
            if not await self.scraper.navigate_to_site(page):
                print("Failed to navigate to website")
                return
            
            # Wait for form to be ready
            if not await self.scraper.wait_for_form_ready(page):
                print("Failed to load search form")
                return
            
            # Run interactive prompt
            params, export_format, filename = await self.interactive_prompt.run_interactive_mode(page)
            
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
            print(f"Error in interactive mode: {e}")
        finally:
            if 'browser' in locals():
                try:
                    await browser.close()
                except Exception as e:
                    print(f"Warning: Error closing browser: {e}")
            if 'playwright' in locals():
                try:
                    await playwright.stop()
                except Exception as e:
                    print(f"Warning: Error stopping playwright: {e}")
    
    async def main(self) -> None:
        """Main entry point with mode detection"""
        # Parse command line arguments
        args = self.cli.parse_arguments()
        
        # Handle special commands first
        if args.list_locations:
            await self.cli.list_locations()
            return
        
        if args.form_info:
            await self.cli.show_form_info()
            return
        
        # Check if any search parameters are provided
        if self.has_search_parameters(args):
            # Run in parameter mode (automated)
            print("Running in parameter mode...")
            await self.run_parameter_mode(args)
        else:
            # Run in interactive mode (user input)
            print("No search parameters provided. Switching to interactive mode...")
            await self.run_interactive_mode()


async def main():
    """Main entry point"""
    app = RanchScraperMain()
    await app.main()


if __name__ == "__main__":
    asyncio.run(main()) 