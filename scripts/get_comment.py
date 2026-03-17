import json, sys
data = open(sys.argv[1]).read()
parts = data.split('---REVIEWS---')
rest = parts[1].split('---ISSUE_COMMENTS---')
reviews = json.loads(rest[0])
target_ids = sys.argv[2:]
for c in reviews:
    if str(c['id']) in target_ids or str(c.get('in_reply_to_id','')) in target_ids:
        print(f"id={c['id']} reply_to={c.get('in_reply_to_id')} user={c['user']['login']} body={c['body'][:400]}")
        print(f"diff_hunk={c['diff_hunk'][-300:]}")
        print()
