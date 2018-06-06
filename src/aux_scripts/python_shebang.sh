#!/bin/sh
#NAME:	python_shebang.sh - changes python shebang in all python scripts
#
#SYNOPSIS:	python_shebang.sh path [-h]
#

if [ "$#" -eq 1 ] && ([ "$1" = "-h" ] || [ "$1" = "--help" ]); then
	echo "Usage: python_shebang.sh path [-h]"
	echo "  path   path where is python 3.5 or greater installed"
	echo "  -h     prints this help message"
	exit 1
fi

if [ "$#" -lt 1 ]; then
	printf "ERR: TOO FEW ARGUMENTS\n" 1>&2
	exit 1
fi
if [ "$#" -gt 1 ]; then
	printf "ERR: TOO MANY ARGUMENTS\n" 1>&2
	exit 1
fi

SHEBANG="#!$1"
PARENTDIR="$(dirname $0)"
if [ $PARENTDIR = "." ]; then
	DIR="$(cd "..";pwd)"
else
	DIR="$(pwd)"
fi
echo $DIR
echo $SHEBANG
PYTHON_FILES="$(find "$DIR" -type f -name \*.py)"
echo "$PYTHON_FILES"|while IFS= read -r line; do
  sed -i "1s|.*|$SHEBANG|" "$line"
done
