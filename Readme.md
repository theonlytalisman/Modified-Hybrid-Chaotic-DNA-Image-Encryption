# MHC-DIE — Modified Hybrid Chaotic-DNA Image Encryption

> **By Muhammad Adeel Haider (BitR1ft)**

A research-grade image encryption system that fuses **chaos theory** with **DNA computing** to provide strong, key-dependent encryption for digital images. MHC-DIE is built on Kerckhoffs's Principle — security resides entirely in the secret key, never in algorithm secrecy.

---

## Overview

MHC-DIE combines three modified chaotic maps, dynamic DNA encoding rules, bit-level permutation, and chained bidirectional diffusion across 5 encryption rounds per channel. It comes with both a polished **GUI application** and an **interactive CLI**, plus a comprehensive **security analysis** module.

---

## Key Features

- **Three Modified Chaotic Maps** — Perturbed Logistic, Modified Sine, and Tent Map combined for a vastly larger key space
- **Dynamic DNA Encoding** — 8 DNA rules selected per-round and per-channel; rules change dynamically throughout encryption
- **Hybrid Permutation** — Bit-level + row/column pixel-level shuffling applied every round
- **Bidirectional Diffusion** — Chained forward modular-addition diffusion followed by backward XOR diffusion with feedback
- **SHA-512 Key Derivation** — 2^512 key space; computationally infeasible to brute-force
- **5 Encryption Rounds** — Per colour channel (RGB), with round-dependent parameter injection to prevent slide attacks
- **Cross-Channel XOR Mixing** — RGB channels are XOR-coupled after individual encryption
- **Security Analysis Suite** — Entropy, correlation, NPCR, UACI, histogram uniformity, and more
- **GUI + CLI** — Nord-themed Tkinter GUI and a full-featured interactive terminal interface

---

## Algorithm at a Glance

```
For each round r in {0, 1, 2, 3, 4}:
  1. SHA-512 key schedule  →  chaotic map initial conditions
  2. Bit-level permutation (Perturbed Logistic Map)
  3. Row permutation       (Modified Sine Map)
  4. Column permutation    (Tent Map)
  5. DNA encode  →  DNA add with chaotic DNA sequence  →  DNA decode
  6. Forward chained addition diffusion  c[i] = (p[i] + seq[i] + c[i-1]) mod 256
  7. Backward chained XOR diffusion      c[i] =  p[i] ⊕ seq[i] ⊕ c[i+1]
```

### Chaotic Maps

| Map | Formula | Modification |
|-----|---------|--------------|
| Perturbed Logistic | `x(n+1) = r·x(n)·(1−x(n)) + ε·sin(2π·x(n))` | Sinusoidal perturbation eliminates periodic windows |
| Modified Sine | `x(n+1) = (4−a)·sin(π·x(n))` | Stable chaotic regime across wide parameter range |
| Tent Map | `x(n+1) = x(n)/α  or  (1−x(n))/(1−α)` | Used for spatial permutation index generation |

---

## Project Structure

```
MHC-DIE/
├── main.py             # GUI application (Tkinter, Nord theme)
├── cli.py              # Interactive command-line interface
├── crypto_engine.py    # Core encryption/decryption engine
├── security_analysis.py# Security metrics (entropy, NPCR, UACI, correlation…)
├── MHC-DIE.pdf         # Research paper / documentation
└── MHC-DIE.pptx        # Presentation slides
```

---

## Requirements

```
Python >= 3.8
numpy
Pillow
matplotlib   (for histogram / correlation visualisations)
tkinter      (bundled with standard Python on Windows)
```

Install dependencies:

```bash
pip install numpy Pillow matplotlib
```

---

## Usage

### GUI (Recommended)

```bash
python main.py
```

1. Enter an **encryption key** (minimum 16 characters) in the toolbar.
2. Click **Load Image** and select any PNG / BMP / JPEG file.
3. Click **Encrypt** — the encrypted image appears alongside the original.
4. Click **Decrypt** to recover the original; a pixel-perfect verification check runs automatically.
5. Use the **Analysis** menu or tab to run the full security report.

### CLI

```bash
python cli.py
```

Choose from the interactive menu:

| Option | Action |
|--------|--------|
| 1 | Encrypt an image |
| 2 | Decrypt an image |
| 3 | Run full security analysis |
| 4 | Generate & save histogram / correlation visualisations |
| 5 | Exit |

---

## Security Properties

| Property | Value |
|----------|-------|
| Key derivation | SHA-512 (512-bit output) |
| Key space | 2^512 |
| Minimum key length | 16 characters |
| Encryption rounds | 5 per channel |
| Chaotic maps | 3 (combined) |
| DNA encoding rules | 8 (dynamic) |
| Security principle | Kerckhoffs's Principle |

---

## Research Basis

This work builds upon and improves:

1. Anees et al. — *Chaotic Cryptosystem for Images* (2014)
2. Ratna & Surya — *Chaos-Based Image Encryption Using Arnold's Cat Map* (2025)
3. Zhang et al. — *DNA Encoding for Image Encryption* (2020–2024)

**Key contributions over existing work:**
- Sinusoidal perturbation added to the logistic map to close periodic windows
- Three chaotic maps combined (most papers use one or two)
- Bit-level AND pixel-level hybrid permutation
- Dynamic DNA rule chain (rules vary per round, not fixed)
- Hybrid bidirectional diffusion (addition forward, XOR backward) to prevent cancellation
- SHA-512 key derivation (stronger than the SHA-256 used in most prior work)
- Round-dependent parameter injection to resist slide attacks

---

## Author

**Muhammad Adeel Haider** — *BitR1ft*

---

*MHC-DIE is a research / academic project. Always evaluate any encryption scheme with domain experts before deploying in production.*
