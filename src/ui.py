"""
Desktop UI module using tkinter.
Provides simple interface for non-technical users.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import logging
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv, set_key

from .input_processor import InputProcessor
from .browser_automation import VerificationStatus, VerificationResult
from .output_processor import OutputProcessor, VerificationLog
from .business_checker import SerperBusinessChecker
from .api_verification import LNNTEApiVerifier

logger = logging.getLogger(__name__)


class TextHandler(logging.Handler):
    """Logging handler that writes to a tkinter Text widget."""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
    
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tk.END)
        self.text_widget.after(0, append)


class LNNTEVerifierApp:
    """Main application window for LNNTÉ phone verification."""
    
    ENV_FILE = Path(__file__).parent.parent / ".env"
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LNNTÉ Phone Number Verifier")
        self.root.geometry("850x900")
        self.root.minsize(750, 800)
        
        self.input_file: Optional[str] = None
        self.output_file: Optional[str] = None
        self.is_running = False
        self.should_stop = False
        
        # Load environment variables
        load_dotenv(self.ENV_FILE)
        self._env_keys = {
            'serper': os.getenv('SERPER_API_KEY', ''),
            'captcha': os.getenv('Captcha_API_KEY', ''),
            'proxies': os.getenv('PROXIES', '')
        }
        
        self._setup_ui()
        self._setup_logging()
        self._load_env_to_ui()
    
    def _setup_ui(self):
        """Create and arrange UI components."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        title_label = ttk.Label(
            main_frame, 
            text="LNNTÉ / DNCL Phone Number Verifier",
            font=('Helvetica', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        input_frame = ttk.LabelFrame(main_frame, text="Input File", padding="10")
        input_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        input_frame.columnconfigure(1, weight=1)
        
        ttk.Label(input_frame, text="File:").grid(row=0, column=0, padx=(0, 5))
        self.input_path_var = tk.StringVar()
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_path_var, state='readonly')
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.browse_btn = ttk.Button(input_frame, text="Browse...", command=self._browse_input)
        self.browse_btn.grid(row=0, column=2, padx=(5, 0))
        
        self.file_info_var = tk.StringVar(value="No file loaded")
        ttk.Label(input_frame, textvariable=self.file_info_var, foreground='gray').grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(5, 0)
        )
        
        # 2captcha Settings
        captcha_frame = ttk.LabelFrame(main_frame, text="2Captcha API Key (Required)", padding="10")
        captcha_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
        captcha_frame.columnconfigure(1, weight=1)
        
        ttk.Label(captcha_frame, text="2Captcha API Key:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.twocaptcha_key_var = tk.StringVar()
        self.twocaptcha_show_var = tk.BooleanVar(value=False)
        self.twocaptcha_entry = ttk.Entry(captcha_frame, textvariable=self.twocaptcha_key_var, show="*")
        self.twocaptcha_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.twocaptcha_toggle_btn = ttk.Button(
            captcha_frame, text="Show", width=6,
            command=lambda: self._toggle_key_visibility('captcha')
        )
        self.twocaptcha_toggle_btn.grid(row=0, column=2, padx=(0, 5))
        ttk.Button(captcha_frame, text="Save", width=6, command=lambda: self._save_env_key('captcha')).grid(
            row=0, column=3
        )
        self.twocaptcha_status_var = tk.StringVar(value="")
        ttk.Label(captcha_frame, textvariable=self.twocaptcha_status_var, foreground='green').grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(2, 0)
        )
        
        # Proxy Settings
        proxy_frame = ttk.LabelFrame(main_frame, text="Proxy Settings (Optional)", padding="10")
        proxy_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        proxy_frame.columnconfigure(1, weight=1)
        
        ttk.Label(proxy_frame, text="Proxies:").grid(row=0, column=0, padx=(0, 5), sticky="nw")
        self.proxy_var = tk.StringVar()
        self.proxy_show_var = tk.BooleanVar(value=False)
        self.proxy_entry = ttk.Entry(proxy_frame, textvariable=self.proxy_var, show="*")
        self.proxy_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.proxy_toggle_btn = ttk.Button(
            proxy_frame, text="Show", width=6,
            command=lambda: self._toggle_key_visibility('proxy')
        )
        self.proxy_toggle_btn.grid(row=0, column=2, padx=(0, 5))
        ttk.Button(proxy_frame, text="Save", width=6, command=lambda: self._save_env_key('proxy')).grid(
            row=0, column=3
        )
        self.proxy_status_var = tk.StringVar(value="")
        ttk.Label(proxy_frame, textvariable=self.proxy_status_var, foreground='green').grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(2, 0)
        )
        
        # Output Settings
        settings_frame = ttk.LabelFrame(main_frame, text="Output Settings", padding="10")
        settings_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=5)
        settings_frame.columnconfigure(1, weight=1)
        
        ttk.Label(settings_frame, text="Output Format:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.output_format_var = tk.StringVar(value="csv")
        format_combo = ttk.Combobox(
            settings_frame, 
            textvariable=self.output_format_var,
            values=["csv", "excel"],
            state='readonly',
            width=10
        )
        format_combo.grid(row=0, column=1, sticky="w", padx=5)
        
        # Business Check (Serper API)
        api_frame = ttk.LabelFrame(main_frame, text="Business Check (Serper API)", padding="10")
        api_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        api_frame.columnconfigure(1, weight=1)
        
        ttk.Label(api_frame, text="Serper API Key:").grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.api_key_var = tk.StringVar()
        self.serper_show_var = tk.BooleanVar(value=False)
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.serper_toggle_btn = ttk.Button(
            api_frame, text="Show", width=6,
            command=lambda: self._toggle_key_visibility('serper')
        )
        self.serper_toggle_btn.grid(row=0, column=2, padx=(0, 5))
        ttk.Button(api_frame, text="Save", width=6, command=lambda: self._save_env_key('serper')).grid(
            row=0, column=3
        )
        self.serper_status_var = tk.StringVar(value="")
        ttk.Label(api_frame, textvariable=self.serper_status_var, foreground='green').grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(2, 0)
        )
        
        self.business_check_var = tk.BooleanVar(value=False)
        business_check = ttk.Checkbutton(
            api_frame,
            text="Check if phone is a business",
            variable=self.business_check_var
        )
        business_check.grid(row=2, column=0, columnspan=4, sticky="w", pady=(5, 0))
        
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=6, column=0, columnspan=3, pady=15)
        
        self.start_btn = ttk.Button(
            control_frame, 
            text="Start Verification",
            command=self._start_verification,
            style='Accent.TButton'
        )
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = ttk.Button(
            control_frame,
            text="Stop",
            command=self._stop_verification,
            state='disabled'
        )
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        
        self.progress_label_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.progress_label_var).grid(
            row=1, column=0, sticky="w", pady=(5, 0)
        )
        
        status_info_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_info_frame.grid(row=9, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.captcha_label_var = tk.StringVar(value="Ready")
        self.captcha_label = ttk.Label(
            status_info_frame, 
            textvariable=self.captcha_label_var,
            font=('Helvetica', 11)
        )
        self.captcha_label.grid(row=0, column=0, sticky="w")
        
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=10, column=0, columnspan=3, sticky="nsew", pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(10, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            state='disabled',
            font=('Consolas', 9)
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready - Load a file to begin")
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
    
    def _setup_logging(self):
        """Configure logging to display in the log widget."""
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S'))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(text_handler)
        root_logger.setLevel(logging.INFO)
    
    def _mask_key(self, key: str) -> str:
        """Mask API key for display, showing only first 4 and last 4 chars."""
        if not key or len(key) < 10:
            return key
        return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"
    
    def _load_env_to_ui(self):
        """Load environment values into UI fields."""
        # Load 2captcha key
        if self._env_keys['captcha']:
            self.twocaptcha_key_var.set(self._env_keys['captcha'])
            self.twocaptcha_status_var.set(f"✓ Loaded from .env ({self._mask_key(self._env_keys['captcha'])})")
        
        # Load Serper key
        if self._env_keys['serper']:
            self.api_key_var.set(self._env_keys['serper'])
            self.serper_status_var.set(f"✓ Loaded from .env ({self._mask_key(self._env_keys['serper'])})")
        
        # Load proxies
        if self._env_keys['proxies']:
            self.proxy_var.set(self._env_keys['proxies'])
            self.proxy_status_var.set("✓ Loaded from .env")
    
    def _toggle_key_visibility(self, key_type: str):
        """Toggle visibility of API key fields."""
        if key_type == 'captcha':
            showing = self.twocaptcha_show_var.get()
            self.twocaptcha_show_var.set(not showing)
            self.twocaptcha_entry.configure(show="" if not showing else "*")
            self.twocaptcha_toggle_btn.configure(text="Hide" if not showing else "Show")
        elif key_type == 'serper':
            showing = self.serper_show_var.get()
            self.serper_show_var.set(not showing)
            self.api_key_entry.configure(show="" if not showing else "*")
            self.serper_toggle_btn.configure(text="Hide" if not showing else "Show")
        elif key_type == 'proxy':
            showing = self.proxy_show_var.get()
            self.proxy_show_var.set(not showing)
            self.proxy_entry.configure(show="" if not showing else "*")
            self.proxy_toggle_btn.configure(text="Hide" if not showing else "Show")
    
    def _save_env_key(self, key_type: str):
        """Save API key to .env file."""
        env_path = str(self.ENV_FILE)
        
        # Create .env file if it doesn't exist
        if not self.ENV_FILE.exists():
            self.ENV_FILE.touch()
        
        try:
            if key_type == 'captcha':
                value = self.twocaptcha_key_var.get().strip()
                if value:
                    set_key(env_path, 'Captcha_API_KEY', value)
                    self._env_keys['captcha'] = value
                    self.twocaptcha_status_var.set(f"✓ Saved to .env ({self._mask_key(value)})")
                    logger.info("2Captcha API key saved to .env")
            elif key_type == 'serper':
                value = self.api_key_var.get().strip()
                if value:
                    set_key(env_path, 'SERPER_API_KEY', value)
                    self._env_keys['serper'] = value
                    self.serper_status_var.set(f"✓ Saved to .env ({self._mask_key(value)})")
                    logger.info("Serper API key saved to .env")
            elif key_type == 'proxy':
                value = self.proxy_var.get().strip()
                if value:
                    set_key(env_path, 'PROXIES', value)
                    self._env_keys['proxies'] = value
                    self.proxy_status_var.set("✓ Saved to .env")
                    logger.info("Proxies saved to .env")
        except Exception as e:
            logger.error(f"Failed to save to .env: {e}")
            messagebox.showerror("Error", f"Failed to save to .env:\n{str(e)}")
    
    def _browse_input(self):
        """Open file dialog to select input file."""
        filetypes = [
            ("Supported files", "*.csv *.xlsx *.xls"),
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx *.xls"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=filetypes
        )
        
        if filename:
            self.input_file = filename
            self.input_path_var.set(filename)
            self._load_and_preview_file(filename)
    
    def _load_and_preview_file(self, filepath: str):
        """Load file and show preview info."""
        try:
            processor = InputProcessor()
            df = processor.load_file(filepath)
            entries = processor.extract_phone_entries()
            
            self.file_info_var.set(
                f"Loaded: {len(df)} rows, {len(entries)} phone numbers to verify"
            )
            self.status_var.set("File loaded - Ready to start verification")
            
            logger.info(f"Loaded {filepath}")
            logger.info(f"Found {len(entries)} phone numbers in {len(df)} rows")
            
        except Exception as e:
            self.file_info_var.set(f"Error: {str(e)}")
            self.status_var.set("Error loading file")
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
    
    def _start_verification(self):
        """Start the verification process in a background thread."""
        if not self.input_file:
            messagebox.showwarning("No File", "Please select an input file first.")
            return
        
        self.is_running = True
        self.should_stop = False
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.browse_btn.configure(state='disabled')
        
        thread = threading.Thread(target=self._run_verification, daemon=True)
        thread.start()
    
    def _stop_verification(self):
        """Signal to stop the verification process."""
        self.should_stop = True
        self.status_var.set("Stopping... please wait")
        logger.info("Stop requested by user")
    
    def _update_captcha_status(self, message: str):
        """Update CAPTCHA status label (called from worker thread)."""
        def update():
            self.captcha_label_var.set(message)
            self.captcha_label.configure(foreground='red' if 'solve' in message.lower() else 'black')
        self.root.after(0, update)
    
    def _update_progress(self, current: int, total: int, message: str):
        """Update progress bar and label (called from worker thread)."""
        def update():
            percent = (current / total * 100) if total > 0 else 0
            self.progress_var.set(percent)
            self.progress_label_var.set(f"{message} ({current}/{total})")
        self.root.after(0, update)
    
    def _update_status(self, message: str):
        """Update status bar (called from worker thread)."""
        def update():
            self.status_var.set(message)
        self.root.after(0, update)
    
    def _run_verification(self):
        """Main verification loop (runs in background thread)."""
        automation = None
        api_verifier = None
        business_checker = None
        
        try:
            processor = InputProcessor()
            df = processor.load_file(self.input_file)
            entries = processor.extract_phone_entries()
            
            if not entries:
                self._update_status("No valid phone numbers found in file")
                self._finish_verification()
                return
            
            output_processor = OutputProcessor(df)
            verification_log = VerificationLog()
            
            # Business check setup
            do_business_check = self.business_check_var.get()
            serper_key = self.api_key_var.get().strip()
            if do_business_check and serper_key:
                business_checker = SerperBusinessChecker(serper_key)
                logger.info("Business checking enabled with Serper API")
            elif do_business_check and not serper_key:
                logger.warning("Business check enabled but no Serper API key provided - skipping")
                do_business_check = False
            
            # API Mode with 2captcha
            twocaptcha_key = self.twocaptcha_key_var.get().strip()
            if not twocaptcha_key:
                self._update_status("Error: 2Captcha API key required")
                logger.error("2Captcha API key is required")
                self._finish_verification()
                return
            
            # Parse proxies
            proxy_text = self.proxy_var.get().strip()
            proxies = [p.strip() for p in proxy_text.split(",") if p.strip()] if proxy_text else None
            
            api_verifier = LNNTEApiVerifier(
                twocaptcha_api_key=twocaptcha_key,
                proxies=proxies,
                status_callback=lambda msg: self._update_captcha_status(msg)
            )
            logger.info("Using API mode with 2captcha")
            if proxies:
                logger.info(f"Using {len(proxies)} proxies for rotation")
            
            total = len(entries)
            for i, entry in enumerate(entries):
                if self.should_stop:
                    logger.info("Verification stopped by user")
                    break
                
                phone = entry['normalized_phone']
                self._update_progress(i + 1, total, f"Verifying {phone}")
                
                # Business check with Société fuzzy matching
                business_result = None
                if do_business_check and business_checker:
                    # Get Société field from original data for fuzzy matching
                    row_index = entry['row_index']
                    societe = ""
                    if row_index in df.index:
                        societe = str(df.at[row_index, 'Société']) if 'Société' in df.columns else ""
                        if societe == 'nan':
                            societe = ""
                    
                    logger.info(f"Checking if {phone} is a business (Société: {societe or 'N/A'})...")
                    business_result = business_checker.check_phone(phone, societe)
                    if business_result.status.value == "Business":
                        match_info = f" (match: {business_result.match_score:.0f}%)" if business_result.societe_matched else ""
                        logger.info(f"  -> Business: {business_result.business_name or 'Yes'}{match_info}")
                    else:
                        logger.info(f"  -> {business_result.status.value}")
                
                # LNNTE verification via API
                self._update_captcha_status("Verifying via API...")
                api_result = api_verifier.verify_phone(phone)
                result = VerificationResult(
                    phone=api_result.phone,
                    status=VerificationStatus(api_result.status.value),
                    raw_message=api_result.raw_response,
                    error=api_result.error
                )
                
                output_processor.add_result(
                    entry['row_index'],
                    phone,
                    entry['source_type'],
                    result,
                    business_result
                )
                
                verification_log.log_attempt(phone, result.status.value, result.error)
                
                self._update_captcha_status("Ready for next")
            
            output_path = OutputProcessor.generate_output_filename(
                self.input_file,
                "_verified"
            )
            
            output_format = self.output_format_var.get()
            saved_path = output_processor.save_output(output_path, output_format)
            self.output_file = saved_path
            
            log_path = verification_log.save_log(
                str(Path(self.input_file).parent / f"verification_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            )
            
            summary = output_processor.get_summary()
            logger.info(f"Verification complete!")
            logger.info(f"Results: {summary['on_list']} on list, {summary['not_on_list']} not on list, {summary['unknown']} unknown")
            logger.info(f"Output saved to: {saved_path}")
            logger.info(f"Log saved to: {log_path}")
            
            self._update_status(f"Complete! Output saved to: {saved_path}")
            self._update_progress(total, total, "Complete")
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Verification Complete",
                f"Verified {summary['verified_rows']} phone numbers.\n\n"
                f"On list: {summary['on_list']}\n"
                f"Not on list: {summary['not_on_list']}\n"
                f"Unknown: {summary['unknown']}\n\n"
                f"Output saved to:\n{saved_path}"
            ))
            
        except Exception as e:
            logger.error(f"Verification error: {e}")
            self._update_status(f"Error: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Verification failed:\n{str(e)}"))
        
        finally:
            self._finish_verification()
    
    def _finish_verification(self):
        """Reset UI state after verification completes."""
        def reset():
            self.is_running = False
            self.should_stop = False
            self.start_btn.configure(state='normal')
            self.stop_btn.configure(state='disabled')
            self.browse_btn.configure(state='normal')
            self._update_captcha_status("No CAPTCHA pending")
        self.root.after(0, reset)
    
    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


def main():
    """Entry point for the application."""
    app = LNNTEVerifierApp()
    app.run()


if __name__ == "__main__":
    main()
