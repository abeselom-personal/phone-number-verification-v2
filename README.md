# LNNTÉ / DNCL Phone Number Verifier

A Python tool that verifies Canadian phone numbers against the National Do Not Call List (DNCL) using the official LNNTÉ consumer verification portal.

## Features

- **Input Support**: CSV and Excel files (.xlsx, .xls)
- **Phone Detection**: Automatically finds phone numbers in columns like `Téléphone`, `Portable`, `Phone`, `Mobile`, `Cell`, `Office`
- **Browser Automation**: Uses Playwright for reliable browser control
- **CAPTCHA Handling**: Pauses for human CAPTCHA solving (no bypass attempts)
- **Result Output**: Preserves all original columns, adds verification status
- **Logging**: Full verification log with timestamps

---

## Quick Start (Windows)

### Step 1: Install Python

1. Download Python 3.9+ from [python.org](https://www.python.org/downloads/)
2. **Important**: Check ✅ "Add Python to PATH" during installation

### Step 2: Run Setup

1. Double-click `setup.bat`
2. Wait for installation to complete (2-5 minutes)

### Step 3: Run the Application

1. Double-click `run.bat`
2. The application window will open

---

## User Guide

### Loading Input Files

1. Click **"Browse..."** to select your CSV or Excel file
2. The application will show how many phone numbers were found
3. Supported phone columns: `Téléphone`, `Telephone`, `Phone`, `Portable`, `Mobile`, `Cell`, `Office`

### Phone Number Format

Phone numbers are automatically normalized. These formats are all accepted:
- `819-555-1234`
- `(819) 555-1234`
- `819.555.1234`
- `8195551234`
- `1-819-555-1234`

### Running Verification

1. Select output format (CSV or Excel)
2. Click **"Start Verification"**
3. A browser window will open automatically

### Solving CAPTCHA

⚠️ **Important**: For each phone number:

1. The browser will navigate to the LNNTÉ site
2. The phone number will be entered automatically
3. **You must solve the CAPTCHA manually** in the browser
4. After solving, click the checkbox or complete the challenge
5. The tool will automatically detect completion and proceed

The application status bar shows: `"Please solve the CAPTCHA in the browser window"`

### Retrieving Output

After verification completes:

1. A summary dialog appears with results
2. Output file is saved in the **same folder** as your input file
3. Filename: `[original_name]_verified_[timestamp].csv` (or `.xlsx`)

### Output Columns

Your output file contains:
- **All original columns** (preserved exactly)
- **Cell or Office**: Which type of phone field contained the number
- **LNNTE**: Verification result
  - `On list` - Number is registered on the Do Not Call List
  - `Not on list` - Number is NOT registered
  - `Unknown` - Could not determine (timeout, error, etc.)

---

## Troubleshooting

### "Python is not installed"
- Install Python from [python.org](https://www.python.org/downloads/)
- Make sure to check "Add Python to PATH"

### Browser doesn't open
- Run `setup.bat` again to reinstall Playwright browsers
- Check your antivirus isn't blocking the application

### CAPTCHA timeout
- You have 5 minutes to solve each CAPTCHA
- If it times out, the number is marked as "Unknown"
- You can re-run verification for failed numbers

### No phone numbers found
- Check your column names match supported formats
- Ensure phone numbers are in valid Canadian format (10 digits)

---

## Project Structure

```
candice/
├── main.py              # Application entry point
├── run.bat              # Windows launcher
├── setup.bat            # Windows setup script
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── src/
    ├── __init__.py
    ├── input_processor.py    # CSV/Excel parsing, phone normalization
    ├── browser_automation.py # Playwright browser control
    ├── output_processor.py   # Result aggregation, file output
    └── ui.py                 # Desktop GUI (tkinter)
```

---

## Automation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    VERIFICATION FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Load Input File                                         │
│     └── Parse CSV/Excel, extract phone numbers              │
│                                                             │
│  2. For Each Phone Number:                                  │
│     ├── Navigate to LNNTÉ verification page                 │
│     ├── Enter phone in #phone input field                   │
│     ├── Click "Next" button                                 │
│     ├── ⏸️  PAUSE: Wait for human CAPTCHA solution          │
│     ├── Detect CAPTCHA completion (g-recaptcha-response)    │
│     ├── Click "Check Registration" button                   │
│     └── Extract result from page content                    │
│                                                             │
│  3. Generate Output                                         │
│     ├── Preserve all original columns                       │
│     ├── Add "Cell or Office" column                         │
│     ├── Add "LNNTE" status column                           │
│     └── Save as CSV or Excel                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Compliance & Limitations

### What This Tool Does
- Uses the **official public LNNTÉ consumer verification portal**
- Automates only the form-filling steps
- **Requires human CAPTCHA solving** for each verification
- Operates at human-speed (one number at a time)

### What This Tool Does NOT Do
- ❌ Bypass or auto-solve CAPTCHAs
- ❌ Scrape or extract data beyond verification results
- ❌ Use unofficial APIs or endpoints
- ❌ Store or transmit phone numbers externally

### Rate Limiting
- The tool processes one phone number at a time
- Each verification requires human CAPTCHA interaction
- This inherently limits request rate to human speed

### Terms of Service
Users are responsible for ensuring their use of this tool complies with:
- LNNTÉ/DNCL Terms of Service
- Canadian privacy regulations (PIPEDA)
- Any applicable telemarketing regulations

---

## Requirements

- **OS**: Windows 10/11
- **Python**: 3.9 or later
- **Dependencies**:
  - playwright 1.40.0
  - pandas 2.1.4
  - openpyxl 3.1.2

---

## Manual Installation (Advanced)

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run application
python main.py
```

---

## License

This tool is provided for legitimate business verification purposes. Use responsibly and in compliance with all applicable laws and regulations.
