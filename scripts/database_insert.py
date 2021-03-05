import os, sys, inspect, datetime

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpra_web_portal.settings")

import django
django.setup()

from cpra_web_portal import models


directories_to_check = [
    'ICM'
]

sims = models.Simulation.objects.all()

current_timestamp = datetime.datetime.now()

for sim in sims:
    sim_path = sim.results_dir
#    directory_path = os.path.join(base_directory, directory)
    new_sim_runs = []
    if sim.name=='ICM':
        # There are two different levels for ICM runs, S** and G***
        for s_level in os.listdir(sim_path):
            if "S" in s_level and len(s_level) == 3:
                for g_level in os.listdir(os.path.join(sim_path, s_level)):
                    if "G" in g_level and len(g_level) == 4:
                        # Check to see if this sim run exists yet
                        sim_run_name = s_level + "_" + g_level
                        print(sim_run_name)
                        try:
                            sim_run = models.SimulationRun.objects.get(name=sim_run_name)
                            print("exists")
                        except:
                            sim_run = models.SimulationRun(**{
                                'name': sim_run_name,
                                'sim_id': sim,
                                'results_file_path': s_level+'/'+g_level,
                                'datetime_created': datetime.datetime.now()
                            })
                            sim_run.save()
                            new_sim_runs.append(sim_run)

    # the creation of the sim runs may be unique, but populating the validation assignments for new sim_runs are NOT unique
    for new_sim_run in new_sim_runs:
        sim_user_id_assignments = []
        # Get related subroutines
        wf_simulation_subroutines = models.WFSimulationSubroutine.objects.filter(sim_id=new_sim_run.sim_id)
        wf_simulation_assignments = models.WFAssignment.objects.filter(sim_id=new_sim_run.sim_id)
        for wf_simulation_assignment in wf_simulation_assignments:
            sim_user_id_assignments.append(wf_simulation_assignment.user_id)

        for wf_simulation_subroutine in wf_simulation_subroutines:
            wf_subroutine_validation_items = models.WFSubroutineValidationItem.objects.filter(sub_id=wf_simulation_subroutine.sub_id)
            wf_subroutine_assignments = models.WFAssignment.objects.filter(sub_id=wf_simulation_subroutine.sub_id)
            subroutine_user_id_assignments = []
            for wf_subroutine_assignment in wf_subroutine_assignments:
                if wf_subroutine_assignment.user_id not in (sim_user_id_assignments + subroutine_user_id_assignments):
                    subroutine_user_id_assignments.append(wf_subroutine_assignment.user_id)

            # Have to create a srv for each of these
            for wf_subroutine_validation_item in wf_subroutine_validation_items:
                validation_item_user_id_assignments = []
                wf_validation_item_assignments = models.WFAssignment.objects.filter(vi_id=wf_subroutine_validation_item.vi_id)
                for wf_validation_item_assignment in wf_validation_item_assignments:
                    if wf_validation_item_assignment.user_id not in (sim_user_id_assignments + subroutine_user_id_assignments + validation_item_user_id_assignments):
                        validation_item_user_id_assignments.append(wf_validation_item_assignment.user_id)

                srv = models.SimulationRunValidation(**{
                    'sr_id': new_sim_run,
                    'sub_id': wf_simulation_subroutine.sub_id,
                    'vi_id': wf_subroutine_validation_item.vi_id,
                    'datetime_created': datetime.datetime.now()
                })
                srv.save()

                for user in (sim_user_id_assignments + subroutine_user_id_assignments + validation_item_user_id_assignments):
                    assignment = models.ValidationAssignment(**{
                        'user_id': user,
                        'srv_id': srv
                    })
                    assignment.save()




    # for item in os.listdir(directory_path):
    #     print(item)
    #     item_path = os.path.join(directory_path, item)
    #     item_stat = os.stat(item_path)
    #     item_datetime_created = datetime.datetime.fromtimestamp(item_stat.st_ctime)
    #
    #     if item_datetime_created > (current_timestamp - datetime.timedelta(hours=2)):
    #         # If its been created recently then we should insert it.
    #         # So what do we need to insert?
    #         # What do we need to grab?
    #
    #         # We should grab the simulation ID
    #         simulation = models.Simulation.objects.get(name=directory)
    #
    #         # Insert simulation_run item
    #         new_simulation_run_data = {
    #             'name': item,
    #             'sim_id': simulation,
    #             'datetime_created': current_timestamp,
    #             'results_file_path': item_path
    #         }
    #
    #         new_simulation_run = models.SimulationRun(**new_simulation_run_data)
    #
    #         new_simulation_run.save()
    #
    #         # TODO: Add fixtures for these other tables so that we can test the script all the way through.
    #         # We should grab the related wf_simulation_subroutines
    #         wf_simulation_subroutines = models.WFSimulationSubroutine.objects.filter(sim_id=simulation.pk)
    #         # Grab the related wf_subroutine_validation_items
    #
    #         for wf_simulation_subroutine in wf_simulation_subroutines:
    #             wf_subroutine_validation_items = models.WFSubroutineValidationItem.objects.filter(list_id=wf_simulation_subroutine.sub_vi_list_id)
    #             # Grab the related wf_assignments
    #
    #             for wf_subroutine_validation_item in wf_subroutine_validation_items:
    #                 wf_assignments = models.WFAssignment.objects.filter(sim_id=simulation, sub_id=wf_subroutine_validation_item.sub_id,
    #                                                     vi_id=wf_subroutine_validation_item.vi_id)
    #                 # Insert validation_assignment items
    #                 for wf_assignment in wf_assignments:
    #                     validation_assignment_item_data = {
    #                         'sr_id': new_simulation_run,
    #                         'sub_id': wf_assignment.sub_id,
    #                         'vi_id': wf_assignment.vi_id,
    #                         'user_id': wf_assignment.user_id,
    #                         'datetime_created': current_timestamp
    #                     }
    #                     validation_assignment_item = models.ValidationAssignment(**validation_assignment_item_data)
    #                     validation_assignment_item.save()
    #
    #         print(item_stat)
    #         print(item_datetime_created)

