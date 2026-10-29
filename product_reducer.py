#!/usr/bin/env python3
import sys
current=None; orders=units=0; revenue=0.0
for line in sys.stdin:
    key, q, rev = line.rstrip('\n').split('\t'); q=int(q); rev=float(rev)
    if current != key:
        if current is not None: print(f"{current}\t{orders}\t{units}\t{revenue:.2f}")
        current=key; orders=units=0; revenue=0.0
    orders += 1; units += q; revenue += rev
if current is not None: print(f"{current}\t{orders}\t{units}\t{revenue:.2f}")
