#!/usr/bin/python3

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

plaintext = b"This is a top secret."
ciphertext = bytearray.fromhex("764aa26b55a4da654df6b19e4bce00f4ed05e09346fb0e762583cb7da2ac93a2")

iv = bytearray.fromhex("aabbccddeeff00998877665544332211")

with open("words.txt", "r") as file:
    for lines in file:
        words = lines.strip()
        if len(words) <= 16:
            key_padded = words + '#' * (16 - len(words))
            byte_key = bytes(key_padded, 'utf-8')
            try:
                cipher = AES.new(byte_key, AES.MODE_CBC, iv)
                ct_bytes = cipher.encrypt(pad(plaintext, 16))
                if ct_bytes == ciphertext:
                    print("the key is", key_padded)
                    break
            except:
                continue

