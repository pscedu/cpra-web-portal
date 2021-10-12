import os
import datetime
import pandas as pa

from django.forms.models import model_to_dict
from django.db.models import Sum, Count
from django.apps import apps
from django.core.cache import cache

from . import models


def populate_filters(filters):
    for filter_id, filter in filters.items():
        filter['options'] = []
        if filter['data_source'] == 'query':
            for filter_option in apps.get_model('cpra_web_portal', filter['data_source_model']).objects.all():
                filter_option = model_to_dict(filter_option)
                filter['options'].append({
                    'value': str(filter_option[filter['data_source_value']]),
                    'text': filter_option[filter['data_source_text']]
                })
        if 'default' in filter:
            filter['value'] = filter['default']


def set_filter_values(filters, request):
    for query_object in request.GET:
        if query_object in filters:
            value = request.GET.get(query_object)
            filter_type = filters[query_object]['data_source_value_type']
            if filter_type == 'list':
                value = value.split(",")
            elif filter_type == 'int':
                value = int(value)
            filters[query_object]['value'] = value


def filter_queryset(queryset, request):
    filter_dict = {}
    for filter_id, filter_obj in request.items():
        if 'value' in filter_obj:
            filter_dict[filter_id] = filter_obj['value']

    return queryset.filter(**filter_dict)


def update_approval(srv):
    users_to_email = []
    sim_run = srv.sr_id

    # If the SRV is not approved then get all of the related validation assignments
    if not srv.is_approved:
        sum_count_related_vas = models.ValidationAssignment.objects.filter(srv_id=srv).aggregate(
            num_related=Count('id'), num_approved=Sum('is_approved'))

        srv.is_approved = sum_count_related_vas['num_related'] == sum_count_related_vas['num_approved']
        srv.save()

    # Sim Run Flag update
    sim_run.is_flagged = models.SimulationRunValidation.objects.filter(is_flagged=1).all().exists()
    sim_run.save()
    # if the srv is approved now, get all of the srvs related to the subroutine and check whether they are all approved
    if srv.is_approved and not sim_run.is_approved and not sim_run.is_flagged:
        sum_count_related_subs = models.SimulationRunValidation.objects.filter(sr_id=sim_run,
                                                                               sub_id=srv.sub_id).aggregate(
            num_related=Count('id'), num_approved=Sum('is_approved'))

        # If they are all approved, do more checking/generation
        if sum_count_related_subs['num_related'] == sum_count_related_subs['num_approved']:
            last_wf_sim_sub = models.WFSimulationSubroutine.objects.filter(sim_id=sim_run.sim_id).order_by(
                'step').last()
            # Check to see if this subroutine is the last step for the SimRun
            if srv.sub_id == last_wf_sim_sub.sub_id:
                # If it is the last step, then update the sim run to be approved and return
                sim_run.is_approved = 1
                sim_run.save()
                return
            else:
                # If it is not the last step, get the next subroutine
                wf_sim_sub = models.WFSimulationSubroutine.objects.filter(sim_id=sim_run.sim_id,
                                                                          sub_id=srv.sub_id).first()
                next_wf_sim_sub = models.WFSimulationSubroutine.objects.filter(sim_id=sim_run.sim_id,
                                                                               step__gt=wf_sim_sub.step).order_by(
                    'step').select_related('sub_id').first()
                next_subroutine = next_wf_sim_sub.sub_id

                # Get the validation items associated with the next subroutine
                wf_sub_vis = models.WFSubroutineValidationItem.objects.filter(sub_id=next_subroutine).select_related(
                    'vi_id').all()

                # Check to see if there are actually validation items associated with the next subroutine.
                while not wf_sub_vis:
                    # Check to see if next_subroutine is the last subroutine
                    if next_subroutine == last_wf_sim_sub.sub_id:
                        sim_run.is_approved = 1
                        sim_run.save()
                        return
                    else:
                        # If it is not the last subroutine, get the next one and check its vis
                        next_wf_sim_sub = models.WFSimulationSubroutine.objects.filter(sim_id=sim_run.sim_id,
                                                                                       step__gt=next_wf_sim_sub.step).order_by(
                            'step').select_related('sub_id').first()
                        next_subroutine = next_wf_sim_sub.sub_id
                        wf_sub_vis = models.WFSubroutineValidationItem.objects.filter(
                            sub_id=next_subroutine).select_related('vi_id').all()

                # Get all of the wf_assignments for the sim_run and for the next subroutine
                wf_simulation_assignments = models.WFAssignment.objects.filter(sim_id=sim_run.sim_id).all()
                wf_subroutine_assignments = models.WFAssignment.objects.filter(sub_id=next_subroutine).all()
                for wf_sub_vi in wf_sub_vis:
                    validation_item = wf_sub_vi.vi_id
                    wf_validation_item_assignments = models.WFAssignment.objects.filter(vi_id=validation_item)
                    # Check to see if an SRV exists already
                    new_srv = models.SimulationRunValidation.objects.filter(
                        **{'sr_id': sim_run, 'sub_id': next_subroutine, 'vi_id': validation_item}).first()
                    if not new_srv:
                        # If no SRV exists, generate a new SRV
                        new_srv = models.SimulationRunValidation(
                            **{'sr_id': sim_run, 'sub_id': next_subroutine, 'vi_id': validation_item,
                               'datetime_created': datetime.datetime.now()})
                        new_srv.save()

                    # here we have all of the users/teams at the sim, sub, and vi level
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

    for user in users_to_email:
        user.email_user(
            'New QA/QC Assignments',
            "Hello " + user.username + ",\n\nThere are new assignments that have been generated for your review."
                                       "\n\nPlease review at your earliest convenience"
                                       "\n\nHappy QA/QCing!"
        )


def update_related_tables(related_tables):
    from django.apps import apps
    parent_table = related_tables.pop('parent_table')
    for related_table, actions in related_tables.items():
        related_table_model = apps.get_model('cpra_web_portal', related_table)
        for action in actions:
            if action == 'delete':
                related_table_model.objects.filter(id__in=actions[action]).delete()
            elif action == 'add':
                items_to_add = []
                for item_to_add in actions[action]:
                    item_to_add[parent_table['id_field']] = parent_table['id_value']
                    items_to_add.append(related_table_model(**item_to_add))
                related_table_model.objects.bulk_create(items_to_add)


def create_tasks(related_tables):
    parent_table = related_tables.get('parent_table')
    if 'WFAssignment' in related_tables:
        wf_assignment = related_tables.get('WFAssignment')
        if 'add' in wf_assignment:
            for assignment in wf_assignment['add']:
                filter_clause = {parent_table['id_field']: parent_table['id_value'], 'is_approved': 0}
                srvs = models.SimulationRunValidation.objects.filter(**filter_clause).all()
                for srv in srvs:
                    # if the id that was passed is a team id
                    # we need to get the related users and check to see if there are assignments
                    if assignment['team_id_id']:
                        users = models.UserTeam.objects.filter(team_id_id=assignment['team_id_id']).all()
                        for user in users:
                            if not models.ValidationAssignment.objects.filter(user_id=user.user_id, srv_id=srv):
                                va = models.ValidationAssignment(**{'srv_id': srv, 'user_id': user.user_id})
                                va.save()
                    # if the id that was passed is a user id - we only need to check to see if there are assignments
                    elif assignment['user_id_id'] and not models.ValidationAssignment.objects.filter(
                            user_id_id=assignment['user_id_id'], srv_id=srv):
                        # Then we need to create the validation assignment
                        va = models.ValidationAssignment(**{'srv_id': srv, 'user_id_id': assignment['user_id_id']})
                        va.save()
    elif 'UserTeam' in related_tables:
        user_team = related_tables.get('UserTeam')
        if 'add' in user_team:
            for user in user_team['add']:
                # We need to grab all of the assignments related to the team
                filter_clause = {parent_table['id_field']: parent_table['id_value']}
                wf_assignments = models.WFAssignment.objects.filter(**filter_clause).all()
                for wf_assignment in wf_assignments:
                    # Check to see which type of assignment this is
                    related_id = wf_assignment.sim_id if wf_assignment.sim_id else \
                        (wf_assignment.sub_id if wf_assignment.sub_id else wf_assignment.vi_id)
                    srv_filter = 'sr_id__sim_id' if wf_assignment.sim_id else \
                        ('sub_id' if wf_assignment.sub_id else 'vi_id')
                    # Grab the srvs related to this assignment (aka if the srvs exist)
                    srvs_to_check = models.SimulationRunValidation.objects.filter(
                        **{srv_filter: related_id, 'is_approved': 0})
                    for srv_to_check in srvs_to_check:
                        if not models.ValidationAssignment.objects.filter(user_id_id=user['user_id_id'],
                                                                          srv_id=srv_to_check):
                            va = models.ValidationAssignment(
                                **{'srv_id': srv_to_check, 'user_id_id': user['user_id_id']})
                            va.save()


def get_metric_files(metric, file_path):
    if metric.type == "dynamic_graph" and metric.graph_config['misc']['data_model'] != 'extraction_points':
        return get_dynamic_graph_metric_files(metric, file_path)

    if "map" in metric.type:
        parent_index = 0
        child_index = 9
    else:
        parent_index = 11
        child_index = 11
    # files will be structured as follows
    # files = {'region': {'point': 'filename'}}
    files = {}
    # I also need to get all of the files listed under this metric

    # file_path needs to be constructed if the metric has dynamic_file_path set
    if type(metric.graph_config) is dict and metric.graph_config.get('misc', {}).get('dynamic_file_path', {}):
        for x in metric.graph_config['misc']['dynamic_file_path']:
            # TODO: Rethink this for when we might be multiple levels deep
            for obj in sorted(os.scandir(file_path), key=lambda e: e.name):
                if obj.is_dir() and x['directory_regex'] in obj.name:
                    files[obj.name] = {}
                    for file in sorted(os.scandir(obj.path), key=lambda e: e.name):
                        if metric.file_name_regex in file.name:
                            file_name_list = file.name.split(metric.graph_config['misc']['delimiter'])
                            files[obj.name][file_name_list[metric.graph_config['misc']['child_index']]] = os.path.join(
                                obj.name, file.name)
    else:
        for file in (file for file in sorted(os.listdir(file_path)) if metric.file_name_regex in file) \
                if metric.file_name_regex else os.listdir(file_path):
            if os.path.isdir(os.path.join(file_path, file)):
                continue

            file_name_list = file.split("_")
            parent = file_name_list[parent_index] if "map" in metric.type else (file_name_list[child_index])[0:3]
            child = file_name_list[child_index] if "map" in metric.type else (file_name_list[child_index])[4:7]
            if parent in files:
                files[parent][child] = file
            else:
                files[parent] = {child: file}

    return files


def get_dynamic_graph_metric_files(metric, file_path):
    files = {'Hydro Compartments': {}}

    dynamic_graph_data_model = metric.graph_config['misc']['data_model']
    first_file = [f for f in os.listdir(file_path) if metric.file_name_regex in f][0]

    first_file_path = os.path.join(file_path, first_file)

    with open(first_file_path, 'r') as f:
        if dynamic_graph_data_model == 'daily_hydro_compartments':
            if not cache.keys(first_file + '_0'):
                csv_reader = pa.read_csv(f, header=None)
                num_cols = 0
                for col in csv_reader.columns:
                    cache.set(first_file + '_' + str(col), csv_reader[col])
                    num_cols += 1
            else:
                csv_reader = cache.get(first_file + '_0')
                num_cols = len(cache.keys(first_file + '_*'))
            num_rows = len(csv_reader)
        else:
            df = pa.read_csv(f)
            num_rows = len(df)
            num_cols = len(df.columns)

    for x in range(1, num_cols + 1):
        files['Hydro Compartments'][str(x)] = str(x)

    metric.graph_config['misc']['num_rows'] = num_rows
    return files


def get_comparison_cols(metric, file_path):
    first_file = [f for f in os.listdir(file_path) if metric.file_name_regex in f][0] if metric.file_name_regex else [os.listdir(file_path)][0]

    first_file_path = os.path.join(file_path, first_file)

    with open(first_file_path, 'r') as f:
        csv_reader = pa.read_csv(f)
        cols = list(csv_reader.columns)

    return cols
