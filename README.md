# SEED Labs — Secret-Key Encryption Lab

A complete walkthrough of the [SEED Labs Secret-Key Encryption Lab](https://seedsecuritylabs.org/Labs_20.04/Crypto/Crypto_Encryption/), covering secret-key encryption concepts, encryption modes, padding, initial vectors (IVs), and common cryptographic mistakes — plus the full environment setup used to run it on Apple Silicon.

This repo documents both the **lab solutions** (Tasks 1–7) and the **non-trivial VM setup** required to get a SEED Labs environment running under VMware Fusion on an ARM64 Mac, where the stock x86 SEED VM image isn't available.

---

## Table of Contents

- [Environment Setup](#environment-setup)
  - [VM Installation (Ubuntu Server ARM64)](#vm-installation-ubuntu-server-arm64)
  - [GUI via TightVNC + XFCE](#gui-via-tightvnc--xfce)
  - [Connecting to the VM](#connecting-to-the-vm)
  - [Common Setup Problems & Fixes](#common-setup-problems--fixes)
- [Lab Tasks](#lab-tasks)
  - [Task 1 — Frequency Analysis](#task-1--frequency-analysis)
  - [Task 2 — Encryption with Different Ciphers & Modes](#task-2--encryption-with-different-ciphers--modes)
  - [Task 3 — ECB vs. CBC](#task-3--ecb-vs-cbc)
  - [Task 4 — Padding](#task-4--padding)
  - [Task 5 — Error Propagation](#task-5--error-propagation)
  - [Task 6 — Initial Vector (IV) & Common Mistakes](#task-6--initial-vector-iv--common-mistakes)
  - [Task 7 — Programming with the Crypto Library](#task-7--programming-with-the-crypto-library)
- [Tools & Concepts Used](#tools--concepts-used)
- [References](#references)

---

## Environment Setup

The standard SEED Labs VM is distributed as an x86-64 image. On Apple Silicon (M-series) Macs this won't run under VMware Fusion, so the environment was built from scratch on **Ubuntu Server 22.04 ARM64**, with a lightweight desktop added on top for the GUI tasks.

### VM Installation (Ubuntu Server ARM64)

- **Host:** Apple Silicon Mac, VMware Fusion
- **Guest:** Ubuntu 22.04.5 LTS Server (ARM64) — `ubuntu-22.04.5-live-server-arm64.iso`
- **Guide followed:** [SEED Labs v2 Apple-ARM setup](https://github.com/seed-labs/seed-labs/blob/master/lab-setup/apple-arm/seedvm-v2/SeedVM-Ubuntu_Installation.md)

After the base OS install, the SEED Labs software was installed via the project's `install.sh` from the `src-arm` package:

```bash
# Download and run the SEED setup (ARM build)
curl -O https://seedsecuritylabs.org/setup/src-arm.zip
unzip src-arm.zip
cd src-arm
sudo ./install.sh
```

During install:
- Wireshark → selected **No** for non-superuser packet capture
- Display manager → selected **LightDM**
- Installed `open-vm-tools-desktop` for VMware guest integration

Two accounts exist on the VM:
- `seeds` — general admin account created during the Ubuntu install
- `seed` — SEED Labs dedicated account created by `install.sh`, used for lab work

### GUI via TightVNC + XFCE

GNOME does **not** work in this VM — there's no VMware SVGA driver for ARM64 (no `/dev/dri/card0`, no `/dev/fb0` framebuffer), so GDM/GNOME crashes on launch. The fix is a lightweight desktop (XFCE) served over TightVNC, which needs no GPU:

```bash
# Install
sudo apt install -y tightvncserver xfce4 xfce4-goodies

# ~/.vnc/xstartup should contain:
#   #!/bin/sh
#   startxfce4

# Start / stop the VNC server (display :1 → port 5901)
vncserver :1
vncserver -kill :1
```

### Connecting to the VM

**SSH:**
```bash
ssh seeds@172.16.83.130     # admin account
ssh seed@172.16.83.130      # SEED lab account
```

**VNC** (macOS: Finder → `Cmd+K` → Connect to Server):
```
vnc://172.16.83.130:5901
```
> Port `5901` = `5900 + display number` (display `:1`).

**Running GUI apps over SSH** (e.g. `eog`, `bless`) — point them at the VNC display:
```bash
DISPLAY=:1 eog pic_ecb.bmp &
DISPLAY=:1 bless cipher.bin &
```

### Common Setup Problems & Fixes

| Problem | Cause | Fix |
|---|---|---|
| Host disk full (`Docker.raw` ballooned to 245 GB) | Docker image/volume buildup | `docker system prune -a --volumes` |
| Console freezes at `EFI stub: Exiting boot services...` every boot | Known Fusion ARM64 console-rendering bug — VM is actually booting fine | Ignore the console; confirm with `ping` / `ssh` |
| `Failed unmounting /cdrom` on reboot | CD-ROM lock after install | Fusion dialog → "Disconnect anyway and override the lock" → Enter |
| GNOME/GDM crashes, Xorg `Failed to load module vmware` | No ARM64 VMware SVGA driver / no framebuffer | Use TightVNC + XFCE instead |
| `vncserver` fails with font-path error | Stale lock files | `vncserver -kill :1 && rm -f ~/.vnc/*.pid ~/.vnc/*.log && vncserver :1` |
| macOS "enable Screen Sharing / Remote Management" error on connect | VNC server not running on the VM (nothing on port 5901) | SSH in, `ps aux \| grep vnc`, then `vncserver :1` |
| Forgot VNC password | — | SSH in as `seeds`, run `vncpasswd`, then restart `vncserver` |

---

## Lab Tasks

The lab container (used only in Task 6.3) is managed with Docker Compose:

```bash
docker compose build     # build the container image
docker compose up -d      # start (oracle listens at 10.9.0.80:3000)
docker compose down       # tear down
```
> On this setup the standalone `docker-compose` binary wasn't present; the bundled `docker compose` (with a space) plugin was used instead.

### Task 1 — Frequency Analysis

Break a monoalphabetic substitution cipher using n-gram frequency analysis — no key given.

- Ran the provided `freq.py` to get 1-gram, 2-gram, and 3-gram statistics.
- Dominant trigram `ytn` (78) → **THE**, giving `y→t`, `t→h`, `n→e`. Cross-checked against top bigrams (`yt`→th, `tn`→he, `yn`→te).
- Second trigram `vup` (30) → **AND**, giving `v→a`, `u→n`, `p→d` (validated by `up`→nd).
- Substituted known letters back with `tr` (solved letters in uppercase) and iterated — each pass revealed more common words (`WITH`, `OF`, `ONE`, `WAS`, `OUT`), supplying new mappings until the full 26-letter key was recovered.

```bash
./freq.py
tr 'ytnvup' 'THEAND' < ciphertext.txt > attempt1.txt
# ...repeat, refining the substitution each pass
```

**Result:** fully decoded plaintext (a 2018 Oscars / #MeToo news article).

### Task 2 — Encryption with Different Ciphers & Modes

Encrypt a file with ≥3 cipher/mode combinations using OpenSSL's `enc`:

```bash
openssl enc -aes-128-cbc -e -in task2.txt -out cipher_cbc.bin \
  -K 00112233445566778899aabbccddeeff \
  -iv 0102030405060708090a0b0c0d0e0f10
```
Also exercised `aes-128-cfb`, `aes-128-ofb`, and `des-ede3-cbc` (3DES). Ciphertext inspected with `xxd` / `hexdump -C`; round-trip verified by decrypting and `diff`-ing against the original.

> **Note:** For AES modes the IV must be 16 bytes (32 hex chars) — it's tied to AES's **block size**, not the key size. 3DES uses an 8-byte (16-hex) IV.

### Task 3 — ECB vs. CBC

Encrypt a `.bmp` image in ECB and CBC, then reattach the original 54-byte header so it renders as an image:

```bash
head -c 54 pic_original.bmp > header
tail -c +55 pic_ecb.bin > body_ecb
cat header body_ecb > pic_ecb.bmp
DISPLAY=:1 eog pic_ecb.bmp &
```

**Observation:** In **ECB**, the original shapes (ellipse, rectangle) remain clearly visible — identical plaintext blocks map to identical ciphertext blocks, so structure leaks. In **CBC**, the output is uniform random noise — chaining ensures identical plaintext blocks produce different ciphertext. ECB is unsafe for structured data even with a strong cipher.

### Task 4 — Padding

- **ECB and CBC require padding** (block modes — the final block must be full); **CFB and OFB do not** (stream-like — ciphertext length equals plaintext length).
- Created 5-, 10-, and 16-byte files and encrypted with AES-128-CBC. Decrypted with `-nopad` to expose the raw padding, viewed with `hexdump -C`.

**PKCS#5 finding:** padding bytes equal the *number* of padding bytes added. A 5-byte file → 11 bytes of `0x0b`; a 10-byte file → 6 bytes of `0x06`; a **16-byte file → a whole extra block of 16 bytes of `0x10`** (padding is always added, even when already block-aligned).

### Task 5 — Error Propagation

Flip a single bit in the 55th byte of a ciphertext, decrypt, and compare to the original with `cmp -l`:

| Mode | Corruption effect |
|---|---|
| **ECB** | One full 16-byte block garbled (bytes 49–64); nothing else |
| **CBC** | Full block garbled (49–64) + 1 bit flipped at the same offset in the next block |
| **CFB** | 1 bit at the corruption point (55) + the entire next block garbled (65–80) |
| **OFB** | Exactly 1 bit in 1 byte (55); no propagation |

OFB self-heals immediately; ECB/CBC/CFB each lose a full block, with CBC/CFB leaking a small error into a neighboring block.

### Task 6 — Initial Vector (IV) & Common Mistakes

**6.1 — IV uniqueness:** Encrypting the same plaintext + key + IV gives byte-identical ciphertext (`cmp` → no diff); changing only the IV changes the ciphertext from byte 1. Reused IVs leak when two messages are identical.

**6.2 — Reused IV in OFB (known-plaintext attack):** Since the OFB keystream depends only on key+IV, reusing the IV reuses the keystream, so `P2 = C1 ⊕ C2 ⊕ P1`. Recovered the hidden plaintext with a short XOR script.
> **CFB variant:** only the **first block** of P2 is recoverable — later CFB keystream depends on the previous ciphertext block, which diverges once P1 ≠ P2.

**6.3 — Predictable IV (chosen-plaintext / BEAST-style attack):** Against a CBC oracle that reveals the next (predictable) IV, craft `X = guess ⊕ IV_bob ⊕ IV_next`. When the oracle encrypts `X` with `IV_next`, the block-cipher input equals `guess ⊕ IV_bob` — so the resulting ciphertext matches Bob's **iff** the guess equals Bob's message. Matching ciphertext confirmed Bob's secret was **"Yes"**.
> Key gotcha: the guess must reproduce Bob's exact pre-encryption block, i.e. `"Yes"` padded with **PKCS#5** (`0x0d × 13`), not zero-padding.

### Task 7 — Programming with the Crypto Library

Given a plaintext, ciphertext, and IV (AES-128-CBC), recover the key — a dictionary word under 16 chars, padded with `#` (`0x23`) to 128 bits.

Implemented a **dictionary attack** that calls the crypto library directly (per the lab rule — no shelling out to `openssl`). For each word it builds the padded key, encrypts the known plaintext, and compares against the known ciphertext:

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

plaintext  = b"This is a top secret."
ciphertext = bytearray.fromhex("764aa26b55a4da654df6b19e4bce00f4ed05e09346fb0e762583cb7da2ac93a2")
iv         = bytearray.fromhex("aabbccddeeff00998877665544332211")

with open("words.txt") as f:
    for line in f:
        word = line.strip()
        if len(word) <= 16:
            key = bytes(word + '#' * (16 - len(word)), 'utf-8')
            if AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plaintext, 16)) == ciphertext:
                print("The key is", word)
                break
```

**Result:** against a 25,143-word list the key was found in seconds — **`Syracuse`** (padded to `Syracuse########`).

A C version using OpenSSL's EVP API (`gcc task7.c -lcrypto`) is also included as an alternative.

> The `#` padding here fills the **key** to AES-128's 128-bit **key size** — a separate "16" from Task 4's block-size padding of the plaintext.

**Takeaway:** AES itself isn't broken here. The attack works purely because the key was a predictable dictionary word — security depends on key *unpredictability*, not just on the cipher.

---

## Tools & Concepts Used

- **Ciphers/modes:** AES-128 (ECB, CBC, CFB, OFB), 3DES, monoalphabetic substitution
- **Tooling:** OpenSSL `enc`, Python (PyCryptodome), C (OpenSSL EVP API, `-lcrypto`), Bash, `xxd`/`hexdump`/`cmp`, `bless`, `tr`, Docker Compose
- **Concepts:** frequency analysis, encryption modes, PKCS#5 padding, error propagation, IV uniqueness/unpredictability, known-plaintext & chosen-plaintext attacks, dictionary attacks

## References

- [SEED Labs — Secret-Key Encryption Lab](https://seedsecuritylabs.org/Labs_20.04/Crypto/Crypto_Encryption/)
- [SEED Labs Apple-ARM VM setup guide](https://github.com/seed-labs/seed-labs/blob/master/lab-setup/apple-arm/seedvm-v2/SeedVM-Ubuntu_Installation.md)
- [OpenSSL EVP Symmetric Encryption API](https://docs.openssl.org/1.1.1/man3/EVP_EncryptInit/)
- [PyCryptodome — Encrypt data with AES](https://www.pycryptodome.org/src/examples#encrypt-data-with-aes)

---

*Secret-Key Encryption Lab © 2018 Wenliang Du (SEED Labs). Lab solutions and setup notes by Krish Puwar.*
