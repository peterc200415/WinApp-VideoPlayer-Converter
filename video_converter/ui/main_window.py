"""
Main Window Module
Modern GUI for video conversion
"""
import os
import queue
import threading
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Button, Text, Scrollbar,
    filedialog, ttk, StringVar, IntVar, BooleanVar, messagebox
)
from typing import List, Optional, Callable

from ..core.converter import VideoConverter
from ..core.config import Config
from ..core.encoder_detector import EncoderDetector
from ..core.sequence_manager import SequenceManager
from ..utils.file_utils import format_file_size, get_video_files


class MainWindow:
    """Main Window Class"""
    
    def __init__(self, root: Tk):
        """
        Initialize Main Window
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Video Converter")
        self.root.geometry("900x700")
        
        # Initialize components
        self.config = Config()
        self.encoder_detector = EncoderDetector()
        self.sequence_manager = SequenceManager(
            self.config.get("sequence_file", "sequence_number.txt")
        )
        self.converter: Optional[VideoConverter] = None
        
        # State variables
        self.input_files: List[str] = []
        self.output_folder: StringVar = StringVar()
        self.is_converting = False
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        
        # Build UI
        self.create_widgets()
        self.update_log_display()
        
        # Load config
        self.load_config_to_ui()
    
    def create_widgets(self):
        """Create UI widgets"""
        # Main frame
        main_frame = Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = Label(
            main_frame,
            text="Video Converter",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # File selection area
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding=10)
        file_frame.pack(fill="x", pady=5)
        
        Button(
            file_frame,
            text="Select Files",
            command=self.select_files
        ).pack(side="left", padx=5)
        
        Button(
            file_frame,
            text="Select Folder",
            command=self.select_folder
        ).pack(side="left", padx=5)
        
        self.file_count_label = Label(
            file_frame,
            text="Selected: 0 files",
            fg="gray"
        )
        self.file_count_label.pack(side="left", padx=10)
        
        # Output folder selection
        output_frame = ttk.LabelFrame(main_frame, text="Output Settings", padding=10)
        output_frame.pack(fill="x", pady=5)
        
        Button(
            output_frame,
            text="Select Output Folder",
            command=self.select_output_folder
        ).pack(side="left", padx=5)
        
        self.output_label = Label(
            output_frame,
            textvariable=self.output_folder,
            fg="gray"
        )
        self.output_label.pack(side="left", padx=10)
        
        # Conversion settings area
        settings_frame = ttk.LabelFrame(main_frame, text="Conversion Settings", padding=10)
        settings_frame.pack(fill="x", pady=5)
        
        # Resolution setting
        res_frame = Frame(settings_frame)
        res_frame.pack(fill="x", pady=2)
        
        Label(res_frame, text="Resolution:").pack(side="left", padx=5)
        
        RESOLUTION_PRESETS = {
            "Original": (0, 0),
            "4K (3840x2160)": (3840, 2160),
            "1080p (1920x1080)": (1920, 1080),
            "720p (1280x720)": (1280, 720),
            "480p (854x480)": (854, 480),
            "360p (640x360)": (640, 360),
        }
        
        self.resolution_var = StringVar(value="720p (1280x720)")
        
        def on_resolution_change(*args):
            selected = self.resolution_var.get()
            if selected in RESOLUTION_PRESETS:
                w, h = RESOLUTION_PRESETS[selected]
                if w > 0 and h > 0:
                    self.width_var.set(str(w))
                    self.height_var.set(str(h))
        
        self.resolution_var.trace("w", on_resolution_change)
        res_combo = ttk.Combobox(
            res_frame,
            textvariable=self.resolution_var,
            values=list(RESOLUTION_PRESETS.keys()),
            state="readonly",
            width=20
        )
        res_combo.pack(side="left", padx=5)
        
        Label(res_frame, text="W:").pack(side="left", padx=10)
        self.width_var = StringVar(value=str(self.config.get("width", 1280)))
        width_entry = ttk.Entry(res_frame, textvariable=self.width_var, width=8)
        width_entry.pack(side="left", padx=5)
        
        Label(res_frame, text="H:").pack(side="left", padx=5)
        self.height_var = StringVar(value=str(self.config.get("height", 720)))
        height_entry = ttk.Entry(res_frame, textvariable=self.height_var, width=8)
        height_entry.pack(side="left", padx=5)
        
        # Bitrate setting
        bitrate_frame = Frame(settings_frame)
        bitrate_frame.pack(fill="x", pady=2)
        
        Label(bitrate_frame, text="Bitrate:").pack(side="left", padx=5)
        self.bitrate_var = StringVar(value=self.config.get("bitrate", "1000k"))
        bitrate_entry = ttk.Entry(bitrate_frame, textvariable=self.bitrate_var, width=10)
        bitrate_entry.pack(side="left", padx=5)
        
        # CRF mode
        self.use_crf_var = BooleanVar(value=self.config.get("use_crf", False))
        ttk.Checkbutton(
            bitrate_frame,
            text="Use CRF Quality Mode",
            variable=self.use_crf_var
        ).pack(side="left", padx=10)
        
        Label(bitrate_frame, text="CRF:").pack(side="left", padx=5)
        self.crf_var = IntVar(value=self.config.get("crf", 23))
        crf_spin = ttk.Spinbox(bitrate_frame, from_=0, to=51, width=5, textvariable=self.crf_var)
        crf_spin.pack(side="left", padx=5)
        
        # Encoder selection
        encoder_frame = Frame(settings_frame)
        encoder_frame.pack(fill="x", pady=2)
        
        Label(encoder_frame, text="Encoder:").pack(side="left", padx=5)
        self.encoder_var = StringVar(value=self.config.get("encoder", "auto"))
        encoder_combo = ttk.Combobox(
            encoder_frame,
            textvariable=self.encoder_var,
            values=["auto"] + self.encoder_detector.detect_available_encoders(),
            state="readonly",
            width=15
        )
        encoder_combo.pack(side="left", padx=5)
        
        # Preset selection
        preset_frame = Frame(settings_frame)
        preset_frame.pack(fill="x", pady=2)
        
        Label(preset_frame, text="Preset:").pack(side="left", padx=5)
        self.preset_var = StringVar(value=self.config.get("preset", "medium"))
        preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.preset_var,
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            state="readonly",
            width=10
        )
        preset_combo.pack(side="left", padx=5)
        
        # Threads
        threads_frame = Frame(settings_frame)
        threads_frame.pack(fill="x", pady=2)
        
        Label(threads_frame, text="Threads:").pack(side="left", padx=5)
        self.threads_var = IntVar(value=self.config.get("threads", 1))
        threads_combo = ttk.Combobox(
            threads_frame,
            textvariable=self.threads_var,
            values=[1, 2, 4, 8],
            state="readonly",
            width=10
        )
        threads_combo.pack(side="left", padx=5)
        
        # Options
        options_frame = Frame(settings_frame)
        options_frame.pack(fill="x", pady=2)
        
        self.delete_original_var = BooleanVar(
            value=self.config.get("delete_original", True)
        )
        ttk.Checkbutton(
            options_frame,
            text="Delete original files after conversion",
            variable=self.delete_original_var
        ).pack(side="left", padx=5)
        
        # Control buttons
        control_frame = Frame(main_frame)
        control_frame.pack(fill="x", pady=10)
        
        self.start_button = Button(
            control_frame,
            text="Start Conversion",
            command=self.start_conversion,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5
        )
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = Button(
            control_frame,
            text="Stop",
            command=self.stop_conversion,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)
        
        # Progress
        self.progress_var = StringVar(value="Ready")
        self.progress_label = Label(
            control_frame,
            textvariable=self.progress_var,
            font=("Arial", 9)
        )
        self.progress_label.pack(side="left", padx=10)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode="determinate",
            maximum=100
        )
        self.progress_bar.pack(fill="x", pady=5)
        
        # Log display area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding=5)
        log_frame.pack(fill="both", expand=True, pady=5)
        
        # Log text area
        log_text_frame = Frame(log_frame)
        log_text_frame.pack(fill="both", expand=True)
        
        self.log_text = Text(
            log_text_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 9)
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        
        log_scrollbar = Scrollbar(log_text_frame, command=self.log_text.yview)
        log_scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # Status bar
        self.status_var = StringVar(value="Ready")
        status_label = Label(
            main_frame,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padx=5
        )
        status_label.pack(fill="x", pady=(5, 0))
    
    def log(self, message: str, level: str = "INFO"):
        """
        Log message
        
        Args:
            message: Message content
            level: Log level
        """
        self.log_queue.put(f"[{level}] {message}")
    
    def update_log_display(self):
        """Update log display"""
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_log_display)
    
    def select_files(self):
        """Select video files"""
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self.input_files = list(files)
            self.file_count_label.config(
                text=f"Selected: {len(self.input_files)} files"
            )
            self.log(f"Selected {len(self.input_files)} files")
    
    def select_folder(self):
        """Select folder (batch processing)"""
        folder = filedialog.askdirectory(title="Select Folder with Videos")
        if folder:
            video_files = get_video_files(folder)
            if video_files:
                self.input_files = [str(f) for f in video_files]
                self.file_count_label.config(
                    text=f"Selected: {len(self.input_files)} files"
                )
                self.log(f"Found {len(self.input_files)} video files in folder")
            else:
                messagebox.showwarning("Warning", "No video files found in the folder")
    
    def select_output_folder(self):
        """Select output folder"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
            self.log(f"Output folder: {folder}")
    
    def load_config_to_ui(self):
        """Load config to UI"""
        pass
    
    def save_ui_to_config(self):
        """Save UI settings to config"""
        try:
            self.config.set("width", int(self.width_var.get()))
            self.config.set("height", int(self.height_var.get()))
            self.config.set("bitrate", self.bitrate_var.get())
            self.config.set("encoder", self.encoder_var.get())
            self.config.set("threads", self.threads_var.get())
            self.config.set("delete_original", self.delete_original_var.get())
            self.config.set("preset", self.preset_var.get())
            self.config.set("use_crf", self.use_crf_var.get())
            self.config.set("crf", self.crf_var.get())
            self.config.save_config()
        except ValueError as e:
            self.log(f"Config error: {e}", "ERROR")
    
    def start_conversion(self):
        """Start conversion"""
        if not self.input_files:
            messagebox.showwarning("Warning", "Please select files to convert")
            return
        
        if not self.output_folder.get():
            messagebox.showwarning("Warning", "Please select output folder")
            return
        
        # Save settings
        self.save_ui_to_config()
        
        # Update UI state
        self.is_converting = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.stop_event.clear()
        
        # Create converter
        self.converter = VideoConverter(
            encoder=self.encoder_var.get(),
            width=int(self.width_var.get()),
            height=int(self.height_var.get()),
            bitrate=self.bitrate_var.get(),
            threads=self.threads_var.get(),
            timeout=self.config.get("timeout", 300),
            sequence_manager=self.sequence_manager,
            preset=self.preset_var.get(),
            use_crf=self.use_crf_var.get(),
            crf=self.crf_var.get()
        )
        
        # Start conversion thread
        thread = threading.Thread(target=self.convert_thread)
        thread.daemon = True
        thread.start()
    
    def convert_thread(self):
        """Conversion thread"""
        try:
            self.log("Starting batch conversion...")
            self.status_var.set("Converting...")
            
            current_file_info = {}
            
            def file_progress_callback(progress: dict):
                """Single file progress callback"""
                info = progress.get("video_info", {})
                percent = progress.get("percent", 0)
                current_time = progress.get("time", 0)
                
                # Format time
                mins = int(current_time // 60)
                secs = int(current_time % 60)
                time_str = f"{mins:02d}:{secs:02d}"
                
                # Get source format
                src_format = info.get("format", "unknown")
                src_codec = info.get("codec", "")
                src_res = f"{info.get('width', 0)}x{info.get('height', 0)}"
                
                # Calculate total progress
                total_progress = ((current_file_info.get("idx", 0) + percent / 100) / current_file_info.get("total", 1)) * 100
                
                self.progress_bar["value"] = total_progress
                self.progress_var.set(
                    f"[{current_file_info.get('idx', 0)+1}/{current_file_info.get('total', 1)}] "
                    f"{percent:.1f}% ({time_str}) - {src_format} {src_res}"
                )
            
            def progress_callback(current: int, total: int, filename: str):
                """Batch progress callback"""
                current_file_info["idx"] = current
                current_file_info["total"] = total
                filename_only = Path(filename).name
                self.log(f"[{current+1}/{total}] Processing: {filename_only}")
            
            # Run batch conversion
            result = self.converter.convert_batch(
                self.input_files,
                self.output_folder.get(),
                delete_original=self.delete_original_var.get(),
                progress_callback=progress_callback,
                file_progress_callback=file_progress_callback
            )
            
            # Show results
            self.progress_bar["value"] = 100
            self.progress_var.set("Conversion Complete")
            self.status_var.set(
                f"Complete: Success {result['success']}/{result['total']}, "
                f"Failed {result['failed']}"
            )
            
            self.log(f"Conversion complete: Success {result['success']}, Failed {result['failed']}")
            
            if result['failed'] > 0:
                self.log("Failed files:", "WARNING")
                for item in result['failed_files']:
                    if isinstance(item, tuple):
                        self.log(f"  - {item[0]}: {item[1]}", "ERROR")
                    else:
                        self.log(f"  - {item}", "ERROR")
                
                # Show error details
                last_error = self.converter.get_last_error()
                if last_error:
                    self.log("--- Error Details ---", "ERROR")
                    error_lines = last_error.split('\n')
                    for line in error_lines:
                        if 'error' in line.lower() or 'failed' in line.lower() or 'nvenc' in line.lower() or 'driver' in line.lower():
                            self.log(f"  {line}", "ERROR")
            
            messagebox.showinfo(
                "Conversion Complete",
                f"Conversion complete!\nSuccess: {result['success']}\nFailed: {result['failed']}"
            )
            
        except Exception as e:
            self.log(f"Conversion error: {e}", "ERROR")
            messagebox.showerror("Error", f"Error during conversion: {e}")
        finally:
            # Reset UI state
            self.is_converting = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.progress_bar["value"] = 0
    
    def stop_conversion(self):
        """Stop conversion"""
        if self.converter:
            self.converter.stop()
            self.stop_event.set()
            self.log("Stopping conversion...", "WARNING")
            self.status_var.set("Stopping...")
    
    def run(self):
        """Run main loop"""
        self.root.mainloop()
