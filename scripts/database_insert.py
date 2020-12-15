import os
import sqlalchemy

engine = sqlalchemy.create_engine("db_url")

base_directory = "/pylon5/bcz3a2p/ewhite12/public/MP2023_production_runs"

directories_to_check = os.listdir(base_directory)


for directory in directories_to_check:
    print(directory)

