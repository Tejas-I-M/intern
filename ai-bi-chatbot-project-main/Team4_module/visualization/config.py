import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))

DATA_PATH = os.path.join(PROJECT_ROOT, 'Team1_module', 'data', 'processed', 'master_dataset.csv')
REPORT_PATH = os.path.join(BASE_DIR, 'reports')