import sys
import os

# Add the project directory to sys.path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Ensure the database exists on startup
import config
from init_db import init_database

if not os.path.exists(config.DB_PATH):
    init_database(config.DB_PATH)

# Import Flask app as WSGI 'application' for PythonAnywhere / Gunicorn
from app import app as application

if __name__ == "__main__":
    application.run()
