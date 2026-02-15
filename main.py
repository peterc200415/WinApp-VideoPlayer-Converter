"""
Video Converter - Main Entry Point
"""
import sys
from tkinter import Tk, messagebox

from video_converter.ui.main_window import MainWindow
from video_converter.core.encoder_detector import EncoderDetector


def check_requirements():
    """Check system requirements"""
    detector = EncoderDetector()
    
    if not detector.check_ffmpeg():
        messagebox.showerror(
            "Error",
            "FFmpeg not found!\n\n"
            "Please ensure FFmpeg is installed and in system PATH.\n"
            "Download: https://ffmpeg.org/download.html"
        )
        return False
    
    return True


def main():
    """Main function"""
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Create main window
    root = Tk()
    app = MainWindow(root)
    
    # Run application
    app.run()


if __name__ == "__main__":
    main()
