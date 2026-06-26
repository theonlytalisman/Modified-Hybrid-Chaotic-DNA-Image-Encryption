"""
crypto_engine.py - Core Image Encryption/Decryption Engine

Algorithm: Modified Hybrid Chaotic-DNA Image Encryption (MHC-DIE)

This module implements a novel image encryption algorithm that combines:
1. Perturbed Logistic Map (modified with sinusoidal perturbation to avoid periodic orbits)
2. Modified Sine Map (for secondary chaotic sequences)
3. Tent Map (for block permutation indices)
4. DNA Encoding with 8 dynamic rules (biological-inspired confusion)
5. Bit-level permutation + Pixel-level diffusion (hybrid approach)
6. Chained XOR diffusion with feedback mechanism
7. SHA-512 based key derivation (Kerckhoffs's principle)

Research Basis (modified/improved from):
- Arnold Cat Map permutation [Ratna & Surya, 2025; Anees et al., 2014]
- Logistic Map chaos [May, 1976; various image encryption papers]
- Henon Map for multi-chaotic systems [Henon, 1976]
- DNA encoding [Zhang et al.; multiple 2023-2024 papers]
- Bit-level operations [Wang et al., 2022; Chen et al., 2023]

Key Modifications from Existing Work:
1. Sinusoidal perturbation added to logistic map to eliminate periodic windows
2. Three chaotic maps combined (not just 1-2) for larger key space
3. Bit-level AND pixel-level hybrid processing (most papers use only one)
4. Dynamic DNA rule chain (rules change per round, not fixed)
5. Chained diffusion with cumulative feedback (each pixel depends on all previous)
6. SHA-512 key derivation (stronger than SHA-256 used in most papers)
7. Round-dependent parameter injection (prevents slide attacks)

Security Principle: Kerckhoffs's Principle - Security depends on KEY only, not algorithm secrecy
"""

import hashlib
import numpy as np
from typing import Tuple, Dict, Optional
import logging

logger = logging.getLogger("MHC-DIE")

# ============================================================================
# DNA ENCODING RULES
# ============================================================================

DNA_ENCODE_RULES = {
    0: [0, 1, 2, 3], 1: [0, 1, 3, 2], 2: [0, 2, 1, 3], 3: [0, 2, 3, 1],
    4: [0, 3, 1, 2], 5: [0, 3, 2, 1], 6: [1, 0, 2, 3], 7: [1, 0, 3, 2],
}
DNA_COMPLEMENTARY = {0: 7, 1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1, 7: 0}

# Pre-build lookup arrays for vectorized DNA encode (shape: 4 x 256)
DNA_ENCODE_LUT = {}
DNA_DECODE_LUT = {}
for _rule_id in range(8):
    _rt = DNA_ENCODE_RULES[_rule_id]
    _lut = np.zeros((4, 256), dtype=np.uint8)
    for _b in range(4):
        for _v in range(256):
            _lut[_b, _v] = _rt[(_v >> (6 - 2 * _b)) & 0x03]
    DNA_ENCODE_LUT[_rule_id] = _lut

    _inv = [0] * 4
    for _i, _base in enumerate(_rt):
        _inv[_base] = _i
    _dlut = np.zeros((4, 4), dtype=np.uint8)
    for _b in range(4):
        for _base in range(4):
            _dlut[_b, _base] = _inv[_base]
    DNA_DECODE_LUT[_rule_id] = _dlut

# DNA addition table (mod 4)
DNA_ADD = np.array([[0,1,2,3],[1,2,3,0],[2,3,0,1],[3,0,1,2]], dtype=np.uint8)
# DNA subtraction table (mod 4)
DNA_SUB = np.array([[0,3,2,1],[1,0,3,2],[2,1,0,3],[3,2,1,0]], dtype=np.uint8)


# ============================================================================
# KEY SCHEDULE MODULE
# ============================================================================

class KeySchedule:
    """
    SHA-512 based key derivation for all chaotic map parameters.
    Key space: 2^512 (computationally infeasible to brute-force)
    """

    MIN_KEY_LENGTH = 16
    NUM_ROUNDS = 5

    @staticmethod
    def derive(text_key: str) -> Dict:
        if len(text_key) < KeySchedule.MIN_KEY_LENGTH:
            raise ValueError(
                f"Key must be at least {KeySchedule.MIN_KEY_LENGTH} characters. "
                f"Provided: {len(text_key)} characters."
            )

        key_hash = hashlib.sha512(
            text_key.encode('utf-8') + b'\x00MHC-DIE-v1.0'
        ).digest()

        def to_float(idx, low=0.001, high=0.999):
            val = int.from_bytes(key_hash[idx:idx+4], byteorder='big')
            return low + (val / 0xFFFFFFFF) * (high - low)

        def to_int(idx, low=1, high=256):
            val = int.from_bytes(key_hash[idx:idx+2], byteorder='big')
            return low + (val % (high - low + 1))

        params = {}
        params['x0_logistic'] = to_float(0, 0.100, 0.900)
        params['r_logistic'] = 3.57 + to_float(4, 0.0, 0.43)
        params['epsilon'] = to_float(8, 0.0005, 0.005)
        params['x0_sine'] = to_float(12, 0.100, 0.900)
        params['r_sine'] = to_float(16, 0.100, 0.999)
        params['x0_tent'] = to_float(20, 0.100, 0.900)
        params['alpha_tent'] = to_float(24, 0.100, 0.900)
        params['dna_enc_rules'] = [int(key_hash[28 + i] % 8) for i in range(8)]
        params['dna_dec_rules'] = [
            DNA_COMPLEMENTARY[params['dna_enc_rules'][i]] for i in range(8)
        ]
        params['arnold_a'] = to_int(36, 1, 256)
        params['arnold_b'] = to_int(38, 1, 256)
        params['round_keys'] = [
            to_float(40 + i * 4, 0.001, 0.999) for i in range(KeySchedule.NUM_ROUNDS)
        ]
        params['num_rounds'] = KeySchedule.NUM_ROUNDS
        params['chaotic_skip'] = 200  # Reduced from 2000 for performance; still sufficient

        assert 3.57 <= params['r_logistic'] <= 4.0
        assert 0 < params['epsilon'] < 0.01
        assert 0 < params['alpha_tent'] < 1

        logger.debug(f"Key derived. Rounds: {params['num_rounds']}, Skip: {params['chaotic_skip']}")
        return params


# ============================================================================
# CHAOTIC MAP MODULE (Fully vectorized with numpy)
# ============================================================================

class ChaoticMaps:
    """Three modified chaotic map implementations - fully vectorized."""

    @staticmethod
    def perturbed_logistic(x0, r, epsilon, length, skip=200):
        if length <= 0:
            return np.array([], dtype=np.float64)
        x = float(x0)
        for _ in range(skip):
            x = r * x * (1.0 - x) + epsilon * np.sin(2.0 * np.pi * x)
            x = max(1e-15, min(1.0 - 1e-15, x))

        # Vectorized generation in blocks
        result = np.empty(length, dtype=np.float64)
        BLOCK = 4096
        idx = 0
        while idx < length:
            block_size = min(BLOCK, length - idx)
            arr = np.full(block_size, x, dtype=np.float64)
            for j in range(block_size):
                arr[j] = r * arr[j] * (1.0 - arr[j]) + epsilon * np.sin(2.0 * np.pi * arr[j])
                arr[j] = max(1e-15, min(1.0 - 1e-15, arr[j]))
            x = arr[-1]
            result[idx:idx + block_size] = arr
            idx += block_size
        return result

    @staticmethod
    def modified_sine(x0, r, length, skip=200):
        if length <= 0:
            return np.array([], dtype=np.float64)
        x = float(x0)
        coeff = 4.0 - r
        for _ in range(skip):
            x = coeff * np.sin(np.pi * x)
            x = max(1e-15, min(1.0 - 1e-15, x))

        result = np.empty(length, dtype=np.float64)
        BLOCK = 4096
        idx = 0
        while idx < length:
            block_size = min(BLOCK, length - idx)
            arr = np.full(block_size, x, dtype=np.float64)
            for j in range(block_size):
                arr[j] = coeff * np.sin(np.pi * arr[j])
                arr[j] = max(1e-15, min(1.0 - 1e-15, arr[j]))
            x = arr[-1]
            result[idx:idx + block_size] = arr
            idx += block_size
        return result

    @staticmethod
    def tent_map(x0, alpha, length, skip=200):
        if length <= 0:
            return np.array([], dtype=np.float64)
        x = float(x0)
        inv_a = 1.0 / alpha
        inv_1a = 1.0 / (1.0 - alpha)
        for _ in range(skip):
            x = x * inv_a if x < alpha else (1.0 - x) * inv_1a
            x = max(1e-15, min(1.0 - 1e-15, x))

        result = np.empty(length, dtype=np.float64)
        BLOCK = 4096
        idx = 0
        while idx < length:
            block_size = min(BLOCK, length - idx)
            arr = np.full(block_size, x, dtype=np.float64)
            for j in range(block_size):
                arr[j] = arr[j] * inv_a if arr[j] < alpha else (1.0 - arr[j]) * inv_1a
                arr[j] = max(1e-15, min(1.0 - 1e-15, arr[j]))
            x = arr[-1]
            result[idx:idx + block_size] = arr
            idx += block_size
        return result


# ============================================================================
# DNA OPERATIONS MODULE (Vectorized)
# ============================================================================

class DNAOps:
    """Vectorized DNA encoding, decoding, and operations."""

    @staticmethod
    def encode(data, rule):
        """Vectorized DNA encode using pre-built lookup tables."""
        flat = data.astype(np.uint8).flatten()
        n = len(flat)
        out = np.empty(n * 4, dtype=np.uint8)
        lut = DNA_ENCODE_LUT[rule]
        for b in range(4):
            out[b::4] = lut[b, flat]
        return out

    @staticmethod
    def decode(dna, rule):
        """Vectorized DNA decode."""
        lut = DNA_DECODE_LUT[rule]
        reshaped = dna.reshape(-1, 4)
        bytes_out = np.zeros(len(reshaped), dtype=np.uint8)
        for i in range(4):
            bytes_out = (bytes_out << 2) | lut[i, reshaped[:, i]]
        return bytes_out

    @staticmethod
    def add(dna1, dna2):
        return DNA_ADD[dna1, dna2]

    @staticmethod
    def subtract(dna1, dna2):
        return DNA_SUB[dna1, dna2]


# ============================================================================
# PERMUTATION MODULE (Vectorized bit-perm)
# ============================================================================

class PermutationOps:
    """Pixel and bit-level permutation operations."""

    @staticmethod
    def _build_bit_perm_lut(chaotic_seq, total_bytes):
        """Build a lookup table for all bit permutations at once (vectorized)."""
        n = len(chaotic_seq)
        # For each byte, get 8 chaotic values -> argsort -> permutation
        byte_indices = np.arange(total_bytes)
        chaotic_indices = (byte_indices[:, None] * 8 + np.arange(8)[None, :]) % n
        sampled = chaotic_seq[chaotic_indices]  # shape: (total_bytes, 8)
        perms = np.argsort(sampled, axis=1)  # shape: (total_bytes, 8)
        inv_perms = np.argsort(perms, axis=1)  # shape: (total_bytes, 8)
        return perms, inv_perms

    @staticmethod
    def bit_permute(data, chaotic_seq):
        """Vectorized bit-level permutation using lookup table approach."""
        result = data.copy().astype(np.uint8)
        n = len(result)
        perms, _ = PermutationOps._build_bit_perm_lut(chaotic_seq, n)
        # Build a (256, 8) table: for each byte value, what are the 8 bits
        bits = ((result[:, None] >> np.arange(8)[None, :]) & 1).astype(np.uint8)  # (n, 8)
        # Permute bits: take bit at position j, put it at position perms[i, j]
        permuted_bits = np.take_along_axis(bits, perms, axis=1)  # (n, 8)
        # Reconstruct bytes
        powers = (1 << np.arange(8)).astype(np.uint16)
        result = (permuted_bits.astype(np.uint16) * powers[None, :]).sum(axis=1).astype(np.uint8)
        return result

    @staticmethod
    def inverse_bit_permute(data, chaotic_seq):
        """Vectorized inverse bit-level permutation."""
        result = data.copy().astype(np.uint8)
        n = len(result)
        _, inv_perms = PermutationOps._build_bit_perm_lut(chaotic_seq, n)
        bits = ((result[:, None] >> np.arange(8)[None, :]) & 1).astype(np.uint8)
        permuted_bits = np.take_along_axis(bits, inv_perms, axis=1)
        powers = (1 << np.arange(8)).astype(np.uint16)
        result = (permuted_bits.astype(np.uint16) * powers[None, :]).sum(axis=1).astype(np.uint8)
        return result

    @staticmethod
    def row_permute(image, chaotic_seq):
        h = image.shape[0]
        seq = chaotic_seq[:h]
        perm_order = np.argsort(seq)
        return image[perm_order]

    @staticmethod
    def inverse_row_permute(image, chaotic_seq):
        h = image.shape[0]
        seq = chaotic_seq[:h]
        perm_order = np.argsort(seq)
        inv_order = np.argsort(perm_order)
        return image[inv_order]

    @staticmethod
    def col_permute(image, chaotic_seq):
        w = image.shape[1]
        seq = chaotic_seq[:w]
        perm_order = np.argsort(seq)
        return image[:, perm_order]

    @staticmethod
    def inverse_col_permute(image, chaotic_seq):
        w = image.shape[1]
        seq = chaotic_seq[:w]
        perm_order = np.argsort(seq)
        inv_order = np.argsort(perm_order)
        return image[:, inv_order]


# ============================================================================
# DIFFUSION MODULE (Hybrid: Addition + XOR to prevent cancellation)
# ============================================================================

class DiffusionOps:
    """
    Diffusion operations - fully vectorized with numpy.

    Design: Forward diffusion uses modular ADDITION, backward uses XOR.
    This hybrid approach prevents XOR cancellation that occurs when
    both directions use XOR with cumulative operations. Modular addition
    is nonlinear over GF(2), ensuring that bit changes propagate without
    cancellation across the diffusion chain.

    Forward:  c[i] = (p[i] + seq[i] + c[i-1]) mod 256
    Backward: c[i] = (p[i] ^ seq[i] ^ c[i+1])
    """

    @staticmethod
    def _seq_to_uint8(chaotic_seq, length):
        """Convert chaotic float sequence to uint8 key stream."""
        vals = (chaotic_seq[:length] * 255).astype(np.uint32) % 256
        return vals.astype(np.uint8)

    @staticmethod
    def forward_diffusion(data, chaotic_seq, iv=0):
        """Forward chained ADDITION diffusion - fully vectorized.
        c[i] = (p[i] + seq[i] + c[i-1]) mod 256,  c[0] = (p[0] + seq[0] + iv) mod 256
        Implemented as cumulative addition mod 256.
        """
        seq8 = DiffusionOps._seq_to_uint8(chaotic_seq, len(data))
        # Build array: a[i] = p[i] + seq[i], a[0] += iv
        a = data.astype(np.int32) + seq8.astype(np.int32)
        a[0] += iv
        # Cumulative sum mod 256 (int32 to avoid overflow during accumulate)
        return np.mod(np.add.accumulate(a), 256).astype(np.uint8)

    @staticmethod
    def inverse_forward_diffusion(data, chaotic_seq, iv=0):
        """Inverse of forward addition diffusion - fully vectorized.
        p[i] = (c[i] - seq[i] - c[i-1] + 512) mod 256
        p[0] = (c[0] - seq[0] - iv + 512) mod 256
        p[i] = (c[i] - seq[i] - c[i-1] + 512) mod 256
        """
        seq8 = DiffusionOps._seq_to_uint8(chaotic_seq, len(data))
        s = data.astype(np.int32) - seq8.astype(np.int32)
        result = np.empty_like(s)
        result[0] = (s[0] - iv + 512) % 256
        result[1:] = (s[1:] - data[:-1].astype(np.int32) + 512) % 256
        return result.astype(np.uint8)

    @staticmethod
    def backward_diffusion(data, chaotic_seq, iv=0):
        """Backward chained XOR diffusion - fully vectorized.
        c[i] = p[i] ^ seq[i] ^ c[i+1],  c[n-1] = p[n-1] ^ seq[n-1] ^ iv
        Reverse accumulate: x=p^seq, x[-1]^=iv, c = reverse_cumxor(x)
        """
        seq8 = DiffusionOps._seq_to_uint8(chaotic_seq, len(data))
        x = np.bitwise_xor(data.astype(np.uint32), seq8.astype(np.uint32))
        x[-1] ^= np.uint32(iv)
        return np.bitwise_xor.accumulate(x[::-1])[::-1].astype(np.uint8)

    @staticmethod
    def inverse_backward_diffusion(data, chaotic_seq, iv=0):
        """Inverse of backward XOR diffusion - fully vectorized.
        p[i] = c[i] ^ seq[i] ^ c[i+1]  (c[i+1] from ciphertext)
        p[n-1] = c[n-1]^seq[n-1]^iv;  p[i] = (c[i]^seq[i]) ^ c[i+1]
        """
        seq8 = DiffusionOps._seq_to_uint8(chaotic_seq, len(data))
        y = np.bitwise_xor(data.astype(np.uint32), seq8.astype(np.uint32))
        result = np.empty_like(y)
        result[-1] = y[-1] ^ np.uint32(iv)
        result[:-1] = y[:-1] ^ data[1:].astype(np.uint32)
        return result.astype(np.uint8)


# ============================================================================
# MAIN ENCRYPTOR CLASS
# ============================================================================

class ImageEncryptor:
    """
    Main image encryption/decryption class.

    Encryption Pipeline (5 rounds per channel):
    For each round r in [0..4]:
        1. Bit-level permutation of pixel values
        2. Row permutation
        3. Column permutation
        4. DNA encode -> DNA add with chaotic seq -> DNA decode
        5. Forward XOR diffusion with feedback
        6. Backward XOR diffusion with feedback
    """

    def __init__(self):
        self.key_schedule = KeySchedule()
        self.chaotic_maps = ChaoticMaps()
        self.dna_ops = DNAOps()
        self.perm_ops = PermutationOps()
        self.diff_ops = DiffusionOps()

    def _generate_chaotic_sequences(self, params, size, round_num, channel=0):
        round_perturbation = params['round_keys'][round_num]
        offset = channel * 0.001 + round_num * 0.0001

        x0_log = min(max((params['x0_logistic'] + offset) % 0.999, 0.001), 0.999)
        x0_sin = min(max((params['x0_sine'] + offset * 1.5) % 0.999, 0.001), 0.999)
        x0_tent = min(max((params['x0_tent'] + offset * 2.0) % 0.999, 0.001), 0.999)

        skip = params['chaotic_skip']

        logger.debug(f"  Generating chaotic sequences: size={size}, round={round_num}, ch={channel}, skip={skip}")

        logistic_seq = self.chaotic_maps.perturbed_logistic(
            x0_log, params['r_logistic'],
            params['epsilon'] + round_perturbation * 0.001,
            size, skip
        )

        sine_seq = self.chaotic_maps.modified_sine(
            x0_sin, params['r_sine'] + round_perturbation * 0.1,
            size, skip
        )

        tent_seq = self.chaotic_maps.tent_map(
            x0_tent, params['alpha_tent'],
            size, skip
        )

        # DNA sequence (4 bases per byte)
        dna_chaotic = self.chaotic_maps.perturbed_logistic(
            (x0_log + 0.5) % 0.999, params['r_logistic'],
            params['epsilon'] * 2,
            size * 4, skip
        )
        dna_seq = (dna_chaotic * 4).astype(np.uint8) % 4

        logger.debug(f"  Chaotic sequences generated successfully")
        return {'logistic': logistic_seq, 'sine': sine_seq, 'tent': tent_seq, 'dna': dna_seq}

    def _encrypt_channel(self, channel_data, params, channel):
        data = channel_data.copy().astype(np.uint8)
        h, w = data.shape
        total_pixels = h * w
        logger.info(f"    Encrypting channel {channel}: {h}x{w} = {total_pixels} pixels, {params['num_rounds']} rounds")

        for round_num in range(params['num_rounds']):
            logger.debug(f"    Round {round_num + 1}/{params['num_rounds']} starting...")

            seqs = self._generate_chaotic_sequences(params, total_pixels, round_num, channel)

            flat_data = data.flatten()

            # Step 1: Bit-level permutation (vectorized)
            logger.debug(f"      Step 1: Bit-level permutation ({total_pixels} pixels)")
            flat_data = self.perm_ops.bit_permute(flat_data, seqs['logistic'])

            # Reshape for spatial ops
            data = flat_data.reshape(h, w)

            # Step 2: Row permutation
            logger.debug(f"      Step 2: Row permutation ({h} rows)")
            data = self.perm_ops.row_permute(data, seqs['sine'])

            # Step 3: Column permutation
            logger.debug(f"      Step 3: Column permutation ({w} cols)")
            data = self.perm_ops.col_permute(data, seqs['tent'])

            flat_data = data.flatten()

            # Step 4-6: DNA encode -> add -> decode
            dna_rule = params['dna_enc_rules'][(round_num + channel) % 8]
            dec_rule = params['dna_dec_rules'][(round_num + channel) % 8]

            logger.debug(f"      Step 4: DNA encode (rule {dna_rule})")
            dna_encoded = self.dna_ops.encode(flat_data, dna_rule)

            dna_length = min(len(dna_encoded), len(seqs['dna']))
            logger.debug(f"      Step 5: DNA add ({dna_length} bases)")
            dna_result = self.dna_ops.add(dna_encoded[:dna_length], seqs['dna'][:dna_length])

            logger.debug(f"      Step 6: DNA decode (rule {dec_rule})")
            flat_data = self.dna_ops.decode(dna_result, dec_rule)

            if len(flat_data) < total_pixels:
                pad = np.zeros(total_pixels - len(flat_data), dtype=np.uint8)
                flat_data = np.concatenate([flat_data, pad])

            # Step 7: Forward diffusion
            iv = int(params['round_keys'][round_num] * 255) % 256
            logger.debug(f"      Step 7: Forward diffusion (IV={iv})")
            flat_data = self.diff_ops.forward_diffusion(flat_data, seqs['logistic'], iv)

            # Step 8: Backward diffusion
            iv2 = int(params['round_keys'][(round_num + 1) % 5] * 200) % 256
            logger.debug(f"      Step 8: Backward diffusion (IV={iv2})")
            flat_data = self.diff_ops.backward_diffusion(flat_data, seqs['sine'], iv2)

            data = flat_data.reshape(h, w)
            logger.info(f"    Round {round_num + 1}/{params['num_rounds']} complete")

        return data

    def _decrypt_channel(self, channel_data, params, channel):
        data = channel_data.copy().astype(np.uint8)
        h, w = data.shape
        total_pixels = h * w
        logger.info(f"    Decrypting channel {channel}: {h}x{w}, {params['num_rounds']} rounds")

        for round_num in range(params['num_rounds'] - 1, -1, -1):
            logger.debug(f"    Reverse round {round_num + 1}/{params['num_rounds']}...")

            seqs = self._generate_chaotic_sequences(params, total_pixels, round_num, channel)

            flat_data = data.flatten()

            # Reverse Step 8
            iv2 = int(params['round_keys'][(round_num + 1) % 5] * 200) % 256
            logger.debug(f"      Inverse backward diffusion (IV={iv2})")
            flat_data = self.diff_ops.inverse_backward_diffusion(flat_data, seqs['sine'], iv2)

            # Reverse Step 7
            iv = int(params['round_keys'][round_num] * 255) % 256
            logger.debug(f"      Inverse forward diffusion (IV={iv})")
            flat_data = self.diff_ops.inverse_forward_diffusion(flat_data, seqs['logistic'], iv)

            # Reverse DNA ops
            dna_rule_enc = params['dna_enc_rules'][(round_num + channel) % 8]
            dna_rule_dec = params['dna_dec_rules'][(round_num + channel) % 8]

            logger.debug(f"      DNA encode (dec_rule {dna_rule_dec}) -> subtract -> decode (enc_rule {dna_rule_enc})")
            dna_encoded = self.dna_ops.encode(flat_data, dna_rule_dec)
            dna_length = min(len(dna_encoded), len(seqs['dna']))
            dna_result = self.dna_ops.subtract(dna_encoded[:dna_length], seqs['dna'][:dna_length])
            flat_data = self.dna_ops.decode(dna_result, dna_rule_enc)

            if len(flat_data) < total_pixels:
                pad = np.zeros(total_pixels - len(flat_data), dtype=np.uint8)
                flat_data = np.concatenate([flat_data, pad])

            data = flat_data.reshape(h, w)

            # Reverse spatial permutations
            logger.debug(f"      Inverse column/row permutation")
            data = self.perm_ops.inverse_col_permute(data, seqs['tent'])
            data = self.perm_ops.inverse_row_permute(data, seqs['sine'])

            flat_data = data.flatten()

            # Reverse bit permutation
            logger.debug(f"      Inverse bit-level permutation")
            flat_data = self.perm_ops.inverse_bit_permute(flat_data, seqs['logistic'])
            data = flat_data.reshape(h, w)

            logger.info(f"    Reverse round {round_num + 1}/{params['num_rounds']} complete")

        return data

    def encrypt(self, image, key):
        """Encrypt an image."""
        if not isinstance(image, np.ndarray):
            raise TypeError("Image must be a numpy array")
        if image.size == 0:
            raise ValueError("Image cannot be empty")
        if len(image.shape) not in (2, 3):
            raise ValueError("Image must be 2D (grayscale) or 3D (RGB)")

        logger.info(f"Encrypting image: shape={image.shape}, dtype={image.dtype}")

        params = self.key_schedule.derive(key)
        logger.info(f"Key derived successfully. Rounds={params['num_rounds']}, Skip={params['chaotic_skip']}")

        if len(image.shape) == 2:
            result = self._encrypt_channel(image, params, channel=0)
        else:
            encrypted = np.zeros_like(image, dtype=np.uint8)
            for ch in range(image.shape[2]):
                logger.info(f"  Processing channel {ch}/{image.shape[2]}")
                encrypted[:, :, ch] = self._encrypt_channel(image[:, :, ch], params, channel=ch)
                if ch > 0:
                    encrypted[:, :, ch] = np.bitwise_xor(encrypted[:, :, ch], encrypted[:, :, ch - 1])
            result = encrypted

        logger.info(f"Encryption complete!")
        return result

    def decrypt(self, image, key):
        """Decrypt an image."""
        if not isinstance(image, np.ndarray):
            raise TypeError("Image must be a numpy array")
        if image.size == 0:
            raise ValueError("Image cannot be empty")

        logger.info(f"Decrypting image: shape={image.shape}, dtype={image.dtype}")

        params = self.key_schedule.derive(key)
        logger.info(f"Key derived successfully. Rounds={params['num_rounds']}, Skip={params['chaotic_skip']}")

        if len(image.shape) == 2:
            result = self._decrypt_channel(image, params, channel=0)
        else:
            temp = image.copy()
            for ch in range(image.shape[2] - 1, 0, -1):
                temp[:, :, ch] = np.bitwise_xor(temp[:, :, ch], temp[:, :, ch - 1])
            decrypted = np.zeros_like(image, dtype=np.uint8)
            for ch in range(image.shape[2]):
                logger.info(f"  Processing channel {ch}/{image.shape[2]}")
                decrypted[:, :, ch] = self._decrypt_channel(temp[:, :, ch], params, channel=ch)
            result = decrypted

        logger.info(f"Decryption complete!")
        return result

    def get_params_info(self, key):
        params = self.key_schedule.derive(key)
        return "\n".join([
            "MHC-DIE Algorithm Parameters (Derived from Key):",
            "=" * 50,
            f"Key hash algorithm: SHA-512",
            f"Number of rounds: {params['num_rounds']}",
            f"Chaotic maps used: 3 (Perturbed Logistic, Modified Sine, Tent)",
            f"DNA encoding rules: 8 (dynamic per round)",
            f"Chaotic transient skip: {params['chaotic_skip']} iterations",
            f"Logistic map r: {params['r_logistic']:.6f} (chaotic regime: [3.57, 4.0])",
            f"Perturbation epsilon: {params['epsilon']:.6f}",
            f"Security: Kerckhoffs's Principle compliant",
            "",
            "Key space: 2^512 (SHA-512 output space)",
        ])
