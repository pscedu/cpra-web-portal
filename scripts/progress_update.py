import os, sys, inspect, datetime, pandas

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
    if sim.name == 'ICM':
        # Get the simulation tracker file
        progress_tracker = pandas.read_csv(os.path.join(sim_path, 'ICM_run_status.csv'))

        # There are two different levels for ICM runs, S** and G***
        for s_level in os.listdir(sim_path):
            if "S" in s_level and len(s_level) == 3 and s_level not in ['S00', 'S04']:
                for g_level in os.listdir(os.path.join(sim_path, s_level)):
                    if "G" in g_level and len(g_level) == 4 and g_level != 'G500':
                        # Check to see if this sim run exists yet
                        sim_run_name = s_level + "_" + g_level
                        print(sim_run_name)
                        try:
                            sim_run = models.SimulationRun.objects.get(name=sim_run_name)
                            progress_tracker_line = progress_tracker.loc[
                                (progress_tracker['S'] == s_level) & (progress_tracker['G'] == g_level)
                            ]

                            sim_run.progress_metric = progress_tracker_line.iloc[0][sim.progress_metric_field]
                            sim_run.save()
                        except Exception as e:
                            print(repr(e))
                            print('does not exist yet')
