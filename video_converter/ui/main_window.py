"""
Main Window Module
Professional GUI for video conversion
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
    
    # Color scheme - Professional dark theme
    COLORS = {
        "bg_primary": "#1e1e2e",
        "bg_secondary": "#2d2d3f",
        "bg_tertiary": "#383850",
        "accent": "#7c3aed",
        "accent_hover": "#8b5cf6",
        "success": "#10b981",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "border": "#4b5563",
    }
    
    def __init__(self, root: Tk):
        """
        Initialize Main Window
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("Video Converter Pro")
        self.root.geometry("950x750")
        self.root.minsize(800, 600)
        
        # Apply dark theme
        self.root.configure(bg=self.COLORS["bg_primary"])
        
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
        self.progress_queue = queue.Queue()

        self._batch_idx = 0
        self._batch_total = 0
        self._batch_filename = ""
        
        # Apply custom styles
        self.setup_styles()
        
        # Build UI
        self.create_widgets()
        self.update_log_display()
        self.update_progress_display()
        
        # Load config
        self.load_config_to_ui()
    
    def setup_styles(self):
        """Setup custom ttk styles"""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure main frame
        style.configure(".", 
            background=self.COLORS["bg_primary"],
            foreground=self.COLORS["text_primary"],
            font=("Segoe UI", 10)
        )
        
        # Configure LabelFrame
        style.configure("TLabelframe",
            background=self.COLORS["bg_secondary"],
            foreground=self.COLORS["text_primary"],
            bordercolor=self.COLORS["border"],
            lightcolor=self.COLORS["bg_secondary"],
            darkcolor=self.COLORS["bg_secondary"]
        )
        style.configure("TLabelframe.Label",
            background=self.COLORS["bg_secondary"],
            foreground=self.COLORS["accent"],
            font=("Segoe UI", 11, "bold")
        )
        
        # Configure Combobox
        style.configure("TCombobox",
            background=self.COLORS["bg_tertiary"],
            foreground=self.COLORS["text_primary"],
            fieldbackground=self.COLORS["bg_tertiary"],
            bordercolor=self.COLORS["border"],
            lightcolor=self.COLORS["bg_tertiary"],
            darkcolor=self.COLORS["bg_tertiary"],
        )
        # Configure Progressbar
        style.configure("Horizontal.TProgressbar",
            background=self.COLORS["accent"],
            troughcolor=self.COLORS["bg_tertiary"],
            bordercolor=self.COLORS["border"],
            lightcolor=self.COLORS["accent"],
            darkcolor=self.COLORS["accent"]
        )
        
        # Configure Checkbutton
        style.configure("TCheckbutton",
            background=self.COLORS["bg_secondary"],
            foreground=self.COLORS["text_primary"]
        )
        
    def create_widgets(self):
        """Create UI widgets"""
        # Main frame with padding
        main_frame = Frame(self.root, bg=self.COLORS["bg_primary"], padx=15, pady=15)
        main_frame.pack(fill="both", expand=True)
        
        # ==================== HEADER ====================
        header_frame = Frame(main_frame, bg=self.COLORS["bg_primary"])
        header_frame.pack(fill="x", pady=(0, 15))
        
        # Logo/Icon area
        icon_label = Label(
            header_frame,
            text="🎬",
            font=("Segoe UI", 32),
            bg=self.COLORS["bg_primary"],
            fg=self.COLORS["accent"]
        )
        icon_label.pack(side="left", padx=(0, 10))
        
        # Title
        title_frame = Frame(header_frame, bg=self.COLORS["bg_primary"])
        title_frame.pack(side="left")
        
        Label(
            title_frame,
            text="Video Converter Pro",
            font=("Segoe UI", 20, "bold"),
            bg=self.COLORS["bg_primary"],
            fg=self.COLORS["text_primary"]
        ).pack(anchor="w")
        
        Label(
            title_frame,
            text="Professional Video Batch Converter",
            font=("Segoe UI", 10),
            bg=self.COLORS["bg_primary"],
            fg=self.COLORS["text_secondary"]
        ).pack(anchor="w")
        
        # ==================== FILE SELECTION ====================
        file_frame = self.create_section_frame(main_frame, "📁 Input Files")
        
        # File selection buttons
        btn_frame = Frame(file_frame, bg=self.COLORS["bg_secondary"])
        btn_frame.pack(fill="x", pady=(0, 10))
        
        self.create_modern_button(
            btn_frame, "Select Files", self.select_files,
            icon="📄"
        ).pack(side="left", padx=(0, 10))
        
        self.create_modern_button(
            btn_frame, "Select Folder", self.select_folder,
            icon="📂"
        ).pack(side="left", padx=(0, 10))
        
        # File info display
        self.file_count_label = self.create_info_label(
            file_frame, "No files selected"
        )
        
        # ==================== OUTPUT SETTINGS ====================
        output_frame = self.create_section_frame(main_frame, "💾 Output Settings")
        
        output_btn_frame = Frame(output_frame, bg=self.COLORS["bg_secondary"])
        output_btn_frame.pack(fill="x", pady=(0, 10))
        
        self.create_modern_button(
            output_btn_frame, "Choose Output Folder", self.select_output_folder,
            icon="📂"
        ).pack(side="left")
        
        self.output_label = self.create_info_label(output_frame, "No folder selected")
        
        # ==================== CONVERSION SETTINGS ====================
        settings_frame = self.create_section_frame(main_frame, "⚙️ Conversion Settings")
        
        # Settings - use simple pack layout
        self.build_settings_section(settings_frame)
        
        # ==================== CONTROL BUTTONS ====================
        control_frame = Frame(main_frame, bg=self.COLORS["bg_primary"])
        control_frame.pack(fill="x", pady=15)
        
        self.start_button = self.create_primary_button(
            control_frame, "▶ Start Conversion", self.start_conversion
        )
        self.start_button.pack(side="left", padx=(0, 10))
        
        self.stop_button = self.create_danger_button(
            control_frame, "■ Stop", self.stop_conversion
        )
        self.stop_button.pack(side="left")
        
        # ==================== PROGRESS SECTION ====================
        self.create_progress_section(main_frame)
        
        # ==================== LOG SECTION ====================
        self.create_log_section(main_frame)
        
        # ==================== STATUS BAR ====================
        self.status_var = StringVar(value="Ready")
        self.status_label = Label(
            main_frame,
            textvariable=self.status_var,
            bg=self.COLORS["bg_tertiary"],
            fg=self.COLORS["text_secondary"],
            font=("Segoe UI", 9),
            anchor="w",
            padx=10,
            pady=5,
            relief="flat"
        )
        self.status_label.pack(fill="x", pady=(10, 0))
    
    def create_section_frame(self, parent, title):
        """Create a section frame with title"""
        frame = Frame(parent, bg=self.COLORS["bg_secondary"], padx=15, pady=10)
        frame.pack(fill="x", pady=(0, 10))
        
        Label(
            frame,
            text=title,
            font=("Segoe UI", 11, "bold"),
            bg=self.COLORS["bg_secondary"],
            fg=self.COLORS["accent"],
            anchor="w"
        ).pack(fill="x", pady=(0, 10))
        
        inner = Frame(frame, bg=self.COLORS["bg_secondary"])
        inner.pack(fill="x")
        return inner
    
    def create_modern_button(self, parent, text, command, icon=""):
        """Create a modern styled button"""
        btn = Button(
            parent,
            text=f"{icon} {text}" if icon else text,
            command=command,
            font=("Segoe UI", 10),
            bg=self.COLORS["bg_tertiary"],
            fg=self.COLORS["text_primary"],
            activebackground=self.COLORS["accent"],
            activeforeground="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        )
        return btn
    
    def create_primary_button(self, parent, text, command):
        """Create primary action button"""
        btn = Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 11, "bold"),
            bg=self.COLORS["accent"],
            fg="white",
            activebackground=self.COLORS["accent_hover"],
            activeforeground="white",
            relief="flat",
            padx=25,
            pady=10,
            cursor="hand2"
        )
        return btn
    
    def create_danger_button(self, parent, text, command):
        """Create danger/stop button"""
        btn = Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 11, "bold"),
            bg=self.COLORS["danger"],
            fg="white",
            activebackground="#dc2626",
            activeforeground="white",
            relief="flat",
            padx=25,
            pady=10,
            cursor="hand2",
            state="disabled"
        )
        return btn
    
    def create_info_label(self, parent, text):
        """Create an info display label"""
        label = Label(
            parent,
            text=text,
            font=("Segoe UI", 10),
            bg=self.COLORS["bg_secondary"],
            fg=self.COLORS["text_secondary"],
            anchor="w",
            padx=5
        )
        label.pack(fill="x", pady=5)
        return label
    
    def create_setting_row(self, parent, label_text, row, widget_frame):
        """Create a settings row with label and widget"""
        Label(
            parent,
            text=label_text,
            font=("Segoe UI", 10),
            bg=self.COLORS["bg_secondary"],
            fg=self.COLORS["text_secondary"],
            width=15,
            anchor="w"
        ).grid(row=row, column=0, padx=5, pady=8, sticky="w")
        
        widget_frame.grid(row=row, column=1, columnspan=2, sticky="w", padx=5, pady=5)
    
    def create_resolution_selector(self):
        """Create resolution selector"""
        frame = Frame(bg=self.COLORS["bg_secondary"])
        
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
        
        ttk.Combobox(
            frame,
            textvariable=self.resolution_var,
            values=list(RESOLUTION_PRESETS.keys()),
            state="readonly",
            width=20
        ).pack(side="left", padx=(0, 10))
        
        Label(frame, text="W:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.width_var = StringVar(value=str(self.config.get("width", 1280)))
        ttk.Entry(frame, textvariable=self.width_var, width=8).pack(side="left", padx=5)
        
        Label(frame, text="H:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.height_var = StringVar(value=str(self.config.get("height", 720)))
        ttk.Entry(frame, textvariable=self.height_var, width=8).pack(side="left", padx=5)
        
        return frame
    
    def create_encoder_selector(self):
        """Create encoder selector"""
        frame = Frame(bg=self.COLORS["bg_secondary"])
        
        self.encoder_var = StringVar(value=self.config.get("encoder", "auto"))
        ttk.Combobox(
            frame,
            textvariable=self.encoder_var,
            values=["auto"] + self.encoder_detector.detect_available_encoders(),
            state="readonly",
            width=20
        ).pack(side="left")
        
        return frame
    
    def create_quality_row(self):
        """Create quality settings row (bitrate + CRF)"""
        frame = Frame(bg=self.COLORS["bg_secondary"])
        
        Label(frame, text="Bitrate:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.bitrate_var = StringVar(value=self.config.get("bitrate", "1000k"))
        ttk.Entry(frame, textvariable=self.bitrate_var, width=10).pack(side="left", padx=5)
        
        self.use_crf_var = BooleanVar(value=self.config.get("use_crf", False))
        ttk.Checkbutton(
            frame,
            text="Use CRF",
            variable=self.use_crf_var
        ).pack(side="left", padx=(15, 5))
        
        Label(frame, text="CRF:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.crf_var = IntVar(value=self.config.get("crf", 23))
        ttk.Spinbox(frame, from_=0, to=51, width=5, textvariable=self.crf_var).pack(side="left", padx=5)
        
        return frame
    
    def create_performance_row(self):
        """Create performance settings row (preset + threads)"""
        frame = Frame(bg=self.COLORS["bg_secondary"])
        
        Label(frame, text="Preset:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.preset_var = StringVar(value=self.config.get("preset", "medium"))
        ttk.Combobox(
            frame,
            textvariable=self.preset_var,
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            state="readonly",
            width=10
        ).pack(side="left", padx=5)
        
        Label(frame, text="Threads:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left", padx=(20, 5))
        self.threads_var = StringVar(value=str(self.config.get("threads", 1)))
        ttk.Combobox(
            frame,
            textvariable=self.threads_var,
            values=["1", "2", "4", "8"],
            state="readonly",
            width=5
        ).pack(side="left", padx=5)
        
        return frame
    
    def create_options_row(self, parent, row):
        """Create options row"""
        frame = Frame(parent, bg=self.COLORS["bg_secondary"])
        frame.grid(row=row, column=0, columnspan=3, sticky="w", padx=5, pady=5)
        
        self.delete_original_var = BooleanVar(value=self.config.get("delete_original", True))
        ttk.Checkbutton(
            frame,
            text="Delete original files after successful conversion",
            variable=self.delete_original_var
        ).pack(side="left")
    
    def build_settings_section(self, parent):
        """Build settings section with pack layout"""
        # Resolution
        row = Frame(parent, bg=self.COLORS["bg_secondary"])
        row.pack(fill="x", pady=3)
        Label(row, text="Resolution:", width=12, anchor="w", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left", padx=5)
        self.resolution_var = StringVar(value="720p (1280x720)")
        
        RESOLUTION_PRESETS = {
            "Original": (0, 0), "4K (3840x2160)": (3840, 2160),
            "1080p (1920x1080)": (1920, 1080), "720p (1280x720)": (1280, 720),
            "480p (854x480)": (854, 480), "360p (640x360)": (640, 360),
        }
        
        def on_res_change(*args):
            sel = self.resolution_var.get()
            if sel in RESOLUTION_PRESETS:
                w, h = RESOLUTION_PRESETS[sel]
                if w > 0:
                    self.width_var.set(str(w))
                    self.height_var.set(str(h))
        
        self.resolution_var.trace("w", on_res_change)
        ttk.Combobox(row, textvariable=self.resolution_var, values=list(RESOLUTION_PRESETS.keys()), state="readonly", width=18).pack(side="left", padx=5)
        
        Label(row, text="W:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.width_var = StringVar(value=str(self.config.get("width", 1280)))
        ttk.Entry(row, textvariable=self.width_var, width=6).pack(side="left", padx=3)
        Label(row, text="H:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.height_var = StringVar(value=str(self.config.get("height", 720)))
        ttk.Entry(row, textvariable=self.height_var, width=6).pack(side="left", padx=3)
        
        # Encoder
        row = Frame(parent, bg=self.COLORS["bg_secondary"])
        row.pack(fill="x", pady=3)
        Label(row, text="Encoder:", width=12, anchor="w", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left", padx=5)
        self.encoder_var = StringVar(value=self.config.get("encoder", "auto"))
        ttk.Combobox(row, textvariable=self.encoder_var, values=["auto"] + self.encoder_detector.detect_available_encoders(), state="readonly", width=20).pack(side="left", padx=5)
        
        # Quality
        row = Frame(parent, bg=self.COLORS["bg_secondary"])
        row.pack(fill="x", pady=3)
        Label(row, text="Quality:", width=12, anchor="w", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left", padx=5)
        Label(row, text="Bitrate:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.bitrate_var = StringVar(value=self.config.get("bitrate", "1000k"))
        ttk.Entry(row, textvariable=self.bitrate_var, width=8).pack(side="left", padx=3)
        self.use_crf_var = BooleanVar(value=self.config.get("use_crf", False))
        ttk.Checkbutton(row, text="CRF", variable=self.use_crf_var).pack(side="left", padx=10)
        Label(row, text="Value:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.crf_var = IntVar(value=self.config.get("crf", 23))
        ttk.Spinbox(row, from_=0, to=51, width=4, textvariable=self.crf_var).pack(side="left", padx=3)
        
        # Performance
        row = Frame(parent, bg=self.COLORS["bg_secondary"])
        row.pack(fill="x", pady=3)
        Label(row, text="Performance:", width=12, anchor="w", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left", padx=5)
        Label(row, text="Preset:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left")
        self.preset_var = StringVar(value=self.config.get("preset", "medium"))
        ttk.Combobox(row, textvariable=self.preset_var, values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"], state="readonly", width=10).pack(side="left", padx=3)
        Label(row, text="Threads:", bg=self.COLORS["bg_secondary"], fg=self.COLORS["text_secondary"]).pack(side="left", padx=(15, 3))
        self.threads_var = StringVar(value=str(self.config.get("threads", 1)))
        ttk.Combobox(row, textvariable=self.threads_var, values=["1", "2", "4", "8"], state="readonly", width=4).pack(side="left")
        
        # Options
        row = Frame(parent, bg=self.COLORS["bg_secondary"])
        row.pack(fill="x", pady=3)
        self.delete_original_var = BooleanVar(value=self.config.get("delete_original", True))
        ttk.Checkbutton(row, text="Delete original files after successful conversion", variable=self.delete_original_var).pack(side="left", padx=5)
        
    def create_progress_section(self, parent):
        """Create progress display section"""
        progress_frame = Frame(parent, bg=self.COLORS["bg_secondary"], padx=15, pady=10)
        progress_frame.pack(fill="x", pady=(0, 10))
        
        # Overall progress
        Label(
            progress_frame,
            text="📊 Overall Progress",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS["bg_secondary"],
            fg=self.COLORS["accent"],
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.overall_progress_var = StringVar(value="Overall: 0/0  0.0%")
        Label(
            progress_frame,
            textvariable=self.overall_progress_var,
            font=("Segoe UI", 9),
            bg=self.COLORS["bg_secondary"],
            fg=self.COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 3))
        
        self.overall_progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            maximum=100,
            length=100
        )
        self.overall_progress_bar.pack(fill="x", pady=(0, 10))
        
        # File progress
        Label(
            progress_frame,
            text="📄 Current File",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS["bg_secondary"],
            fg=self.COLORS["accent"],
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.file_progress_var = StringVar(value="File: 0.0%")
        Label(
            progress_frame,
            textvariable=self.file_progress_var,
            font=("Segoe UI", 9),
            bg=self.COLORS["bg_secondary"],
            fg=self.COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 3))
        
        self.file_progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            maximum=100,
            length=100
        )
        self.file_progress_bar.pack(fill="x")
    
    def create_log_section(self, parent):
        """Create log display section"""
        log_frame = Frame(parent, bg=self.COLORS["bg_secondary"], padx=15, pady=10)
        log_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        Label(
            log_frame,
            text="📋 Log",
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS["bg_secondary"],
            fg=self.COLORS["accent"],
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        log_text_frame = Frame(log_frame, bg=self.COLORS["bg_secondary"])
        log_text_frame.pack(fill="both", expand=True)
        
        self.log_text = Text(
            log_text_frame,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
            bg=self.COLORS["bg_primary"],
            fg=self.COLORS["text_primary"],
            relief="flat",
            padx=10,
            pady=10
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        
        log_scrollbar = Scrollbar(log_text_frame, command=self.log_text.yview)
        log_scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=log_scrollbar.set)
    
    def log(self, message: str, level: str = "INFO"):
        """Log message"""
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
    
    def get_video_info_summary(self, file_path: str) -> str:
        """Get video info summary for display"""
        from ..core.converter import VideoConverter
        try:
            vc = VideoConverter()
            info = vc.get_video_info(file_path)
            if info.get('width', 0) > 0:
                return f"{info['width']}x{info['height']} {info.get('codec', '?')} {info.get('format', '?')}"
        except Exception:
            pass
        return ""
    
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
            
            video_info = ""
            if files:
                video_info = self.get_video_info_summary(files[0])
            
            if video_info:
                self.file_count_label.config(
                    text=f"✓ {len(self.input_files)} files selected | {video_info}"
                )
            else:
                self.file_count_label.config(
                    text=f"✓ {len(self.input_files)} files selected"
                )
            self.log(f"Selected {len(self.input_files)} files")
    
    def select_folder(self):
        """Select folder (batch processing)"""
        folder = filedialog.askdirectory(title="Select Folder with Videos")
        if folder:
            video_files = get_video_files(folder)
            if video_files:
                self.input_files = [str(f) for f in video_files]
                
                video_info = ""
                if video_files:
                    video_info = self.get_video_info_summary(str(video_files[0]))
                
                if video_info:
                    self.file_count_label.config(
                        text=f"✓ {len(self.input_files)} files in folder | {video_info}"
                    )
                else:
                    self.file_count_label.config(
                        text=f"✓ {len(self.input_files)} files in folder"
                    )
                self.log(f"Found {len(self.input_files)} video files in folder")
            else:
                messagebox.showwarning("Warning", "No video files found in the folder")
    
    def select_output_folder(self):
        """Select output folder"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)
            self.output_label.config(text=f"✓ {folder}")
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
            self.config.set("threads", int(self.threads_var.get()))
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
        
        self.save_ui_to_config()
        
        self.is_converting = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.stop_event.clear()
        
        self.converter = VideoConverter(
            encoder=self.encoder_var.get(),
            width=int(self.width_var.get()),
            height=int(self.height_var.get()),
            bitrate=self.bitrate_var.get(),
            threads=int(self.threads_var.get()),
            timeout=self.config.get("timeout", 300),
            sequence_manager=self.sequence_manager,
            preset=self.preset_var.get(),
            use_crf=self.use_crf_var.get(),
            crf=self.crf_var.get()
        )
        
        thread = threading.Thread(target=self.convert_thread)
        thread.daemon = True
        thread.start()
    
    def convert_thread(self):
        """Conversion thread"""
        try:
            self.log("Starting batch conversion...")
            self.status_var.set("Converting...")
            
            self.progress_queue.put({"type": "start", "total": len(self.input_files)})
            
            def file_progress_callback(progress: dict):
                payload = {"type": "file_progress"}
                payload.update(progress)
                self.progress_queue.put(payload)
            
            def progress_callback(current: int, total: int, filename: str):
                filename_only = Path(filename).name
                self.log(f"[{current+1}/{total}] Processing: {filename_only}")
                self.progress_queue.put(
                    {"type": "batch_start", "idx": current, "total": total, "filename": filename}
                )
            
            result = self.converter.convert_batch(
                self.input_files,
                self.output_folder.get(),
                delete_original=self.delete_original_var.get(),
                progress_callback=progress_callback,
                file_progress_callback=file_progress_callback
            )
            
            self.progress_queue.put({"type": "done", "total": result.get("total", 0)})
            self.status_var.set(
                f"Complete: {result['success']}/{result['total']} succeeded, {result['failed']} failed"
            )
            
            self.log(f"Conversion complete: Success {result['success']}, Failed {result['failed']}")
            
            if result['failed'] > 0:
                self.log("Failed files:", "WARNING")
                for item in result['failed_files']:
                    if isinstance(item, tuple):
                        self.log(f"  - {item[0]}: {item[1]}", "ERROR")
                    else:
                        self.log(f"  - {item}", "ERROR")
                
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
            self.is_converting = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.progress_queue.put({"type": "reset"})
    
    def stop_conversion(self):
        """Stop conversion"""
        if self.converter:
            self.converter.stop()
            self.stop_event.set()
            self.log("Stopping conversion...", "WARNING")
            self.status_var.set("Stopping...")
    
    def update_progress_display(self):
        """Update progress bars from queue (main thread only)"""
        try:
            while True:
                event = self.progress_queue.get_nowait()
                etype = event.get("type")

                if etype == "start":
                    self._batch_idx = 0
                    self._batch_total = int(event.get("total", 0) or 0)
                    self._batch_filename = ""
                    self.overall_progress_bar["value"] = 0
                    self.file_progress_bar["value"] = 0
                    self.overall_progress_var.set(f"Overall: 0/{self._batch_total}  0.0%")
                    self.file_progress_var.set("File: 0.0%")

                elif etype == "batch_start":
                    self._batch_idx = int(event.get("idx", 0) or 0)
                    self._batch_total = int(event.get("total", 0) or 0)
                    self._batch_filename = str(event.get("filename", "") or "")

                    self.file_progress_bar["value"] = 0
                    filename_only = Path(self._batch_filename).name if self._batch_filename else ""
                    self.file_progress_var.set(f"File: 0.0%  {filename_only}")

                    overall = (self._batch_idx / self._batch_total) * 100 if self._batch_total else 0
                    self.overall_progress_bar["value"] = overall
                    self.overall_progress_var.set(
                        f"Overall: {self._batch_idx + 1}/{self._batch_total}  {overall:.1f}%"
                    )

                elif etype == "file_progress":
                    percent = event.get("percent", 0) or 0
                    try:
                        percent = float(percent)
                    except Exception:
                        percent = 0.0
                    percent = max(0.0, min(100.0, percent))

                    current_time = event.get("time", 0) or 0
                    try:
                        current_time = float(current_time)
                    except Exception:
                        current_time = 0.0
                    mins = int(current_time // 60)
                    secs = int(current_time % 60)
                    time_str = f"{mins:02d}:{secs:02d}"

                    info = event.get("video_info", {}) or {}
                    src_format = info.get("format", "")
                    src_codec = info.get("codec", "")
                    src_res = ""
                    if info.get("width", 0) and info.get("height", 0):
                        src_res = f"{info.get('width', 0)}x{info.get('height', 0)}"

                    filename_only = Path(self._batch_filename).name if self._batch_filename else ""
                    details_parts = [p for p in [src_format, src_res, src_codec] if p]
                    details = " ".join(details_parts)

                    self.file_progress_bar["value"] = percent
                    self.file_progress_var.set(
                        f"File: {percent:.1f}%  {time_str}  {filename_only}" + (f"  ({details})" if details else "")
                    )

                    overall = ((self._batch_idx + percent / 100.0) / self._batch_total) * 100 if self._batch_total else 0
                    overall = max(0.0, min(100.0, overall))
                    self.overall_progress_bar["value"] = overall
                    self.overall_progress_var.set(
                        f"Overall: {self._batch_idx + 1}/{self._batch_total}  {overall:.1f}%"
                    )

                elif etype == "done":
                    self.file_progress_bar["value"] = 100
                    self.overall_progress_bar["value"] = 100
                    total = int(event.get("total", self._batch_total) or 0)
                    self.overall_progress_var.set(f"Overall: {total}/{total}  100.0%")
                    self.file_progress_var.set("File: 100.0%")

                elif etype == "reset":
                    self.overall_progress_bar["value"] = 0
                    self.file_progress_bar["value"] = 0
                    self.overall_progress_var.set("Overall: 0/0  0.0%")
                    self.file_progress_var.set("File: 0.0%")

        except queue.Empty:
            pass

        self.root.after(100, self.update_progress_display)
    
    def run(self):
        """Run main loop"""
        self.root.mainloop()
