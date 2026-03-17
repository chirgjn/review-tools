import json, sys
files = json.load(sys.stdin)
for f in files:
    print(f['filename'])
