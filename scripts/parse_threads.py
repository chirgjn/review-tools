import json, sys, collections

data = open(sys.argv[1]).read()
pr_num = sys.argv[2]

parts = data.split('---REVIEWS---')
pr_info = json.loads(parts[0])
rest = parts[1].split('---ISSUE_COMMENTS---')
reviews = json.loads(rest[0])

# Group comments into threads by root comment id
threads = collections.OrderedDict()
for c in reviews:
    rid = c.get('in_reply_to_id')
    if rid is None:
        threads[c['id']] = {'root': c, 'replies': []}
    else:
        if rid in threads:
            threads[rid]['replies'].append(c)
        else:
            # reply to a reply — find root
            for tid, t in threads.items():
                if any(r['id'] == rid for r in t['replies']):
                    t['replies'].append(c)
                    break

print(f'=== PR {pr_num}: {pr_info["title"]} ===\n')
for tid, t in threads.items():
    root = t['root']
    all_msgs = [root] + t['replies']
    # Skip all-bot threads
    non_bot = [m for m in all_msgs if 'bot' not in m['user']['login'].lower()]
    if not non_bot:
        continue
    print(f'Thread: {root["path"]}:{root.get("line", root.get("original_line", "?"))}')
    print(f'URL: {root["html_url"]}')
    for m in all_msgs:
        login = m['user']['login']
        print(f'  @{login}: {m["body"][:300]}')
    print()
