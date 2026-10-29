#!/usr/bin/env python3
import sys
current=None; orders=units=0; revenue=0.0
def emit(key, orders, units, revenue):
    if key is not None: print(f"{key}\t{orders}\t{units}\t{revenue:.2f}")
for line in sys.stdin:
    key, q, rev = line.rstrip('\n').split('\t'); q=int(q); rev=float(rev)
    if current != key:
        emit(current, orders, units, revenue); current=key; orders=units=0; revenue=0.0
    orders += 1; units += q; revenue += rev
emit(current, orders, units, revenue)
