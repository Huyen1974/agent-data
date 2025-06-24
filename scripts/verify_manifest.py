import sys

col = {l.strip() for l in open(sys.argv[1]) if l.startswith('tests/')}
man = {l.strip() for l in open('tests/manifest_LOCK.txt')}

missing, extra = man - col, col - man

with open('missing.txt', 'w') as f, open('extra.txt', 'w') as e:
    f.write('\n'.join(sorted(missing)))
    e.write('\n'.join(sorted(extra)))

print(f'Thiếu: {len(missing)}, Dư: {len(extra)}')
sys.exit(1 if len(missing) or len(extra) else 0) 