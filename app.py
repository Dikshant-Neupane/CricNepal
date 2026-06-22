"""
Main Entry point for Streamlit Community Cloud deployment.
This file is provided for convenience so you can select `app.py` directly when deploying.
"""
import os
import sys

# Ensure the app can find the src module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import and run the actual dashboard application
# Using exec ensures Streamlit catches all the magical module-level commands properly.
with open(os.path.join(os.path.dirname(__file__), "src", "dashboard", "app.py"), "r", encoding="utf-8") as f:
    exec(f.read())
