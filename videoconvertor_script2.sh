#!/bin/bash
~/Downloads/ffmpeg.static.64bit.2014-07-16/ffmpeg \
-i $1 \
-r 29.76 -an  \
-vcodec libx264 \
$2
