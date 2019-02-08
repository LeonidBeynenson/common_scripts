#!/bin/bash
IP=$1

if [ "x$IP" == "x" ]; then
	echo "Enter the parameter -- the IP number"
	exit 0
fi

#if present and non-empty then it is true
SHOULD_ALL=$2

echo "IP=$IP"
if [ "x$SHOULD_ALL" != "x" ]; then
	echo "Synchronyze all folder"
	A=$(ssh $IP "find ~/worklog -type f -name 'winlog*'" | grep -v "err$")
else
	echo "Synchronyze couple of last files"
	A=$(ssh $IP "find ~/worklog -type f -name 'winlog*' -mtime -1" | grep -v "err$")
fi
for a in $A; do echo "'$a' => " $(basename $a); done
for a in $A; do echo "'$a'"; scp $IP:$a ~/worklog/$(basename $a).remote; done

