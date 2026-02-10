#!/usr/bin/env python3
"""
Build script to create standalone executable for LNNTÉ Phone Verifier.

This script:
1. Installs required build dependencies
2. Downloads Playwright Chromium browser
3. Builds the .exe using PyInstaller
4. Packages browsers alongside the .exe

Usage:
    python build_exe.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f">>> {description}")
    print(f"{'='*60}")
    print(f"Running: {cmd}")
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"ERROR: {description} failed!")
        return False
    return True


def main():
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print("=" * 60)
    print("LNNTÉ Phone Verifier - Build Script")
    print("=" * 60)
    
    # Step 1: Install build dependencies
    if not run_command(
        f"{sys.executable} -m pip install pyinstaller",
        "Installing PyInstaller"
    ):
        return 1
    
    # Step 2: Install project dependencies
    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing project dependencies"
    ):
        return 1
    
    # Step 3: Install Playwright and download Chromium
    if not run_command(
        f"{sys.executable} -m playwright install chromium",
        "Downloading Playwright Chromium browser"
    ):
        print("WARNING: Playwright browser download failed.")
        print("The app will work in API mode only without browsers.")
    
    # Step 4: Find Playwright browsers location
    browsers_src = None
    possible_paths = [
        Path.home() / ".cache" / "ms-playwright",  # Linux
        Path.home() / "AppData" / "Local" / "ms-playwright",  # Windows
        Path.home() / "Library" / "Caches" / "ms-playwright",  # macOS
    ]
    
    for path in possible_paths:
        if path.exists():
            browsers_src = path
            print(f"Found Playwright browsers at: {browsers_src}")
            break
    
    # Step 5: Build the executable
    if not run_command(
        f"{sys.executable} -m PyInstaller --clean lnnte_verifier.spec",
        "Building executable with PyInstaller"
    ):
        return 1
    
    # Step 6: Copy browsers to dist folder
    dist_dir = project_root / "dist"
    browsers_dest = dist_dir / "browsers"
    
    if browsers_src and browsers_src.exists():
        print(f"\n>>> Copying Playwright browsers to dist folder...")
        if browsers_dest.exists():
            shutil.rmtree(browsers_dest)
        shutil.copytree(browsers_src, browsers_dest)
        print(f"Browsers copied to: {browsers_dest}")
    else:
        print("\nWARNING: Playwright browsers not found.")
        print("The executable will work in API mode only.")
        print("For browser mode, manually copy ms-playwright folder to 'browsers' next to .exe")
    
    # Step 7: Copy .env template
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if env_file.exists():
        # Create example without actual keys
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Replace values with placeholders
        example_content = """# API Keys - Replace with your own keys
SERPER_API_KEY=your_serper_api_key_here
Captcha_API_KEY=your_2captcha_api_key_here
PROXIES=
"""
        with open(dist_dir / ".env.example", 'w') as f:
            f.write(example_content)
        print("Created .env.example in dist folder")
    
    # Step 8: Create README for distribution
    readme_content = """# LNNTÉ Phone Number Verifier

## Quick Start

1. Copy `.env.example` to `.env` and add your API keys:
   - `Captcha_API_KEY`: Your 2captcha.com API key (required for API mode)
   - `SERPER_API_KEY`: Your serper.dev API key (optional, for business check)

2. Run `LNNTE_Verifier.exe`

## Modes

### API Mode (Recommended)
- Fast, automated verification
- Requires 2captcha API key
- No browser needed

### Browser Mode
- Opens a browser window
- Requires manual CAPTCHA solving
- Requires the `browsers` folder next to the .exe

## Troubleshooting

If browser mode doesn't work:
1. Make sure the `browsers` folder exists next to the .exe
2. The folder should contain Chromium from Playwright

For API mode issues:
1. Check your 2captcha balance
2. Verify your API key is correct
"""
    
    with open(dist_dir / "README.txt", 'w') as f:
        f.write(readme_content)
    print("Created README.txt in dist folder")
    
    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    print(f"\nOutput location: {dist_dir}")
    print("\nFiles created:")
    for f in dist_dir.iterdir():
        size = f.stat().st_size if f.is_file() else sum(
            file.stat().st_size for file in f.rglob('*') if file.is_file()
        )
        size_mb = size / (1024 * 1024)
        print(f"  - {f.name}: {size_mb:.1f} MB")
    
    print("\nTo distribute:")
    print("1. Zip the entire 'dist' folder")
    print("2. Share with users")
    print("3. Users should extract and run LNNTE_Verifier.exe")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
