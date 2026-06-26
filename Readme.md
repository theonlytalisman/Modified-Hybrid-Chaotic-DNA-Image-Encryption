<div align="center">

# MHC-DIE
### Modified Hybrid Chaotic-DNA Image Encryption

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-00e5ff?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Research-7c3aed?style=flat-square)]()
[![Security](https://img.shields.io/badge/Key%20Space-2%5E512-238636?style=flat-square)]()

*A research-grade image encryption system fusing chaos theory with DNA computing.*

</div>

---

## Overview

MHC-DIE combines **three modified chaotic maps**, **dynamic DNA encoding**, **bit-level permutation**, and **chained bidirectional diffusion** across 5 encryption rounds per colour channel. Security resides entirely in the secret key — never in algorithm secrecy (Kerckhoffs's Principle).

Comes with a polished **GUI application**, a full **interactive CLI**, and a comprehensive **security analysis** module.

---

## How It Works

Each colour channel (R, G, B) is processed independently through 5 rounds:

```
For each round r ∈ {0, 1, 2, 3, 4}:
  1. SHA-512 key schedule        →  chaotic map initial conditions
  2. Bit-level permutation          (Perturbed Logistic Map)
  3. Row permutation                (Modified Sine Map)
  4. Column permutation             (Tent Map)
  5. DNA encode → XOR with chaotic DNA sequence → DNA decode
  6. Forward diffusion    c[i] = (p[i] + seq[i] + c[i-1]) mod 256
  7. Backward diffusion   c[i] =  p[i] ⊕ seq[i] ⊕ c[i+1]

After all rounds: RGB channels are XOR-coupled across channels.
```

### Chaotic Maps

| Map | Formula | Modification |
|-----|---------|-------------|
| Perturbed Logistic | `x(n+1) = r·x(n)·(1−x(n)) + ε·sin(2π·x(n))` | Sinusoidal perturbation closes periodic windows |
| Modified Sine | `x(n+1) = (4−a)·sin(π·x(n))` | Stable chaotic regime across wide parameter range |
| Tent Map | `x(n+1) = x(n)/α  or  (1−x(n))/(1−α)` | Spatial permutation index generation |

Using three maps in combination expands the effective key space and removes the structural weaknesses present in any single-map scheme.

---

## Security Properties

| Property | Value |
|----------|-------|
| Key derivation | SHA-512 |
| Key space | 2^512 |
| Minimum key length | 16 characters |
| Encryption rounds | 5 per channel |
| Chaotic maps | 3 (combined) |
| DNA encoding rules | 8 (dynamic, per-round) |
| Security principle | Kerckhoffs's Principle |

---

## Key Features

- **Three Modified Chaotic Maps** — combined for a vastly larger key space and no inter-map correlation
- **Dynamic DNA Encoding** — 8 rules selected per-round, per-channel; rules shift throughout encryption, never fixed
- **Hybrid Permutation** — bit-level shuffling (Logistic) + row shuffling (Sine) + column shuffling (Tent) every round
- **Bidirectional Diffusion** — forward modular-addition followed by backward XOR with feedback; prevents cancellation attacks
- **SHA-512 Key Derivation** — round-dependent parameter injection resists slide attacks
- **Cross-Channel XOR Mixing** — RGB channels are coupled after individual encryption for inter-channel diffusion
- **Security Analysis Suite** — entropy, correlation, NPCR, UACI, histogram uniformity
- **GUI + CLI** — Nord-themed Tkinter GUI and a full interactive terminal interface

---

## Project Structure

```
MHC-DIE/
├── main.py               # GUI application (Tkinter, Nord theme)
├── cli.py                # Interactive CLI
├── crypto_engine.py      # Core encryption / decryption engine
├── security_analysis.py  # Security metrics (entropy, NPCR, UACI, correlation…)
├── MHC-DIE.pdf           # Research paper
└── MHC-DIE.pptx          # Presentation slides
```

---

## Installation

**Requirements:** Python 3.8+

```bash
git clone https://github.com/theonlytalisman/MHC-DIE.git
cd MHC-DIE
pip install numpy Pillow matplotlib
```

> `tkinter` is bundled with standard Python on Windows. Linux users may need `sudo apt install python3-tk`.

---

## Usage

### GUI

```bash
python main.py
```

1. Enter an **encryption key** (minimum 16 characters)
2. Click **Load Image** — supports PNG, BMP, JPEG
3. Click **Encrypt** — encrypted image renders alongside the original
4. Click **Decrypt** to recover the original; pixel-perfect verification runs automatically
5. Open the **Analysis** tab to run the full security report

### CLI

```bash
python cli.py
```

| Option | Action |
|--------|--------|
| `1` | Encrypt an image |
| `2` | Decrypt an image |
| `3` | Run full security analysis |
| `4` | Generate histogram / correlation visualisations |
| `5` | Exit |

---

## Research Basis

Built upon and extending:

- Anees et al. — *Chaotic Cryptosystem for Images* (2014)
- Ratna & Surya — *Chaos-Based Image Encryption Using Arnold's Cat Map* (2025)
- Zhang et al. — *DNA Encoding for Image Encryption* (2020–2024)

**Contributions over prior work:**

| Prior Work | MHC-DIE |
|-----------|---------|
| Single or dual chaotic map | Three maps combined |
| Fixed DNA encoding rule | Dynamic per-round, per-channel rule chain |
| Pixel-level permutation only | Bit-level + pixel-level hybrid permutation |
| Unidirectional diffusion | Bidirectional (addition forward, XOR backward) |
| SHA-256 key derivation | SHA-512 key derivation |
| No slide-attack countermeasure | Round-dependent parameter injection |

---

## Disclaimer

MHC-DIE is a research and academic project. Evaluate any encryption scheme with domain experts before deploying in production environments.

---

<div align="center">

Built by **theonlytalisman**

</div>
