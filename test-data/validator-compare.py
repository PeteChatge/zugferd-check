#!/usr/bin/env python3
"""
Vergleicht Track A CSV vs Track B CSV - offline, ohne Netz.
Usage: python validator-compare.py track-a.csv track-b.csv
"""
import csv, sys
a = {r['Dateiname']:r for r in csv.DictReader(open(sys.argv[1], encoding='utf-8'))} if len(sys.argv)>1 else {}
b = {r['Dateiname']:r for r in csv.DictReader(open(sys.argv[2], encoding='utf-8'))} if len(sys.argv)>2 else {}
print(f"A: {len(a)} B: {len(b)}")
for k in sorted(set(a)|set(b)):
    sa=a.get(k,{}).get('Status','—'); sb=b.get(k,{}).get('Status','—')
    mark = "✓" if sa==sb else "≠"
    print(f"{mark} {k:40} A:{sa:4} B:{sb:4}")
