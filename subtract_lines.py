#!/usr/bin/env python

import re
import sys
import datetime
import math

first_line = None
last_line = None

for line in sys.stdin:
    if last_line:
        print(last_line, end="")

    if not first_line:
        first_line = line

    last_line = line

date_re = re.compile(r'^[0-9-_]+')

first_date_match = date_re.match(first_line)
last_date_match = date_re.match(last_line)

if first_date_match and last_date_match:
    first_date = first_date_match.group()
    last_date = last_date_match.group()

    first_time = datetime.datetime.strptime(first_date, "%Y-%m-%d_%H-%M-%S")
    last_time = datetime.datetime.strptime(last_date, "%Y-%m-%d_%H-%M-%S")

    dt_time = last_time - first_time

    numsec = int(dt_time.total_seconds())
    nummin = int(math.ceil( (numsec + 10.0) / 60.0))
    print("\nrest {} min\n".format(nummin))

print(last_line, end="")
