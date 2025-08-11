## DigitalBeef Intelligent Scraper

Search, explore, and export Digital Beef Shorthorn data with a fast, user-friendly CLI. Includes three focused tools (Ranch, Animal, EPD), natural-language entry, interactive prompts, and CSV/JSON export.

### What you get
- **Ranch Search**: Find members by name, city, herd prefix, member ID, and location (auto-mapped to site dropdowns).
- **Animal Search**: Search by registration, tattoo, name, or EID. Open detail pages and enrich results.
- **EPD Search**: Filter by common EPD traits (e.g., WW, YW, Milk) with min/max/accuracy and sorting.
- **Natural-language entry**: Type a query in your own words; the app maps it to the right fields.
- **Interactive mode**: Friendly prompts, live option listing, and validation.
- **Export**: CSV or JSON with smart defaults; optional summary.
- **Automated tests**: A root-level test suite validates end-to-end scraping.

### Quick start
- Windows (CMD/PowerShell)
  - Create venv and install: `python -m venv .venv && .venv\\Scripts\\activate && pip install -r requirements.txt`
  - Install browsers: `python -m playwright install`
- macOS/Linux
  - `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python -m playwright install`

### Two ways to use
- **Menu-driven (interactive)**
  - `python main.py`
  - Choose Ranch, EPD, or Animal; answer short prompts. You can also “type a search in your own words” for a quick start.
- **One-liners (automated)**
  - Ranch examples:
    - `python main.py --location "TX" --name "AA" --export csv`
    - `python main.py --semantic --query "texas ranches near dallas with prefix rz" --summary`

### Feature preview
- **Ranch Search**
  - Filters: `--name`, `--city`, `--prefix`, `--member_id`, `--location`
  - Location is mapped intelligently to the website’s dropdown options, accepting names or codes (e.g., `Texas`, `TX`, `United States|TX`).
  - Interactive mode shows a list of available locations and validates input.
- **Animal Search**
  - Fields: Registration, Tattoo, Name, EID
  - Results include a link to the registration page, and you can fetch detail pages into the result set.
- **EPD Search**
  - Traits with min/max/accuracy (where applicable) and sort by common fields like WW/YW/Milk.
  - Interactive trait selection (numbers, ranges, or partial names) or quick free-text description.
- **Natural-language entry**
  - Automated mode: `--semantic --query "females with milk > 25 and ww > 60 sort by ww"`
  - Interactive mode: choose “Type a search in your own words?” and describe what you’re looking for.
- **Export**
  - `--export csv --output results.csv` or `--export json` (interactive mode also offers export).

### Examples
- Ranch (command-line)
  - `python main.py --name "Red*" --city "Dallas" --location "Texas"`
  - `python main.py --semantic --query "ranches in TX named AA" --summary`
- Animal (interactive)
  - Choose Animal Search → type: “bulls named red*” → export to CSV.
- EPD (interactive)
  - Pick traits (by numbers or partial names), set min/max/acc, choose sort; or describe: “females with ww > 60”.

### Output preview
```
===============================================
registration | name               | birthdate
===============================================
X12345       | RED EXAMPLE 12     | 01/01/2020
...
Total results: 3882
```

### Automated tests
- Run all tests from the repo root: `python test_suite.py`
- The suite exercises:
  - Ranch: result presence and location mapping
  - Animal: wildcard search and detail extraction
  - EPD: broad settings producing results
- Exit code is non-zero on failure; a concise summary prints at the end.

### Notes
- Runs headless via Playwright. No external APIs; works offline (browsers required). 
- If your editor flags missing imports, activate your venv and install dependencies as shown above. 