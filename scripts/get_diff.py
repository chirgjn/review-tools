import json, sys
files = json.load(sys.stdin)
target = sys.argv[2] if len(sys.argv) > 2 else None
for f in files:
    if target and target not in f['filename']:
        continue
    print(f"=== {f['filename']} ===")
    print(f.get('patch', 'NO PATCH'))
    print()
