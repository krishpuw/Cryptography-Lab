#!/usr/bin/python3
def xor(first, second):
    return bytearray(x^y for x,y in zip(first, second))

yesorno = "5965730d0d0d0d0d0d0d0d0d0d0d0d0d"
currentiv = "40ed7da7ddfd82c9aa95224550f7b63c"
nextiv = "dbd907adddfd82c9aa95224550f7b63c"

guess = bytearray.fromhex(yesorno)
current_iv = bytearray.fromhex(currentiv)
next_iv = bytearray.fromhex(nextiv)

result = xor(xor(guess, current_iv), next_iv)
print(result.hex())
