import os, sys, inspect, datetime

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cpra_web_portal.settings")

import django
django.setup()

from cpra_web_portal import models


sims = models.Simulation.objects.all()

current_timestamp = datetime.datetime.now()

create_all_srvs = None

for sim in sims:
    sim_path = sim.results_dir
    new_sim_runs = []
    if sim.name=='ICM':
        # There are two different levels for ICM runs, S** and G***
        for s_level in os.listdir(sim_path):
            if "S" in s_level and len(s_level) == 3 and s_level not in ['S00', 'S04']:
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
    elif sim.name=='ADCIRC':
        # One sim run per Simulations.cpra_mp2023_2020system_vXXa.54_02
        for sim_run_version in (file for file in sorted(os.listdir(sim_path)) if 'Simulations.cpra_mp2023-' in file):
            sim_run_name = sim_run_version.split('.')[1]
            # TODO: Update w/ loading metadata file once Zach has confirmed this is in place
            print(sim_run_name)
            try:
                sim_run = models.SimulationRun.objects.get(name=sim_run_name)
                print("exists")
            except:
                sim_run = models.SimulationRun(**{
                    'name': sim_run_name,
                    'sim_id': sim,
                    'results_file_path': sim_run_version,
                    'datetime_created': datetime.datetime.now()
                })
                sim_run.save()
                new_sim_runs.append(sim_run)

    users_to_email = []

    for new_sim_run in new_sim_runs:
        wf_simulation_subroutines = models.WFSimulationSubroutine.objects.filter(sim_id=new_sim_run.sim_id).order_by('step')
        wf_simulation_subroutines = wf_simulation_subroutines.all() if create_all_srvs else wf_simulation_subroutines.filter(step=1).all()
        for wf_simulation_subroutine in wf_simulation_subroutines:
            subroutine = wf_simulation_subroutine.sub_id
            wf_sub_vis = models.WFSubroutineValidationItem.objects.filter(sub_id=subroutine).select_related(
                'vi_id').all()

            wf_simulation_assignments = models.WFAssignment.objects.filter(sim_id=new_sim_run.sim_id).all()
            wf_subroutine_assignments = models.WFAssignment.objects.filter(sub_id=subroutine).all()
            for wf_sub_vi in wf_sub_vis:
                validation_item = wf_sub_vi.vi_id
                wf_validation_item_assignments = models.WFAssignment.objects.filter(vi_id=validation_item)
                # Generate the Simulation Run Validations
                new_srv = models.SimulationRunValidation(
                    **{'sr_id': new_sim_run, 'sub_id': subroutine, 'vi_id': validation_item,
                       'datetime_created': datetime.datetime.now()})
                new_srv.save()

                # Generate assignments if it is the first subroutine
                if wf_simulation_subroutine.step == 1 and 'G500' not in new_sim_run.name:
                    for wf_assignment in wf_simulation_assignments.union(wf_subroutine_assignments,
                                                                         wf_validation_item_assignments):
                        # check whether this is a team or user assignment
                        if wf_assignment.team_id:
                            users = models.UserTeam.objects.filter(team_id=wf_assignment.team_id).all()
                            for user in users:
                                if not models.ValidationAssignment.objects.filter(user_id=user.user_id, srv_id=new_srv):
                                    va = models.ValidationAssignment(**{'srv_id': new_srv, 'user_id': user.user_id})
                                    va.save()
                                    if user.user_id not in users_to_email:
                                        users_to_email.append(user.user_id)
                        # if the id that was passed is a user id - we only need to check to see if there are assignments
                        elif wf_assignment.user_id and not models.ValidationAssignment.objects.filter(
                                user_id=wf_assignment.user_id, srv_id=new_srv):
                            # Then we need to create the validation assignment
                            va = models.ValidationAssignment(**{'srv_id': new_srv, 'user_id': wf_assignment.user_id})
                            va.save()
                            if wf_assignment.user_id not in users_to_email:
                                users_to_email.append(wf_assignment.user_id)



    # for user in users_to_email:
    #     user.email_user(
    #             'New QA/QC Assignments',
    #             "Hello " + user.username + ",\n\nThere are new assignments that have been generated for your review."
    #                                        "\n\nPlease review at your earliest convenience"
    #             "\n\nHappy QA/QCing!"
    #         )
