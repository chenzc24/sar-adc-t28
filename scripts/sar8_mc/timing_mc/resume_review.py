"""Handoff only the retired reference reviewer after the known empty-line parse error."""
import json
import os
import sys
import time
d=os.path.dirname(os.path.abspath(__file__))
for _ in range(1920):
    with open(d+'/status.json') as f:s=json.load(f)
    if s['stage']=='complete':break
    if s['stage']=='held':
        if 'len(names)==len(vals)' in s.get('traceback',''):
            os.execv(sys.executable,[sys.executable,d+'/review_v2.py'])
        break
    time.sleep(15)
