#!/bin/bash
cd "$(dirname "$0")"
echo "Installing libraries... please wait."
python3 -m pip install -r requirements.txt
echo "Launching the Real Estate Tool..."
python3 -m streamlit run app.py