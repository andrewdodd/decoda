#!bash
(python -c "import build" 2>&1) > /dev/null
has_build=$?

if [ $has_build -eq 0 ]; then
    exit 0
else
    echo "build dependency not found"
    echo " Try > pip install build"
    exit 1
fi
