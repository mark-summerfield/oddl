#!/bin/bash
tokei -slines -f -tPython -esetup.py -et.py
unrecognized.py -q oddl.py
python3 -m flake8 \
    --ignore=E261,E303,W504 \
    oddl.py
python3 -m vulture oddl.py
./t.py $@
git st
