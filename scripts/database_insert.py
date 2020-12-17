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
            # So what do we need to insert?
            # What do we need to grab?

            # We should grab the simulation ID
            simulation = models.Simulation.objects.get(name=directory)

            # Insert simulation_run item
            new_simulation_run_data = {
                'name': item,
                'sim_id': simulation,
                'datetime_created': current_timestamp,
                'results_file_path': item_path
            }

            new_simulation_run = models.SimulationRun(**new_simulation_run_data)

            new_simulation_run.save()

            # TODO: Add fixtures for these other tables so that we can test the script all the way through.
            # We should grab the related wf_simulation_subroutines
            wf_simulation_subroutines = models.WFSimulationSubroutine.objects.filter(sim_id=simulation.pk)
            # Grab the related wf_subroutine_validation_items

            for wf_simulation_subroutine in wf_simulation_subroutines:
                wf_subroutine_validation_items = models.WFSubroutineValidationItem.objects.filter(list_id=wf_simulation_subroutine.sub_vi_list_id)
                # Grab the related wf_assignments

                for wf_subroutine_validation_item in wf_subroutine_validation_items:
                    wf_assignments = models.WFAssignment.objects.filter(sim_id=simulation, sub_id=wf_subroutine_validation_item.sub_id,
                                                        vi_id=wf_subroutine_validation_item.vi_id)
                    # Insert validation_assignment items
                    for wf_assignment in wf_assignments:
                        validation_assignment_item_data = {
                            'sr_id': new_simulation_run,
                            'sub_id': wf_assignment.sub_id,
                            'vi_id': wf_assignment.vi_id,
                            'user_id': wf_assignment.user_id,
                            'datetime_created': current_timestamp
                        }
                        validation_assignment_item = models.ValidationAssignment(**validation_assignment_item_data)
                        validation_assignment_item.save()

            print(item_stat)
            print(item_datetime_created)

