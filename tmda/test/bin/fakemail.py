#!/usr/bin/env python3

import sys

print('FAKE SENDMAIL ARGS:', sys.argv)

for line in sys.stdin:
    print(line, end=' ')

sys.exit(0)
