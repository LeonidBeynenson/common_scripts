while read a; do
	echo "==="
	echo $a
	ffprobe $a
	echo "=="
done
