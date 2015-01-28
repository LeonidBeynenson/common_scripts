#!/bin/bash 
ffmpeg \
-i ~/_Work/ESMStitchingDatasets/esm_data-2014-06-18/NV_building/videos/VID_20000531_024907.3gp \
-r 29.76 -an  \
-vcodec libx264 -b 2000000 \
output.avi
