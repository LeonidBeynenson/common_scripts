#!/bin/bash
IP=$1

if [ "x$IP" == "x" ]; then
	echo "Enter the parameter -- the IP number"
	exit 0
fi

#if present and non-empty then it is true
NUM_DAYS=$2

echo "IP=$IP"
if [ "x$NUM_DAYS" != "x" ]; then
	echo "Synchronyze $NUM_DAYS days (or a bit more)"
	A=$(ssh $IP "find ~/worklog -type f -name 'winlog*' -mtime -$NUM_DAYS" | grep -v "err$")
else
	echo "Synchronyze couple of last files"
	A=$(ssh $IP "find ~/worklog -type f -name 'winlog*' -mtime -1" | grep -v "err$")
fi
for a in $A; do echo "'$a' => " $(basename $a); done
for a in $A; do echo "'$a'"; scp $IP:$a ~/worklog/$(basename $a).remote; done

