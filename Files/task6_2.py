#!/usr/bin/python3
def xor(first, second):
    return bytearray(x^y for x,y in zip(first, second))

message = "This is a known message!"
cipher_1 = "a469b1c502c1cab966965e50425438e1bb1b5f9037a4c159"
cipher_2 = "bf73bcd3509299d566c35b5d450337e1bb175f903fafc159"

p1 = bytes(message, 'utf-8')
c1 = bytearray.fromhex(cipher_1)
c2 = bytearray.fromhex(cipher_2)

result = xor(xor(c1, c2), p1)
print(result)
