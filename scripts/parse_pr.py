import json, sys

data = open(sys.argv[1]).read()
parts = data.split('---REVIEWS---')
pr_info = json.loads(parts[0])
rest = parts[1].split('---ISSUE_COMMENTS---')
reviews = json.loads(rest[0])
issue_comments = json.loads(rest[1])

print(f'=== {sys.argv[2]}: {pr_info["title"]} ===')
print()
print('-- REVIEW COMMENTS (non-bot) --')
for c in reviews:
    login = c['user']['login']
    if 'bot' not in login.lower():
        print(f'File: {c["path"]}:{c.get("line", c.get("original_line", "?"))}')
        print(f'User: @{login}')
        print(f'Body: {c["body"]}')
        print(f'URL: {c["html_url"]}')
        print()

print('-- ISSUE COMMENTS (non-bot) --')
for c in issue_comments:
    login = c['user']['login']
    if 'bot' not in login.lower():
        print(f'User: @{login}')
        print(f'Body: {c["body"]}')
        print()
