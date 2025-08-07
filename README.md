# Ranch Scraper

Dynamic web scraper for Digital Beef Shorthorn ranch data with **dual-mode operation**: parameter mode (automated) and interactive mode (user input).

## 🏗️ Project Structure

```
DigitalBreef/
├── ranch_scraper/           # Ranch Scraper Module
│   ├── __init__.py         # Package initialization
│   ├── cli.py              # Command line interface
│   ├── scraper.py          # Dynamic scraper core
│   ├── form_parser.py      # Form detection & parsing
│   ├── form_handler.py     # Dynamic form field handling
│   ├── interactive_prompt.py # Interactive user input
│   ├── exporter.py         # Export functionality
│   ├── utils.py            # Shared utilities
│   └── test_scraper.py     # Comprehensive tests
├── main.py                 # Main entry point (dual-mode)
├── requirements.txt        # Dependencies
├── README.md              # Documentation
├── install.bat            # Windows installer
├── install.sh             # Unix installer
└── .gitignore            # Git ignore rules
```

## 🚀 Quick Start

### Installation

**Windows:**
```bash
install.bat
```

**Unix/Linux:**
```bash
chmod +x install.sh
./install.sh
```

**Manual:**
```bash
pip install -r requirements.txt
playwright install
```

## 🎯 Dual-Mode Operation

### 1. Parameter Mode (Automated)
When CLI arguments are provided, the scraper runs in automated mode:

```bash
# Basic search with parameters
python main.py --location "Texas" --name "AA"

# Export to CSV
python main.py --location "TX" --export csv --output results.csv

# Export to JSON
python main.py --name "Smith" --export json
```

### 2. Interactive Mode (User Input)
When no parameters are provided, automatically switches to interactive mode:

```bash
# Run interactive mode
python main.py
```

**Interactive Mode Features:**
- ✅ **Step-by-step prompts** for each search field
- ✅ **Live dropdown options** fetched from the website
- ✅ **Dynamic validation** against available form options
- ✅ **Skip any field** by pressing Enter
- ✅ **Export options** at the end (CSV/JSON/none)
- ✅ **Input validation** with retry options

## 📋 Usage Examples

### Parameter Mode Examples

```bash
# Search by ranch name
python main.py --name "Red*"

# Search by city
python main.py --city "Dallas"

# Search by herd prefix
python main.py --prefix "RZ"

# Search by member ID
python main.py --member_id "44-12345"

# Search by location (multiple formats supported)
python main.py --location "United States|TX"
python main.py --location "Texas"
python main.py --location "TX"

# Combine multiple filters
python main.py --name "Red*" --city "Dallas" --location "Texas"

# Export results
python main.py --location "TX" --export csv --output my_results.csv
```

### Interactive Mode Example

```bash
python main.py
```

**Sample Interactive Session:**
```
No search parameters provided. Switching to interactive mode...
Navigating to https://shorthorn.digitalbeef.com
Ranch Search section loaded successfully
=== Ranch Scraper Interactive Mode ===
Enter search parameters (press Enter to skip):

Ranch Name: AA
City: Dallas
Member Id: 
Herd Prefix: 

Available locations (52 total):
  1. 
  2. United States - All
  3. United States - Alabama
  4. United States - Arizona
  ...
  (You can enter location name, state code, or number from list)
Location: Texas
✓ Selected: United States|TX

=== Export Options ===
Export results to CSV, JSON, or skip? (csv/json/none): csv
Output filename (optional, press Enter for auto-generated): my_results.csv
```

## 🎯 Features

### ✅ Dynamic Form Detection
- **No hardcoded values** - discovers form structure at runtime
- **Field validation** - confirms all required fields exist
- **Location mapping** - intelligently maps user input to dropdown options

### ✅ Flexible Search Options
- **Ranch name** - `--name "Red*"`
- **City** - `--city "Dallas"`
- **Herd prefix** - `--prefix "ZZZ"`
- **Member ID** - `--member_id "44-12345"`
- **Location** - `--location "Texas"` or `--location "TX"`

### ✅ Export Capabilities
- **CSV export** - `--export csv`
- **JSON export** - `--export json`
- **Custom filenames** - `--output my_results.csv`
- **Auto-generated names** - timestamp-based defaults

### ✅ Interactive Mode Features
- **Live form detection** - shows available options
- **Guided prompts** - step-by-step parameter entry
- **Location selection** - numbered list of available locations
- **Input validation** - validates against actual form options
- **Export prompts** - asks for export preferences at the end

## 🔧 Technical Details

### Dynamic Capabilities
- **Runtime form validation** - checks field existence before use
- **JavaScript function detection** - adapts to website changes
- **Table structure detection** - no fixed column assumptions
- **Export field auto-detection** - uses actual scraped data structure

### Error Handling
- **Graceful degradation** - multiple fallback methods
- **Clear error messages** - specific field validation errors
- **Resource cleanup** - proper browser and playwright cleanup

### Browser Automation
- **Headless operation** - no visible browser window
- **JavaScript execution** - direct function calls when available
- **Element waiting** - robust timeout and retry logic

## 📊 Example Output

```
Running in parameter mode...
Navigating to https://shorthorn.digitalbeef.com
Ranch Search section loaded successfully
Filled name: AA
Selected location: Texas -> United States|TX
Search triggered via JavaScript function
Search results loaded
Found 21 ranch entries

=======================================================================================================
type | member_id | herd_prefix | member_name                    | dba                           | city | state
=======================================================================================================
AA   | 44-30951  |             | 3 TREES LAND & CATTLE CO       | AARON CASTILLO                | AUSTIN | TX
AA   | 44-18753  | BRTX        | AARON AND TAYLOR BEAMAN        |                               | MART  | TX
=======================================================================================================
Total results: 21
Results exported to: ranch_results_20250807_085821.csv
```

## 🧪 Testing

Run the comprehensive test suite:
```bash
python -m ranch_scraper.test_scraper
```

## 📝 License

This project is for educational and research purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For issues and questions, please check the test results and form information commands:
```bash
python main.py --form-info
python main.py --list-locations
``` 