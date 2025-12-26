@echo off
echo Installing libraries... please wait.
python -m pip install -r requirements.txt
echo.
echo Launching the Real Estate Tool...
python -m streamlit run app.py
pause