#/bin/bash
git status --porcelain | grep "^.[A-Z]" | sed -e "s/^.. *//" | sort | uniq | while read a; do li="$li $a"; echo $li; done | tail -n1
