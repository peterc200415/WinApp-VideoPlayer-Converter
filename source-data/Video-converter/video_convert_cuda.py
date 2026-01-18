import os
import queue
import subprocess
import threading
from tkinter import Tk, filedialog, Text, Scrollbar, Frame, Label, Button, IntVar, OptionMenu
import time

# 文件序号保存路径
SEQUENCE_FILE = "sequence_number.txt"
# 设置超时时间（秒）
TIMEOUT = 300

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Converter")
        self.create_widgets()
        self.process = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.update_log()

    def create_widgets(self):
        frame = Frame(self.root)
        frame.pack(fill="both", expand=True)

        self.text = Text(frame, wrap="word", state="disabled")
        self.text.pack(side="left", fill="both", expand=True)

        scrollbar = Scrollbar(frame, command=self.text.yview)
        scrollbar.pack(side="right", fill="y")
        self.text.config(yscrollcommand=scrollbar.set)

        self.label = Label(self.root, text="")
        self.label.pack()

        button_frame = Frame(self.root)
        button_frame.pack(pady=10)

        self.select_files_button = Button(button_frame, text="Select Files", command=self.select_files)
        self.select_files_button.grid(row=0, column=0, padx=5)

        self.select_output_folder_button = Button(button_frame, text="Select Output Folder", command=self.select_output_folder)
        self.select_output_folder_button.grid(row=0, column=1, padx=5)

        self.start_button = Button(button_frame, text="Start Conversion", command=self.start_conversion)
        self.start_button.grid(row=0, column=2, padx=5)

        self.stop_button = Button(button_frame, text="Stop Conversion", command=self.stop_conversion)
        self.stop_button.grid(row=0, column=3, padx=5)

        self.threads_var = IntVar(value=1)
        self.threads_menu = OptionMenu(button_frame, self.threads_var, 1, 2, 4, 8)
        self.threads_menu.grid(row=0, column=4, padx=5)
        self.threads_label = Label(button_frame, text="Threads")
        self.threads_label.grid(row=0, column=5, padx=5)

    def log(self, message):
        self.log_queue.put(message)

    def update_log(self):
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.text.config(state="normal")
            self.text.insert("end", message + "\n")
            self.text.yview("end")
            self.text.config(state="disabled")
        self.root.after(100, self.update_log)

    def select_files(self):
        self.input_files = filedialog.askopenfilenames(filetypes=[("MP4 files", "*.mp4")])
        self.log(f"Selected files: {self.input_files}")

    def select_output_folder(self):
        self.output_folder = filedialog.askdirectory()
        self.log(f"Selected output folder: {self.output_folder}")

    def start_conversion(self):
        if not hasattr(self, 'input_files') or not self.input_files:
            self.log("No files selected. Exiting.")
            return

        if not hasattr(self, 'output_folder') or not self.output_folder:
            self.log("No output folder selected. Exiting.")
            return

        self.log("Starting conversion...")
        self.stop_event.clear()
        self.process = threading.Thread(target=self.resize_and_convert_videos)
        self.process.start()

    def stop_conversion(self):
        if self.process and self.process.is_alive():
            self.log("Stopping conversion...")
            self.stop_event.set()
            self.process.join()
            self.process = None

    def get_next_sequence_number(self):
        if os.path.exists(SEQUENCE_FILE):
            with open(SEQUENCE_FILE, "r") as file:
                sequence_number = int(file.read().strip())
        else:
            sequence_number = 1
        return sequence_number

    def increment_sequence_number(self, sequence_number):
        with open(SEQUENCE_FILE, "w") as file:
            file.write(str(sequence_number + 1))

    def resize_and_convert_videos(self, width=1280, height=720, bitrate="1000k"):
        for file_path in self.input_files:
            if self.stop_event.is_set():
                break
            try:
                sequence_number = self.get_next_sequence_number()
                output_filename = f"av{sequence_number:04d}.mp4"
                output_path = os.path.join(self.output_folder, output_filename)
                command = [
                    'ffmpeg', '-threads', str(self.threads_var.get()), '-i', file_path,
                    '-c:v', 'h264_nvenc',
                    '-b:v', bitrate,
                    '-vf', f'scale={width}:{height}',
                    output_path
                ]
                self.log(f"Running command: {' '.join(command)}")

                start_time = time.time()
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')

                while True:
                    if time.time() - start_time > TIMEOUT:
                        process.kill()
                        self.log(f"Timeout expired for {file_path}. Moving to the next file.")
                        if os.path.exists(output_path):
                            os.remove(output_path)
                            self.log(f"Deleted incomplete output file {output_path}")
                        break

                    output = process.stderr.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.log(output.strip())
                        if "frame=" in output:
                            start_time = time.time()  # Reset the start time when processing begins

                stdout, stderr = process.communicate()
                self.log(stdout)
                self.log(stderr)
                
                if process.returncode == 0:
                    self.log(f"Saved resized video to {output_path}")
                    # Delete original file
                    os.remove(file_path)
                    self.log(f"Deleted original file {file_path}")
                    # Increment sequence number
                    self.increment_sequence_number(sequence_number)
                else:
                    self.log(f"Error processing {file_path}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                        self.log(f"Deleted incomplete output file {output_path}")
                    
            except subprocess.CalledProcessError as e:
                self.log(f"Error processing {file_path}: {e}")
            except OSError as e:
                self.log(f"Error deleting {file_path}: {e}")

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()
