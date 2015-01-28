#!/bin/bash
git rev-parse --quiet --verify HEAD 2> /dev/null >/dev/null || exit 0
git diff --no-ext-diff --quiet --exit-code || w="*"
git diff-index --cached --quiet HEAD -- || i="+"
if [ -n "$(git ls-files --others --exclude-standard)" ]; then
        u="%"
fi
echo "$w$i$u"

#notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')" qqq
