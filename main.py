"""
main.py - GUI Application for MHC-DIE Image Encryption

A professional tkinter-based GUI application for:
1. Encrypting and decrypting images using the MHC-DIE algorithm
2. Running comprehensive security analysis on encrypted images
3. Visualizing results (original, encrypted, decrypted images)
4. Generating security analysis reports
5. Live log panel showing all encryption/decryption steps

This application follows secure software design principles:
- Input validation on all user inputs
- Error handling with user-friendly messages
- No sensitive data stored in memory longer than necessary
- Clean separation between UI and crypto logic
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import numpy as np
from PIL import Image, ImageTk
import os
import sys
import threading
import time
import logging
import io


# ============================================================================
# SETUP LOGGING - redirect to GUI text widget
# ============================================================================

class TextHandler(logging.Handler):
    """Logging handler that writes to a tkinter Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.see(tk.END)
            self.text_widget.configure(state=tk.DISABLED)
        # Schedule on main thread if needed
        try:
            self.text_widget.after(0, append)
        except Exception:
            pass


# Configure root logger
root_logger = logging.getLogger("MHC-DIE")
root_logger.setLevel(logging.DEBUG)
# Console handler (stderr) as fallback
_console = logging.StreamHandler(sys.stderr)
_console.setLevel(logging.DEBUG)
_console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
root_logger.addHandler(_console)

# Import our modules
from crypto_engine import ImageEncryptor
from security_analysis import SecurityAnalyzer


class ImageEncryptionApp:
    """Main Application Class for Image Encryption GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("MHC-DIE: Modified Hybrid Chaotic-DNA Image Encryption")
        self.root.geometry("1300x920")
        self.root.minsize(1024, 700)

        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Custom colors (Nord Theme)
        self.BG_COLOR = "#2e3440"
        self.FG_COLOR = "#eceff4"
        self.ACCENT = "#81a1c1"
        self.SUCCESS = "#a3be8c"
        self.DANGER = "#bf616a"
        self.WARNING = "#ebcb8b"
        self.SURFACE = "#3b4252"

        self.root.configure(bg=self.BG_COLOR)

        # State variables
        self.original_image = None
        self.encrypted_image = None
        self.decrypted_image = None
        self.current_key = tk.StringVar()
        self.original_path = tk.StringVar()
        self.encrypted_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        # Create encryptor instance
        self.encryptor = ImageEncryptor()

        # Build UI
        self._setup_styles()
        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_status_bar()

        # Setup logging to GUI
        self._setup_logging()

        self._update_status("Ready. Load an image to begin.")

    # ----------------------------------------------------------------
    # LOGGING
    # ----------------------------------------------------------------

    def _setup_logging(self):
        """Attach a logging handler that writes to the log panel."""
        handler = TextHandler(self.log_text)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5s] %(message)s", datefmt="%H:%M:%S"))
        root_logger.addHandler(handler)
        root_logger.info("MHC-DIE Application started")

    # ----------------------------------------------------------------
    # UI SETUP
    # ----------------------------------------------------------------

    def _setup_styles(self):
        self.style.configure('TFrame', background=self.BG_COLOR)
        self.style.configure('TLabel', background=self.BG_COLOR, foreground=self.FG_COLOR, font=('Segoe UI', 10))
        self.style.configure('Title.TLabel', background=self.BG_COLOR, foreground=self.ACCENT, font=('Segoe UI', 14, 'bold'))
        self.style.configure('Subtitle.TLabel', background=self.BG_COLOR, foreground=self.FG_COLOR, font=('Segoe UI', 11, 'bold'))
        self.style.configure('Status.TLabel', background=self.SURFACE, foreground=self.FG_COLOR, font=('Segoe UI', 9))
        self.style.configure('TButton', font=('Segoe UI', 10), padding=6)
        self.style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), padding=8)
        self.style.configure('TNotebook', background=self.BG_COLOR)
        self.style.configure('TNotebook.Tab', background=self.SURFACE, foreground=self.FG_COLOR, font=('Segoe UI', 10), padding=[12, 6])
        self.style.map('TNotebook.Tab', background=[('selected', self.BG_COLOR)], foreground=[('selected', self.ACCENT)])
        self.style.configure('TEntry', fieldbackground=self.SURFACE, foreground=self.FG_COLOR, insertcolor=self.FG_COLOR)
        self.style.configure('TProgressbar', background=self.ACCENT, troughcolor=self.SURFACE)
        self.style.configure('TLabelframe', background=self.BG_COLOR, foreground=self.FG_COLOR)
        self.style.configure('TLabelframe.Label', background=self.BG_COLOR, foreground=self.ACCENT, font=('Segoe UI', 10, 'bold'))

    def _build_menu(self):
        menubar = tk.Menu(self.root, bg=self.SURFACE, fg=self.FG_COLOR, activebackground=self.ACCENT, activeforeground=self.BG_COLOR)

        file_menu = tk.Menu(menubar, tearoff=0, bg=self.SURFACE, fg=self.FG_COLOR, activebackground=self.ACCENT)
        file_menu.add_command(label="Load Image", command=self._load_image, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Encrypted Image", command=self._save_encrypted, accelerator="Ctrl+S")
        file_menu.add_command(label="Save Decrypted Image", command=self._save_decrypted, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label="Generate Test Image", command=self._generate_test_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Alt+F4")
        menubar.add_cascade(label="File", menu=file_menu)

        analysis_menu = tk.Menu(menubar, tearoff=0, bg=self.SURFACE, fg=self.FG_COLOR, activebackground=self.ACCENT)
        analysis_menu.add_command(label="Run Full Analysis", command=self._run_full_analysis)
        analysis_menu.add_command(label="Show Histograms", command=self._show_histograms)
        analysis_menu.add_command(label="Show Correlation", command=self._show_correlation)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=self.SURFACE, fg=self.FG_COLOR, activebackground=self.ACCENT)
        help_menu.add_command(label="About Algorithm", command=self._show_about)
        help_menu.add_command(label="How to Use", command=self._show_help)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self.root.bind('<Control-o>', lambda e: self._load_image())
        self.root.bind('<Control-s>', lambda e: self._save_encrypted())
        self.root.bind('<Control-d>', lambda e: self._save_decrypted())

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 0))

        ttk.Label(toolbar, text="MHC-DIE Image Encryption", style='Title.TLabel').pack(side=tk.LEFT, padx=(0, 30))

        key_frame = ttk.LabelFrame(toolbar, text="Encryption Key (min 16 chars)", padding=6)
        key_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.key_entry = ttk.Entry(key_frame, textvariable=self.current_key, width=40, show="*", font=('Consolas', 11))
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(key_frame, text="Show", variable=self.show_key_var, command=self._toggle_key_visibility).pack(side=tk.LEFT, padx=(0, 6))

        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="Load Image", command=self._load_image).pack(side=tk.LEFT, padx=2)
        self.encrypt_btn = ttk.Button(btn_frame, text="Encrypt", command=self._encrypt_image, style='Accent.TButton')
        self.encrypt_btn.pack(side=tk.LEFT, padx=2)
        self.decrypt_btn = ttk.Button(btn_frame, text="Decrypt", command=self._decrypt_image, style='Accent.TButton')
        self.decrypt_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Analyze", command=self._run_full_analysis).pack(side=tk.LEFT, padx=2)

    def _build_main_area(self):
        # PanedWindow to allow resizing between images and log
        paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Top: notebook with tabs
        notebook_frame = ttk.Frame(paned)
        paned.add(notebook_frame, weight=3)

        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Encryption/Decryption
        self.enc_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.enc_tab, text="  Encrypt / Decrypt  ")
        self._build_encryption_tab()

        # Tab 2: Security Analysis
        self.analysis_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.analysis_tab, text="  Security Analysis  ")
        self._build_analysis_tab()

        # Tab 3: Algorithm Info
        self.info_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.info_tab, text="  Algorithm Info  ")
        self._build_info_tab()

        # Bottom: Log panel
        log_frame = ttk.LabelFrame(paned, text="Live Log & Debug Output", padding=4)
        paned.add(log_frame, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, bg="#2e3440", fg="#d8dee9",
            font=('Consolas', 9), insertbackground=self.FG_COLOR,
            wrap=tk.WORD, state=tk.DISABLED, height=8
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Color tags for log levels
        self.log_text.tag_configure('INFO', foreground=self.SUCCESS)
        self.log_text.tag_configure('WARNING', foreground=self.WARNING)
        self.log_text.tag_configure('ERROR', foreground=self.DANGER)
        self.log_text.tag_configure('DEBUG', foreground="#4c566a")
        self.log_text.tag_configure('CRITICAL', foreground=self.DANGER, font=('Consolas', 9, 'bold'))

        # Log toolbar
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(log_btn_frame, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_btn_frame, text="Save Log to File", command=self._save_log).pack(side=tk.LEFT, padx=2)

    def _build_encryption_tab(self):
        panels_frame = ttk.Frame(self.enc_tab)
        panels_frame.pack(fill=tk.BOTH, expand=True)

        # Original Image Panel
        orig_frame = ttk.LabelFrame(panels_frame, text="Original Image", padding=6)
        orig_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        self.orig_canvas = tk.Canvas(orig_frame, bg=self.SURFACE, highlightthickness=0)
        self.orig_canvas.pack(fill=tk.BOTH, expand=True)
        orig_info = ttk.Frame(orig_frame)
        orig_info.pack(fill=tk.X, pady=(4, 0))
        self.orig_info_label = ttk.Label(orig_info, text="No image loaded", style='Status.TLabel')
        self.orig_info_label.pack(fill=tk.X)

        # Encrypted Image Panel
        enc_frame = ttk.LabelFrame(panels_frame, text="Encrypted Image", padding=6)
        enc_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        self.enc_canvas = tk.Canvas(enc_frame, bg=self.SURFACE, highlightthickness=0)
        self.enc_canvas.pack(fill=tk.BOTH, expand=True)
        enc_info = ttk.Frame(enc_frame)
        enc_info.pack(fill=tk.X, pady=(4, 0))
        self.enc_info_label = ttk.Label(enc_info, text="Not yet encrypted", style='Status.TLabel')
        self.enc_info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(enc_info, text="Save", command=self._save_encrypted).pack(side=tk.RIGHT, padx=2)

        # Decrypted Image Panel
        dec_frame = ttk.LabelFrame(panels_frame, text="Decrypted Image", padding=6)
        dec_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        self.dec_canvas = tk.Canvas(dec_frame, bg=self.SURFACE, highlightthickness=0)
        self.dec_canvas.pack(fill=tk.BOTH, expand=True)
        dec_info = ttk.Frame(dec_frame)
        dec_info.pack(fill=tk.X, pady=(4, 0))
        self.dec_info_label = ttk.Label(dec_info, text="Not yet decrypted", style='Status.TLabel')
        self.dec_info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dec_info, text="Save", command=self._save_decrypted).pack(side=tk.RIGHT, padx=2)

        for canvas, text in [(self.orig_canvas, "Load an image\nto begin"),
                             (self.enc_canvas, "Encrypted output\nwill appear here"),
                             (self.dec_canvas, "Decrypted output\nwill appear here")]:
            canvas.create_text(canvas.winfo_reqwidth()//2, canvas.winfo_reqheight()//2,
                             text=text, fill=self.FG_COLOR, font=('Segoe UI', 12), justify=tk.CENTER, tags='placeholder')

        self.verification_label = ttk.Label(self.enc_tab, text="", style='Status.TLabel')
        self.verification_label.pack(fill=tk.X, pady=(4, 0))

    def _build_analysis_tab(self):
        self.results_text = scrolledtext.ScrolledText(
            self.analysis_tab, bg=self.SURFACE, fg=self.FG_COLOR,
            font=('Consolas', 10), insertbackground=self.FG_COLOR,
            wrap=tk.WORD, state=tk.DISABLED, height=20
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)

        self.results_text.tag_configure('header', foreground=self.ACCENT, font=('Consolas', 11, 'bold'))
        self.results_text.tag_configure('pass', foreground=self.SUCCESS, font=('Consolas', 10, 'bold'))
        self.results_text.tag_configure('fail', foreground=self.DANGER, font=('Consolas', 10, 'bold'))
        self.results_text.tag_configure('warn', foreground=self.WARNING, font=('Consolas', 10, 'bold'))
        self.results_text.tag_configure('normal', foreground=self.FG_COLOR)

        btn_bar = ttk.Frame(self.analysis_tab)
        btn_bar.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_bar, text="Run Full Analysis", command=self._run_full_analysis).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Show Histograms", command=self._show_histograms).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Show Correlation Plots", command=self._show_correlation).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Save Report", command=self._save_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="Clear", command=self._clear_results).pack(side=tk.RIGHT, padx=2)

    def _build_info_tab(self):
        info_text = scrolledtext.ScrolledText(
            self.info_tab, bg=self.SURFACE, fg=self.FG_COLOR,
            font=('Segoe UI', 10), insertbackground=self.FG_COLOR,
            wrap=tk.WORD, state=tk.NORMAL, height=30
        )
        info_text.pack(fill=tk.BOTH, expand=True)

        info_content = """
MHC-DIE: Modified Hybrid Chaotic-DNA Image Encryption
                   Algorithm Documentation

OVERVIEW
--------
MHC-DIE is a symmetric image encryption algorithm that combines chaos theory
with DNA computing to provide strong encryption for digital images. The
algorithm follows Kerckhoffs's Principle: security depends entirely on the
secret key, not on the secrecy of the algorithm.

ALGORITHM COMPONENTS
-------------------

1. KEY SCHEDULE (SHA-512 Based)
   - Input: Text key (minimum 16 characters)
   - Process: SHA-512 hash -> parameter derivation
   - Output: Initial conditions and control parameters for 3 chaotic maps,
             DNA rule indices, round keys, permutation parameters
   - Key Space: 2^512 (computationally infeasible to brute-force)

2. CHAOTIC MAPS (Three Modified Maps)
   a) Perturbed Logistic Map:
      x(n+1) = r * x(n) * (1 - x(n)) + epsilon * sin(2*pi * x(n))
      Modification: Added sinusoidal perturbation to eliminate periodic windows.

   b) Modified Sine Map:
      x(n+1) = (4 - a) * sin(pi * x(n))
      Ensures chaotic regime for wide parameter range.

   c) Tent Map:
      x(n+1) = x(n)/alpha  if x(n) < alpha
      x(n+1) = (1-x(n))/(1-alpha)  if x(n) >= alpha

3. DNA ENCODING OPERATIONS
   - 8 encoding rules mapping 2-bit binary -> DNA base (A, T, G, C)
   - Dynamic rule selection (changes per round and channel)
   - DNA addition/subtraction for pixel value transformation

4. PERMUTATION OPERATIONS
   - Bit-level permutation: Shuffles bits within each pixel byte
   - Row permutation: Shuffles entire rows using chaotic sorting
   - Column permutation: Shuffles entire columns using chaotic sorting

5. DIFFUSION OPERATIONS
   - Forward chained XOR diffusion: c[i] = (p[i] XOR seq[i] XOR c[i-1]) mod 256
   - Backward chained XOR diffusion: c[i] = (p[i] XOR seq[i] XOR c[i+1]) mod 256

ENCRYPTION PIPELINE (5 Rounds per Channel)
------------------------------------------
For each round r in {0, 1, 2, 3, 4}:
  1. Generate round-specific chaotic sequences (3 maps)
  2. Bit-level permutation of all pixel values
  3. Row permutation
  4. Column permutation
  5. DNA encoding (dynamic rule selection)
  6. DNA addition with chaotic DNA sequence
  7. DNA decoding (complementary rule)
  8. Forward XOR diffusion with feedback
  9. Backward XOR diffusion with feedback

RESEARCH BASIS
--------------
[1] Anees et al. - Chaotic Cryptosystem for Images (2014)
[2] Ratna & Surya - Chaos-Based Image Encryption Using Arnold's Cat Map (2025)
[3] Zhang et al. - DNA encoding papers (2020-2024)

KEY MODIFICATIONS FROM EXISTING WORK:
1. Perturbed logistic map (eliminates periodic windows)
2. Three-map combination (vs typical 1-2 maps)
3. Bit-level + pixel-level hybrid
4. Dynamic DNA rule chain
5. Chained bidirectional diffusion
6. SHA-512 key derivation
7. Round-dependent parameter injection
"""
        info_text.insert(tk.END, info_content)
        info_text.configure(state=tk.DISABLED)

    def _build_status_bar(self):
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, side=tk.TOP, pady=(0, 4))

        ttk.Label(status_frame, textvariable=self.status_text, style='Status.TLabel', padding=4).pack(fill=tk.X)

    # ----------------------------------------------------------------
    # LOG OPERATIONS
    # ----------------------------------------------------------------

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state=tk.DISABLED)
        root_logger.info("Log cleared")

    def _save_log(self):
        path = filedialog.asksaveasfilename(
            title="Save Log", defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            content = self.log_text.get('1.0', tk.END)
            with open(path, 'w') as f:
                f.write(content)
            self._update_status(f"Log saved to {os.path.basename(path)}")

    # ----------------------------------------------------------------
    # IMAGE DISPLAY
    # ----------------------------------------------------------------

    def _display_image_on_canvas(self, canvas, image_array, info_label=None, label_text=""):
        if image_array is None:
            return
        canvas.delete('all')
        if len(image_array.shape) == 2:
            pil_img = Image.fromarray(image_array, mode='L')
        else:
            pil_img = Image.fromarray(image_array, mode='RGB')

        canvas.update_idletasks()
        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()
        if canvas_w < 10 or canvas_h < 10:
            canvas_w, canvas_h = 350, 300

        img_w, img_h = pil_img.size
        scale = min(canvas_w / img_w, canvas_h / img_h, 1.0)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

        self._photo = ImageTk.PhotoImage(pil_img)
        canvas.create_image(canvas_w // 2, canvas_h // 2, anchor=tk.CENTER, image=self._photo)

        if info_label and label_text:
            info_label.configure(text=label_text)

    def _set_canvas_placeholder(self, canvas, text):
        canvas.delete('all')
        canvas.update_idletasks()
        canvas.create_text(canvas.winfo_width() // 2, canvas.winfo_height() // 2,
                         text=text, fill=self.FG_COLOR, font=('Segoe UI', 11), justify=tk.CENTER)

    # ----------------------------------------------------------------
    # FILE OPERATIONS
    # ----------------------------------------------------------------

    def _load_image(self):
        filetypes = [("Image files", "*.png *.bmp *.jpg *.jpeg *.tiff *.gif"), ("PNG", "*.png"), ("BMP", "*.bmp"), ("JPEG", "*.jpg *.jpeg"), ("All", "*.*")]
        path = filedialog.askopenfilename(title="Select Image", filetypes=filetypes)
        if not path:
            return
        try:
            img = Image.open(path)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            self.original_image = np.array(img, dtype=np.uint8)
            self.original_path.set(path)

            info_text = f"{os.path.basename(path)} | {img.size[0]}x{img.size[1]} | {img.mode}"
            info_text += " | Grayscale" if len(self.original_image.shape) == 2 else " | RGB"
            self._display_image_on_canvas(self.orig_canvas, self.original_image, self.orig_info_label, info_text)

            self.encrypted_image = None
            self.decrypted_image = None
            self._set_canvas_placeholder(self.enc_canvas, "Encrypted output\nwill appear here")
            self._set_canvas_placeholder(self.dec_canvas, "Decrypted output\nwill appear here")
            self.enc_info_label.configure(text="Not yet encrypted")
            self.dec_info_label.configure(text="Not yet decrypted")
            self.verification_label.configure(text="")
            self._update_status(f"Image loaded: {os.path.basename(path)}")
            root_logger.info(f"Image loaded: {path} ({img.size[0]}x{img.size[1]}, {img.mode})")
        except Exception as e:
            root_logger.error(f"Failed to load image: {e}")
            messagebox.showerror("Error", f"Failed to load image:\n{str(e)}")

    def _save_encrypted(self):
        if self.encrypted_image is None:
            messagebox.showwarning("Warning", "No encrypted image to save. Encrypt first!")
            return
        path = filedialog.asksaveasfilename(title="Save Encrypted", defaultextension=".png", filetypes=[("PNG", "*.png"), ("BMP", "*.bmp"), ("All", "*.*")])
        if path:
            try:
                Image.fromarray(self.encrypted_image).save(path)
                self._update_status(f"Saved: {os.path.basename(path)}")
            except Exception as e:
                root_logger.error(f"Save failed: {e}")

    def _save_decrypted(self):
        if self.decrypted_image is None:
            messagebox.showwarning("Warning", "No decrypted image to save. Decrypt first!")
            return
        path = filedialog.asksaveasfilename(title="Save Decrypted", defaultextension=".png", filetypes=[("PNG", "*.png"), ("BMP", "*.bmp"), ("All", "*.*")])
        if path:
            try:
                Image.fromarray(self.decrypted_image).save(path)
                self._update_status(f"Saved: {os.path.basename(path)}")
            except Exception as e:
                root_logger.error(f"Save failed: {e}")

    def _generate_test_image(self):
        size = 256
        img = np.zeros((size, size, 3), dtype=np.uint8)
        for i in range(size):
            for j in range(size):
                img[i, j] = [i % 256, j % 256, (i + j) % 256]
        cx, cy, r = size//2, size//2, size//4
        y, x = np.ogrid[:size, :size]
        mask = (x - cx)**2 + (y - cy)**2 <= r**2
        img[mask] = [255, 128, 0]
        img[20:60, 20:100] = [255, 0, 0]
        for i in range(180, 240):
            for j in range(180, 180 + (i - 180)):
                img[i, j] = [0, 255, 0]
        for i in range(100, 140, 4):
            for j in range(100, 180, 4):
                img[i:i+2, j:j+2] = [255, 255, 255]
        self.original_image = img
        self._display_image_on_canvas(self.orig_canvas, self.original_image, self.orig_info_label, f"Test Image | {size}x{size} | RGB")
        root_logger.info(f"Test image generated ({size}x{size} RGB)")

    # ----------------------------------------------------------------
    # ENCRYPTION / DECRYPTION
    # ----------------------------------------------------------------

    def _validate_key(self):
        key = self.current_key.get()
        if len(key) < 16:
            messagebox.showwarning("Invalid Key", f"Key must be at least 16 characters.\nCurrent: {len(key)} chars.\n\nExample: MySecureKey123456")
            return False
        return True

    def _encrypt_image(self):
        if self.original_image is None:
            messagebox.showwarning("Warning", "Please load an image first!")
            return
        if not self._validate_key():
            return

        self.encrypt_btn.configure(state='disabled')
        self._update_status("Encrypting...")
        self.progress_var.set(0)
        root_logger.info("="*60)
        root_logger.info("STARTING ENCRYPTION")
        root_logger.info(f"Image shape: {self.original_image.shape}")
        root_logger.info(f"Key length: {len(self.current_key.get())} chars")

        def do_encrypt():
            try:
                start_time = time.time()
                self.encrypted_image = self.encryptor.encrypt(self.original_image, self.current_key.get())
                elapsed = time.time() - start_time
                self.root.after(0, lambda: self._on_encrypt_complete(elapsed))
            except Exception as e:
                root_logger.error(f"ENCRYPTION FAILED: {e}", exc_info=True)
                self.root.after(0, lambda: self._on_error(f"Encryption failed:\n{str(e)}"))

        threading.Thread(target=do_encrypt, daemon=True).start()

    def _on_encrypt_complete(self, elapsed):
        self.progress_var.set(100)
        self.encrypt_btn.configure(state='normal')
        root_logger.info(f"ENCRYPTION COMPLETE in {elapsed:.3f}s")

        info = f"Encrypted | {self.encrypted_image.shape[1]}x{self.encrypted_image.shape[0]}"
        info += " | Grayscale" if len(self.encrypted_image.shape) == 2 else " | RGB"
        info += f" | Time: {elapsed:.3f}s"
        self._display_image_on_canvas(self.enc_canvas, self.encrypted_image, self.enc_info_label, info)

        self.decrypted_image = None
        self._set_canvas_placeholder(self.dec_canvas, "Decrypted output\nwill appear here")
        self.dec_info_label.configure(text="Not yet decrypted")
        self.verification_label.configure(text="")
        self._update_status(f"Encryption complete in {elapsed:.3f} seconds")

    def _decrypt_image(self):
        if self.encrypted_image is None and self.original_image is None:
            messagebox.showwarning("Warning", "Please load an encrypted image or encrypt an image first!")
            return
        if not self._validate_key():
            return

        source_image = self.encrypted_image if self.encrypted_image is not None else self.original_image
        source_is_original = (self.encrypted_image is None)

        self.decrypt_btn.configure(state='disabled')
        self._update_status("Decrypting...")
        self.progress_var.set(0)
        root_logger.info("="*60)
        root_logger.info("STARTING DECRYPTION")
        root_logger.info(f"Encrypted shape: {source_image.shape}")

        def do_decrypt():
            try:
                start_time = time.time()
                self.decrypted_image = self.encryptor.decrypt(source_image, self.current_key.get())
                elapsed = time.time() - start_time
                self.root.after(0, lambda: self._on_decrypt_complete(elapsed, source_is_original))
            except Exception as e:
                root_logger.error(f"DECRYPTION FAILED: {e}", exc_info=True)
                self.root.after(0, lambda: self._on_error(f"Decryption failed:\n{str(e)}"))

        threading.Thread(target=do_decrypt, daemon=True).start()

    def _on_decrypt_complete(self, elapsed, source_is_original=False):
        self.progress_var.set(100)
        self.decrypt_btn.configure(state='normal')
        root_logger.info(f"DECRYPTION COMPLETE in {elapsed:.3f}s")

        # Verify
        if not source_is_original and self.original_image is not None and self.decrypted_image is not None:
            if np.array_equal(self.original_image, self.decrypted_image):
                verify_text = "VERIFICATION: Decrypted image matches original perfectly (0 errors)"
                verify_color = self.SUCCESS
                root_logger.info("VERIFICATION PASSED: Perfect match!")
            else:
                diff_count = int(np.sum(np.not_equal(self.original_image, self.decrypted_image)))
                total = self.original_image.size
                pct = diff_count / total * 100
                verify_text = f"WARNING: {diff_count}/{total} pixels differ ({pct:.4f}%)"
                verify_color = self.DANGER
                root_logger.warning(f"VERIFICATION FAILED: {diff_count} pixels differ ({pct:.4f}%)")
        else:
            verify_text = ""
            verify_color = self.FG_COLOR

        info = f"Decrypted | {self.decrypted_image.shape[1]}x{self.decrypted_image.shape[0]}"
        info += " | Grayscale" if len(self.decrypted_image.shape) == 2 else " | RGB"
        info += f" | Time: {elapsed:.3f}s"
        self._display_image_on_canvas(self.dec_canvas, self.decrypted_image, self.dec_info_label, info)
        self.verification_label.configure(text=verify_text, foreground=verify_color)
        self._update_status(f"Decryption complete in {elapsed:.3f} seconds")

    def _on_error(self, message):
        self.encrypt_btn.configure(state='normal')
        self.decrypt_btn.configure(state='normal')
        self.progress_var.set(0)
        self._update_status("Error occurred")
        messagebox.showerror("Error", message)

    # ----------------------------------------------------------------
    # SECURITY ANALYSIS
    # ----------------------------------------------------------------

    def _run_full_analysis(self):
        if self.original_image is None or self.encrypted_image is None:
            messagebox.showwarning("Warning", "Please load an image AND encrypt it before running analysis!")
            return
        if not self._validate_key():
            return

        self._update_status("Running security analysis...")
        self.notebook.select(self.analysis_tab)
        self.results_text.configure(state=tk.NORMAL)
        self.results_text.delete('1.0', tk.END)
        self.results_text.insert(tk.END, "Running comprehensive security analysis...\n\n")
        self.results_text.configure(state=tk.DISABLED)

        root_logger.info("Starting full security analysis...")

        def do_analysis():
            try:
                key = self.current_key.get()
                results = SecurityAnalyzer.full_analysis(
                    original=self.original_image,
                    encrypted=self.encrypted_image,
                    encrypt_fn=self.encryptor.encrypt,
                    decrypt_fn=self.encryptor.decrypt,
                    key=key
                )
                report = SecurityAnalyzer.format_report(results)
                self.root.after(0, lambda: self._display_analysis_results(report, results))
            except Exception as e:
                root_logger.error(f"Analysis failed: {e}", exc_info=True)
                self.root.after(0, lambda: self._on_error(f"Analysis failed:\n{str(e)}"))

        threading.Thread(target=do_analysis, daemon=True).start()

    def _display_analysis_results(self, report, results):
        self.results_text.configure(state=tk.NORMAL)
        self.results_text.delete('1.0', tk.END)
        for line in report.split('\n'):
            if line.strip().startswith('='):
                tag = 'header'
            elif '[PASS]' in line:
                tag = 'pass'
            elif '[FAIL]' in line:
                tag = 'fail'
            elif '[WARN]' in line:
                tag = 'warn'
            else:
                tag = 'normal'
            self.results_text.insert(tk.END, line + '\n', tag)
        self.results_text.configure(state=tk.DISABLED)
        self._update_status("Security analysis complete")
        root_logger.info("Security analysis complete")

    def _show_histograms(self):
        if self.original_image is None or self.encrypted_image is None:
            messagebox.showwarning("Warning", "Load and encrypt an image first!")
            return

        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        hist_win = tk.Toplevel(self.root)
        hist_win.title("Histogram Analysis")
        hist_win.geometry("1000x700")
        hist_win.configure(bg=self.BG_COLOR)

        if len(self.original_image.shape) == 2:
            channels = [('Gray', 0)]
        else:
            channels = [('Red', 0), ('Green', 1), ('Blue', 2)]

        num_ch = len(channels)
        fig, axes = plt.subplots(num_ch, 2, figsize=(12, 4 * num_ch))
        if num_ch == 1:
            axes = axes.reshape(1, -1)

        for idx, (name, ch_idx) in enumerate(channels):
            orig_ch = self.original_image[:,:,ch_idx] if len(self.original_image.shape) == 3 else self.original_image
            enc_ch = self.encrypted_image[:,:,ch_idx] if len(self.encrypted_image.shape) == 3 else self.encrypted_image

            axes[idx, 0].hist(orig_ch.flatten(), bins=256, range=(0, 256), color='#81a1c1', alpha=0.8)
            axes[idx, 0].set_title(f'Original - {name} Channel', color='#eceff4')
            axes[idx, 0].set_xlabel('Pixel Value', color='#d8dee9')
            axes[idx, 0].set_ylabel('Frequency', color='#d8dee9')
            axes[idx, 0].set_facecolor('#3b4252')
            axes[idx, 0].tick_params(colors='#d8dee9')

            axes[idx, 1].hist(enc_ch.flatten(), bins=256, range=(0, 256), color='#bf616a', alpha=0.8)
            axes[idx, 1].set_title(f'Encrypted - {name} Channel', color='#eceff4')
            axes[idx, 1].set_xlabel('Pixel Value', color='#d8dee9')
            axes[idx, 1].set_ylabel('Frequency', color='#d8dee9')
            axes[idx, 1].set_facecolor('#3b4252')
            axes[idx, 1].tick_params(colors='#d8dee9')

        fig.patch.set_facecolor(self.BG_COLOR)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=hist_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        btn_frame = ttk.Frame(hist_win)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Save Histogram", command=lambda: self._save_plot(fig, "histogram.png")).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Close", command=hist_win.destroy).pack(side=tk.LEFT, padx=4)

    def _show_correlation(self):
        if self.original_image is None or self.encrypted_image is None:
            messagebox.showwarning("Warning", "Load and encrypt an image first!")
            return

        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        corr_win = tk.Toplevel(self.root)
        corr_win.title("Correlation Analysis")
        corr_win.geometry("1200x800")
        corr_win.configure(bg=self.BG_COLOR)

        img = self.original_image if len(self.original_image.shape) == 2 else self.original_image[:,:,0]
        enc = self.encrypted_image if len(self.encrypted_image.shape) == 2 else self.encrypted_image[:,:,0]

        h, w = img.shape
        np.random.seed(42)
        n = min(2000, h * w // 2)
        rows = np.random.randint(0, min(h-1, n), n)
        cols = np.random.randint(0, min(w-1, n), n)

        fig, axes = plt.subplots(2, 3, figsize=(16, 10))

        directions = [
            ('Horizontal', img[rows, cols], img[rows, cols+1]),
            ('Vertical', img[rows, cols], img[rows+1, cols]),
            ('Diagonal', img[rows, cols], img[rows+1, cols+1]),
        ]
        enc_directions = [
            ('Horizontal', enc[rows, cols], enc[rows, cols+1]),
            ('Vertical', enc[rows, cols], enc[rows+1, cols]),
            ('Diagonal', enc[rows, cols], enc[rows+1, cols+1]),
        ]

        for idx, (name, x, y) in enumerate(directions):
            axes[0, idx].scatter(x, y, s=1, c='#81a1c1', alpha=0.6)
            r = SecurityAnalyzer.correlation_coefficient(x.astype(float), y.astype(float))
            axes[0, idx].set_title(f'Original {name}\nr = {r:.6f}', color='#eceff4')
            axes[0, idx].set_facecolor('#3b4252')
            axes[0, idx].tick_params(colors='#d8dee9')

        for idx, (name, x, y) in enumerate(enc_directions):
            axes[1, idx].scatter(x, y, s=1, c='#bf616a', alpha=0.6)
            r = SecurityAnalyzer.correlation_coefficient(x.astype(float), y.astype(float))
            axes[1, idx].set_title(f'Encrypted {name}\nr = {r:.6f}', color='#eceff4')
            axes[1, idx].set_facecolor('#3b4252')
            axes[1, idx].tick_params(colors='#d8dee9')

        fig.patch.set_facecolor(self.BG_COLOR)
        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=corr_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        btn_frame = ttk.Frame(corr_win)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Save Plot", command=lambda: self._save_plot(fig, "correlation.png")).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Close", command=corr_win.destroy).pack(side=tk.LEFT, padx=4)

    def _save_plot(self, fig, default_name):
        path = filedialog.asksaveasfilename(
            title="Save Plot", defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG", "*.png"), ("All files", "*.*")]
        )
        if path:
            try:
                fig.savefig(path, facecolor=fig.get_facecolor())
                self._update_status(f"Plot saved: {os.path.basename(path)}")
            except Exception as e:
                root_logger.error(f"Failed to save plot: {e}")
                messagebox.showerror("Error", f"Failed to save plot:\n{str(e)}")

    def _clear_results(self):
        self.results_text.configure(state=tk.NORMAL)
        self.results_text.delete('1.0', tk.END)
        self.results_text.configure(state=tk.DISABLED)

    def _save_report(self):
        path = filedialog.asksaveasfilename(
            title="Save Report", defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            content = self.results_text.get('1.0', tk.END)
            with open(path, 'w') as f:
                f.write(content)
            self._update_status(f"Report saved: {os.path.basename(path)}")

    # ----------------------------------------------------------------
    # HELP DIALOGS
    # ----------------------------------------------------------------

    def _show_about(self):
        messagebox.showinfo("About MHC-DIE",
            "MHC-DIE: Modified Hybrid Chaotic-DNA Image Encryption\n\n"
            "A novel image encryption algorithm combining:\n"
            "  - Perturbed Logistic Map\n"
            "  - Modified Sine Map\n"
            "  - Tent Map\n"
            "  - DNA Encoding Operations\n"
            "  - Bit-level + Pixel-level Permutation\n"
            "  - Chained XOR Diffusion\n\n"
            "Security: Kerckhoffs's Principle compliant\n"
            "Key Space: 2^512 (SHA-512)")

    def _show_help(self):
        messagebox.showinfo("How to Use",
            "1. Load an image (File > Load Image, or Ctrl+O)\n"
            "2. Enter an encryption key (min 16 characters)\n"
            "3. Click 'Encrypt' to encrypt the image\n"
            "4. Click 'Decrypt' to verify decryption works\n"
            "5. Click 'Analyze' to run security tests\n\n"
            "Tips:\n"
            "- Use File > Generate Test Image for quick testing\n"
            "- Watch the Log panel at the bottom for step-by-step progress\n"
            "- Save the log if you need to debug issues\n\n"
            "Keyboard Shortcuts:\n"
            "  Ctrl+O - Load image\n"
            "  Ctrl+S - Save encrypted image\n"
            "  Ctrl+D - Save decrypted image")

    def _toggle_key_visibility(self):
        if self.show_key_var.get():
            self.key_entry.configure(show="")
        else:
            self.key_entry.configure(show="*")

    def _update_status(self, text):
        self.status_text.set(text)


# ============================================================================
# MAIN
# ============================================================================

def main():
    root = tk.Tk()
    app = ImageEncryptionApp(root)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()


if __name__ == "__main__":
    main()
