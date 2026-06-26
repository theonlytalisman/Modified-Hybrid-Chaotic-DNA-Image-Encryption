"""
cli.py - Interactive Command Line Interface for MHC-DIE Image Encryption
"""

import os
import sys
import numpy as np
from PIL import Image
import logging

# Ensure the root logger doesn't spam the terminal unnecessarily
logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("MHC-DIE")

# Import the core modules
from crypto_engine import ImageEncryptor
from security_analysis import SecurityAnalyzer

# ANSI Colors
C_RED = "\033[91m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_RESET = "\033[0m"

def print_header():
    # Clear screen for a cleaner UI
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{C_CYAN}")
    print("="*60)
    print(" MHC-DIE: Modified Hybrid Chaotic-DNA Image Encryption CLI")
    print("="*60)
    print(f"{C_RESET}")

def get_input(prompt, required=True):
    while True:
        val = input(f"{C_YELLOW}{prompt}{C_RESET} ").strip()
        if val or not required:
            return val
        print(f"{C_RED}Input cannot be empty. Please try again.{C_RESET}")

def load_image(path):
    if not os.path.exists(path):
        print(f"{C_RED}Error: File '{path}' not found.{C_RESET}")
        return None
    try:
        img = Image.open(path)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        return np.array(img, dtype=np.uint8)
    except Exception as e:
        print(f"{C_RED}Error loading image: {e}{C_RESET}")
        return None

def save_image(img_array, path):
    try:
        Image.fromarray(img_array).save(path)
        print(f"{C_GREEN}Image successfully saved to '{path}'{C_RESET}")
    except Exception as e:
        print(f"{C_RED}Error saving image: {e}{C_RESET}")

def handle_encrypt(encryptor):
    print(f"\n{C_CYAN}--- Encrypt Image ---{C_RESET}")
    in_path = get_input("Enter path to input image:")
    img = load_image(in_path)
    if img is None:
        return
    
    key = get_input("Enter encryption key (min 16 characters):")
    if len(key) < 16:
        print(f"{C_RED}Key must be at least 16 characters.{C_RESET}")
        return
    
    out_path = get_input("Enter path to save encrypted image (e.g., enc.png):")
    
    print(f"\n{C_BLUE}Encrypting... Please wait.{C_RESET}")
    try:
        enc_img = encryptor.encrypt(img, key)
        save_image(enc_img, out_path)
    except Exception as e:
        print(f"{C_RED}Encryption failed: {e}{C_RESET}")

def handle_decrypt(encryptor):
    print(f"\n{C_CYAN}--- Decrypt Image ---{C_RESET}")
    in_path = get_input("Enter path to encrypted image:")
    img = load_image(in_path)
    if img is None:
        return
    
    key = get_input("Enter decryption key:")
    out_path = get_input("Enter path to save decrypted image (e.g., dec.png):")
    
    print(f"\n{C_BLUE}Decrypting... Please wait.{C_RESET}")
    try:
        dec_img = encryptor.decrypt(img, key)
        save_image(dec_img, out_path)
    except Exception as e:
        print(f"{C_RED}Decryption failed: {e}{C_RESET}")

def handle_analysis(encryptor):
    print(f"\n{C_CYAN}--- Security Analysis ---{C_RESET}")
    orig_path = get_input("Enter path to original image:")
    orig_img = load_image(orig_path)
    if orig_img is None: return

    enc_path = get_input("Enter path to encrypted image:")
    enc_img = load_image(enc_path)
    if enc_img is None: return

    key = get_input("Enter the encryption key used:")

    print(f"\n{C_BLUE}Running comprehensive security analysis...{C_RESET}")
    try:
        results = SecurityAnalyzer.full_analysis(
            original=orig_img,
            encrypted=enc_img,
            encrypt_fn=encryptor.encrypt,
            decrypt_fn=encryptor.decrypt,
            key=key
        )
        report = SecurityAnalyzer.format_report(results)
        print("\n" + report + "\n")
        
        save = get_input("Save this report to a text file? (y/n):", required=False).lower()
        if save == 'y':
            rep_path = get_input("Enter path to save report (e.g., report.txt):")
            with open(rep_path, "w") as f:
                f.write(report)
            print(f"{C_GREEN}Report saved to '{rep_path}'{C_RESET}")
    except Exception as e:
        print(f"{C_RED}Analysis failed: {e}{C_RESET}")

def handle_visualizations():
    print(f"\n{C_CYAN}--- Generate & Save Visualizations ---{C_RESET}")
    orig_path = get_input("Enter path to original image:")
    orig_img = load_image(orig_path)
    if orig_img is None: return

    enc_path = get_input("Enter path to encrypted image:")
    enc_img = load_image(enc_path)
    if enc_img is None: return

    out_dir = get_input("Enter directory to save visualizations (e.g., ./output or .):")
    if not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir)
        except Exception as e:
            print(f"{C_RED}Failed to create directory: {e}{C_RESET}")
            return
    
    print(f"\n{C_BLUE}Generating visualizations...{C_RESET}")
    
    try:
        import matplotlib
        matplotlib.use('Agg') # non-interactive backend for saving directly
        import matplotlib.pyplot as plt
        
        # 1. Histogram
        if len(orig_img.shape) == 2:
            channels = [('Gray', 0)]
        else:
            channels = [('Red', 0), ('Green', 1), ('Blue', 2)]

        num_ch = len(channels)
        fig, axes = plt.subplots(num_ch, 2, figsize=(12, 4 * num_ch))
        if num_ch == 1:
            axes = axes.reshape(1, -1)

        for idx, (name, ch_idx) in enumerate(channels):
            o_ch = orig_img[:,:,ch_idx] if len(orig_img.shape) == 3 else orig_img
            e_ch = enc_img[:,:,ch_idx] if len(enc_img.shape) == 3 else enc_img

            axes[idx, 0].hist(o_ch.flatten(), bins=256, range=(0, 256), color='#89b4fa', alpha=0.7)
            axes[idx, 0].set_title(f'Original - {name} Channel')
            
            axes[idx, 1].hist(e_ch.flatten(), bins=256, range=(0, 256), color='#f38ba8', alpha=0.7)
            axes[idx, 1].set_title(f'Encrypted - {name} Channel')

        plt.tight_layout()
        hist_path = os.path.join(out_dir, "histograms.png")
        fig.savefig(hist_path)
        plt.close(fig)
        print(f"{C_GREEN}Saved histograms to '{hist_path}'{C_RESET}")
        
        # 2. Correlation
        img = orig_img if len(orig_img.shape) == 2 else orig_img[:,:,0]
        enc = enc_img if len(enc_img.shape) == 2 else enc_img[:,:,0]
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
            axes[0, idx].scatter(x, y, s=1, c='#89b4fa', alpha=0.5)
            r = SecurityAnalyzer.correlation_coefficient(x.astype(float), y.astype(float))
            axes[0, idx].set_title(f'Original {name}\nr = {r:.6f}')

        for idx, (name, x, y) in enumerate(enc_directions):
            axes[1, idx].scatter(x, y, s=1, c='#f38ba8', alpha=0.5)
            r = SecurityAnalyzer.correlation_coefficient(x.astype(float), y.astype(float))
            axes[1, idx].set_title(f'Encrypted {name}\nr = {r:.6f}')

        plt.tight_layout()
        corr_path = os.path.join(out_dir, "correlation.png")
        fig.savefig(corr_path)
        plt.close(fig)
        print(f"{C_GREEN}Saved correlation plots to '{corr_path}'{C_RESET}")

    except Exception as e:
        print(f"{C_RED}Failed to generate visualizations: {e}{C_RESET}")

def main():
    encryptor = ImageEncryptor()
    while True:
        print_header()
        print("1. Encrypt Image")
        print("2. Decrypt Image")
        print("3. Run Security Analysis")
        print("4. Generate & Save Visualizations")
        print("5. Exit")
        
        choice = get_input("\nSelect an option (1-5):")
        
        if choice == '1':
            handle_encrypt(encryptor)
        elif choice == '2':
            handle_decrypt(encryptor)
        elif choice == '3':
            handle_analysis(encryptor)
        elif choice == '4':
            handle_visualizations()
        elif choice == '5':
            print(f"{C_GREEN}Exiting. Goodbye!{C_RESET}")
            break
        else:
            print(f"{C_RED}Invalid option. Please select 1-5.{C_RESET}")
        
        print(f"\n{C_CYAN}Press Enter to continue...{C_RESET}", end="")
        input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C_RED}Process interrupted by user. Exiting.{C_RESET}")
        sys.exit(0)
