import os, sys, inspect

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpra_web_portal.settings")

import django
django.setup()

from cpra_web_portal import models

base_directory = "/pylon5/bcz3a2p/ewhite12/public/MP2023_production_runs"

directories_to_check = [
    'ADCIRC',
    'CLARA',
    'ICM'
]


for directory in directories_to_check:
    directory_path = os.path.join(base_directory, directory)
    print(os.listdir(directory_path))
    print(directory)


