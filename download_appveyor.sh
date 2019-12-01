#! /bin/bash

# COMMIT=$(git show-ref --head HEAD | cut -f 1 -d" ")
appveyor-dist \
	-u MikeCFletcher \
	-p pyvrml97 \
	--dist dist
