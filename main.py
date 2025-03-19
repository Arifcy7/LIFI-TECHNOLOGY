import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import time
import threading
import serial
import webbrowser

# Configure Arduino Connection
arduino_port = "COM3"  # Change to your Arduino port
baud_rate = 9600

try:
    arduino = serial.Serial(arduino_port, baud_rate, timeout=1)
    print(f"Connected to {arduino_port}")
except serial.SerialException:
    print("Error: Could not connect to Arduino")
    arduino = None

# Color Scheme
BG_COLOR = "#2E3440"
PRIMARY_COLOR = "#88C0D0"
SECONDARY_COLOR = "#81A1C1"
ACCENT_COLOR = "#BF616A"
TEXT_COLOR = "#ECEFF4"

# Modern Style Configuration
def configure_styles():
    style = ttk.Style()
    style.theme_use('clam')
    
    style.configure("TFrame", background=BG_COLOR)
    style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 12))
    style.configure("TButton", background=PRIMARY_COLOR, foreground=TEXT_COLOR,
                   borderwidth=0, font=("Segoe UI", 10, "bold"), padding=10)
    style.map("TButton", background=[('active', SECONDARY_COLOR), ('disabled', BG_COLOR)])
    style.configure("Horizontal.TProgressbar", troughcolor=BG_COLOR, background=PRIMARY_COLOR, thickness=20)
    style.configure("TEntry", fieldbackground="#4C566A", foreground=TEXT_COLOR, 
                   insertcolor=TEXT_COLOR, bordercolor=PRIMARY_COLOR)

# GUI Functions
def show_screen(screen):
    for frame in (main_screen, send_screen, receive_screen, text_receive_screen):
        frame.pack_forget()
    screen.pack(padx=20, pady=20, fill="both", expand=True)

def select_pdf():
    file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if file_path:
        pdf_entry.delete(0, tk.END)
        pdf_entry.insert(0, file_path)

def open_pdf():
    pdf_path = "received_file.pdf"
    if os.path.exists(pdf_path):
        webbrowser.open(pdf_path)
    else:
        messagebox.showerror("Error", "No received PDF found")

# PDF Transfer Functions
def send_pdf():
    pdf_path = pdf_entry.get()
    if not pdf_path or not os.path.exists(pdf_path):
        messagebox.showerror("Error", "Please select a valid PDF file")
        return

    send_progress["value"] = 0
    try:
        with open(pdf_path, "rb") as file:
            pdf_data = file.read()
        if arduino:
            threading.Thread(target=send_to_arduino, args=(pdf_data,)).start()
        else:
            messagebox.showerror("Error", "Arduino not connected")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read PDF: {str(e)}")

def send_to_arduino(pdf_data):
    try:
        chunk_size = 64
        total_size = len(pdf_data)
        sent_size = 0

        arduino.write(b"START_PDF")
        for i in range(0, total_size, chunk_size):
            chunk = pdf_data[i:i + chunk_size]
            arduino.write(chunk)
            sent_size += len(chunk)
            send_progress["value"] = (sent_size / total_size) * 100
            root.update_idletasks()
            time.sleep(0.1)

        arduino.write(b"END_PDF")
        messagebox.showinfo("Success", "PDF Sent Successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to send PDF: {str(e)}")

def receive_pdf():
    receive_progress["value"] = 0
    if arduino:
        threading.Thread(target=receive_from_arduino).start()
    else:
        messagebox.showerror("Error", "Arduino not connected")

def receive_from_arduino():
    try:
        received_data = b""
        start_time = time.time()

        while True:
            if arduino.in_waiting > 0:
                data = arduino.read(64)
                received_data += data
                receive_progress["value"] = min(100, len(received_data) / 50000 * 100)
                root.update_idletasks()

            if b"END_PDF" in received_data or (time.time() - start_time > 15):
                break

        received_data = received_data.replace(b"END_PDF", b"")
        if received_data:
            with open("received_file.pdf", "wb") as f:
                f.write(received_data)
            messagebox.showinfo("Success", "PDF Received!")
        else:
            messagebox.showerror("Error", "No PDF received")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to receive PDF: {str(e)}")

# Text Receive Functions
def receive_text():
    text_receive_progress["value"] = 0
    text_display.delete('1.0', tk.END)
    if arduino:
        threading.Thread(target=receive_text_from_arduino).start()
    else:
        messagebox.showerror("Error", "Arduino not connected")

def receive_text_from_arduino():
    try:
        received_text = ""
        start_time = time.time()
        arduino.write(b"START_TEXT")

        while True:
            if arduino.in_waiting > 0:
                data = arduino.read(arduino.in_waiting).decode('utf-8', errors='ignore')
                received_text += data
                text_display.insert(tk.END, data)
                text_display.see(tk.END)
                text_receive_progress["value"] = min(100, len(received_text) / 1000 * 100)
                root.update_idletasks()

            if b"END_TEXT" in received_text.encode() or (time.time() - start_time > 15):
                break

        messagebox.showinfo("Success", "Text received!" if received_text else messagebox.showerror("Error", "No text received"))
    except Exception as e:
        messagebox.showerror("Error", f"Text receive failed: {str(e)}")

def save_text():
    text_content = text_display.get('1.0', tk.END)
    if text_content.strip():
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, 'w') as f:
                f.write(text_content)
            messagebox.showinfo("Success", f"Text saved to {file_path}")
    else:
        messagebox.showerror("Error", "No text to save")

# GUI Setup
root = tk.Tk()
root.title("Li-Fi File Transfer")
root.geometry("800x600")
root.configure(bg=BG_COLOR)
configure_styles()

# Create frames
main_screen = ttk.Frame(root, style="TFrame")
send_screen = ttk.Frame(root, style="TFrame")
receive_screen = ttk.Frame(root, style="TFrame")
text_receive_screen = ttk.Frame(root, style="TFrame")

# Main Screen
main_label = ttk.Label(main_screen, text="📡 Li-Fi File Transfer", 
                      font=("Segoe UI", 24, "bold"), foreground=PRIMARY_COLOR)
main_label.pack(pady=40)

button_style = {"style": "TButton", "width": 25}
ttk.Button(main_screen, text="📤 Send PDF", command=lambda: show_screen(send_screen), **button_style).pack(pady=10)
ttk.Button(main_screen, text="📥 Receive PDF", command=lambda: show_screen(receive_screen), **button_style).pack(pady=10)
ttk.Button(main_screen, text="📝 Receive Text", command=lambda: show_screen(text_receive_screen), **button_style).pack(pady=10)

# Send Screen
ttk.Label(send_screen, text="📤 Send PDF", font=("Segoe UI", 18, "bold"), foreground=PRIMARY_COLOR).pack(pady=20)
pdf_entry = ttk.Entry(send_screen, width=50, style="TEntry", font=("Segoe UI", 10))
pdf_entry.pack(pady=10)
ttk.Button(send_screen, text="🔍 Browse PDF", command=select_pdf).pack(pady=10)
ttk.Button(send_screen, text="🚀 Start Transfer", command=send_pdf).pack(pady=20)
send_progress = ttk.Progressbar(send_screen, style="Horizontal.TProgressbar", length=500)
send_progress.pack(pady=10)

# Receive Screen
ttk.Label(receive_screen, text="📥 Receive PDF", font=("Segoe UI", 18, "bold"), foreground=PRIMARY_COLOR).pack(pady=20)
ttk.Button(receive_screen, text="🔄 Start Receiving", command=receive_pdf).pack(pady=20)
receive_progress = ttk.Progressbar(receive_screen, style="Horizontal.TProgressbar", length=500)
receive_progress.pack(pady=10)
ttk.Button(receive_screen, text="📂 Open Received PDF", command=open_pdf).pack(pady=20)

# Text Receive Screen
ttk.Label(text_receive_screen, text="📥 Receive Text", font=("Segoe UI", 18, "bold"), foreground=PRIMARY_COLOR).pack(pady=20)
text_display = scrolledtext.ScrolledText(text_receive_screen, wrap=tk.WORD, width=70, height=15,
                                        bg="#4C566A", fg=TEXT_COLOR, insertbackground=TEXT_COLOR)
text_display.pack(pady=10)
button_frame = ttk.Frame(text_receive_screen)
button_frame.pack(pady=10)
ttk.Button(button_frame, text="🔄 Start Receiving", command=receive_text).pack(side=tk.LEFT, padx=5)
ttk.Button(button_frame, text="💾 Save Text", command=save_text).pack(side=tk.LEFT, padx=5)
text_receive_progress = ttk.Progressbar(text_receive_screen, style="Horizontal.TProgressbar", length=500)
text_receive_progress.pack(pady=10)

# Navigation Buttons
def create_back_button(parent):
    return ttk.Button(parent, text="◀ Back to Main", command=lambda: show_screen(main_screen))

for screen in (send_screen, receive_screen, text_receive_screen):
    create_back_button(screen).pack(side="bottom", pady=20)

show_screen(main_screen)
root.mainloop()