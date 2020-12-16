import os, sys, inspect, datetime

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

current_timestamp = datetime.datetime.now()

for directory in directories_to_check:
    directory_path = os.path.join(base_directory, directory)
    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)
        item_stat = os.stat(item_path)
        item_datetime_created = datetime.datetime.fromtimestamp(item_stat.st_ctime)

        if item_datetime_created > (current_timestamp - datetime.timedelta(hours=2)):
            # If its been created recently then we should insert it.
            print(item_stat)
            print(item_datetime_created)

