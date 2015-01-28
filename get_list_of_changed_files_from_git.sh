#/bin/bash
git status | grep "^#\s*\(modified\|new\):\s\+" | sed -e "s/^#\s*\(modified\|new\):\s\+//" | sort | uniq | while read a; do li="$li $a"; echo $li; done | tail -n1
