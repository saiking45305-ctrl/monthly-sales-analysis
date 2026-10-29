#!/usr/bin/env python3
import csv, sys
for row in csv.DictReader(sys.stdin, delimiter='\t'):
    if row.get('date') and row.get('revenue'):
        print(f"{row['date'][:7]}\t{row['quantity']}\t{row['revenue']}")
