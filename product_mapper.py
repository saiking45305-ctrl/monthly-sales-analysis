#!/usr/bin/env python3
import csv, sys
for row in csv.DictReader(sys.stdin, delimiter='\t'):
    if row.get('product') and row.get('revenue'):
        print(f"{row['product']}\t{row['quantity']}\t{row['revenue']}")
