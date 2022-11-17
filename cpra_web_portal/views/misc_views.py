import json
import os
import csv

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.forms.models import model_to_dict
from django.http import HttpResponse, FileResponse
from django.template import loader
from django.utils import timezone
from django.views import View
from django.core.cache import cache
from django.db.models import Sum, Count
from django.core.serializers.json import DjangoJSONEncoder
import pandas as pa
import zipfile
import re

from cpra_web_portal import models, utils


def get_extraction_points(request):
    sim_run_id = request.GET.get('sim_run_id')
    sim_run = models.SimulationRun.objects.get(pk=sim_run_id)
    metric = models.Metric(**{
        'type': 'dynamic_graph',
        'file_path': 'geomorph/output_qaqc',
        'graph_config': {
            'misc': {
                'data_model': 'extraction_points'
            }
        },
        'file_name_regex': 'MP2023_'
    })
    file_path = os.path.join(
        sim_run.sim_id.results_dir,
        sim_run.results_file_path,
        metric.file_path
    )

    try:
        files = utils.get_metric_files(metric, file_path)
    except FileNotFoundError as e:
        print(repr(e))
        return HttpResponse(json.dumps({'success': False, 'message': 'Directory/Files not yet available.'}))

    response = {'extraction_points': files}

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


def get_extraction_point_values(request):
    sim_run_id = request.GET.get('sim_run_id')
    sim_run = models.SimulationRun.objects.get(pk=sim_run_id)
    file_name = request.GET.get('file_name')
    file_path = os.path.join(
        sim_run.sim_id.results_dir,
        sim_run.results_file_path,
        'geomorph/output_qaqc',
        file_name
    )
    with open(file_path, "r") as f:
        dict_reader = csv.DictReader(f)
        json_from_csv = list(dict_reader)

    return HttpResponse(json.dumps(json_from_csv))


def get_metric(request):
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    validation_assignment = models.SimulationRunValidation.objects.filter(
        id=validation_assignment_id).select_related('sr_id').first()

    file_path = os.path.join(
        validation_assignment.sr_id.sim_id.results_dir,
        validation_assignment.sr_id.results_file_path,
        metric.file_path
    )

    try:
        files = utils.get_metric_files(metric, file_path)
    except FileNotFoundError as e:
        print(repr(e))
        return HttpResponse(json.dumps({'success': False, 'message': 'Directory/Files not yet available.'}))

    response = {
        'metric': model_to_dict(metric),
        'files': files
    }

    if metric.type == 'dynamic_graph' and metric.graph_config.get('misc', {}).get('comparison_type', False):
        response['columns'] = utils.get_comparison_cols(metric, file_path)

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


def export_metric(request):
    response = None
    file_name = request.GET.get('file_name')
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()
    metric_data_model = metric.graph_config['misc']['data_model'] if metric.type == 'dynamic_graph' else ''

    validation_assignment = models.SimulationRunValidation.objects.filter(
        id=validation_assignment_id).select_related(
        'sr_id').first()

    file_path = os.path.join(
        validation_assignment.sr_id.sim_id.results_dir,
        validation_assignment.sr_id.results_file_path,
        metric.file_path,
        '' if metric.type == 'dynamic_graph' and metric_data_model != 'extraction_points' else file_name
    )

    if metric.type == 'dynamic_graph' and metric_data_model != 'extraction_points':
        if metric_data_model == 'hydro_compartments':
            archive_path = settings.TMP_ARCHIVES_PATH
            os.makedirs(archive_path, exist_ok=True)
            archive_file_path = os.path.join(archive_path, f'{metric.name}_hydro_compartments.zip')
            #  Check to see if the file already exists, minor optimization
            if not os.path.exists(archive_file_path):
                response = zipfile.ZipFile(archive_file_path, 'w')
                for file in (file for file in sorted(os.listdir(file_path)) if
                             re.search(metric.file_name_regex, file)):
                    response.write(os.path.join(file_path, file), file)
                response.close()
            response = open(archive_file_path, 'rb')
        elif metric_data_model == 'daily_hydro_compartments':
            for file in (file for file in sorted(os.listdir(file_path)) if re.search(metric.file_name_regex, file)):
                response = open(os.path.join(file_path, file), 'rb')
    else:
        response = open(file_path, 'rb')

    try:
        return FileResponse(response, as_attachment=True)
    except:
        return HttpResponse(status=500)


def get_static_metric(request):
    file_name = request.GET.get('file_name')
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    validation_assignment = models.SimulationRunValidation.objects.filter(
        id=validation_assignment_id).select_related(
        'sr_id').first()

    file_path = os.path.join(
        validation_assignment.sr_id.sim_id.results_dir,
        validation_assignment.sr_id.results_file_path,
        metric.file_path,
        file_name
    )

    try:
        with open(file_path, "rb") as f:
            return HttpResponse(f.read(), content_type="image/jpeg")
    except:
        return HttpResponse(status=500)


def get_dynamic_graph_metric(request):
    file_name = request.GET.get('file_name')
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()
    metric_data_model = metric.graph_config['misc']['data_model']

    validation_assignment = models.SimulationRunValidation.objects.filter(
        id=validation_assignment_id).select_related('sr_id').first()

    file_path = os.path.join(
        validation_assignment.sr_id.sim_id.results_dir,
        validation_assignment.sr_id.results_file_path,
        metric.file_path,
        file_name if metric_data_model == 'extraction_points' else ''
    )

    json_from_csv = {'fwa': [], 'fwoa': []} if metric.graph_config.get('misc', {}).get('comparison_type',
                                                                                       False) == 'fwa_fwoa' else []

    scenario = validation_assignment.sr_id.name.split('_')[0]

    if metric_data_model == 'extraction_points':
        with open(file_path, "r") as f:
            dict_reader = csv.DictReader(f)
            if metric.graph_config.get('misc', {}).get('comparison_type', False) == 'fwa_fwoa':
                fwoa_model_group = 'G500'
                if validation_assignment.sr_id.sim_id.name == 'ICM IP2':
                    fwoa_model_group = 'G512'
                elif validation_assignment.sr_id.sim_id.name == 'ICM FWMP':
                    fwoa_model_group = 'G514'

                json_from_csv['fwa'] = list(dict_reader)
                # In this case, we need to load data from another file as well
                fwoa_file_path = os.path.join(
                    validation_assignment.sr_id.sim_id.results_dir,
                    scenario,
                    fwoa_model_group,
                    metric.file_path,
                    file_name.replace(validation_assignment.sr_id.name.split('_')[1], fwoa_model_group)
                )
                with open(fwoa_file_path, 'r') as fwoa_f:
                    fwoa_dict_reader = csv.DictReader(fwoa_f)
                    json_from_csv['fwoa'] = list(fwoa_dict_reader)
            else:
                # Otherwise, just load the data from this file
                json_from_csv = list(dict_reader)
    else:
        for file in (file for file in sorted(os.listdir(file_path)) if re.search(metric.file_name_regex, file)):
            with open(os.path.join(file_path, file), 'r') as f:
                if metric_data_model == 'hydro_compartments':
                    csv_reader = list(csv.DictReader(f))
                    # This iterates over yearly files, and grabs the column that is being viewed
                    if metric.graph_config.get('misc', {}).get('comparison_type', False) == 'fwa_fwoa':
                        json_from_csv['fwa'].append(csv_reader[int(file_name) - 1])
                        fwoa_model_group = 'G500'
                        if validation_assignment.sr_id.sim_id.name == 'ICM IP2':
                            fwoa_model_group = 'G512'
                        elif validation_assignment.sr_id.sim_id.name == 'ICM FWMP':
                            fwoa_model_group = 'G514'

                        # file can be used here (rather than fwoa_file) because its just compartment_out_xxxx
                        fwoa_file_path = os.path.join(
                            validation_assignment.sr_id.sim_id.results_dir,
                            scenario,
                            fwoa_model_group,
                            metric.file_path,
                            file
                        )
                        with open(fwoa_file_path, 'r') as fwoa_f:
                            fwoa_csv_reader = list(csv.DictReader(fwoa_f))
                            json_from_csv['fwoa'].append(fwoa_csv_reader[int(file_name) - 1])
                    else:
                        json_from_csv.append(csv_reader[int(file_name) - 1])
                elif metric_data_model == 'daily_hydro_compartments':
                    # This iterates over the columns in a file, and grabs the column that is being viewed
                    result = None
                    if not cache.keys(f'{file}_{int(file_name) - 1}'):
                        csv_reader = pa.read_csv(f, header=None)
                        for col in csv_reader.columns:
                            # Set the columns in Redis so that subsequent loads are faster
                            cache.set(f'{file}_{col}', csv_reader[col])
                            if col == int(file_name) - 1:
                                result = csv_reader[col]

                    result = cache.get(f'{file}_{int(file_name) - 1}') if result is None else result

                    # We only want to get a set of years (if the year is not -1)
                    year = int(request.GET.get('year'))
                    first_day = (year - 1) * 365 if year > 0 else 0
                    last_day = year * 365 if year > 0 else len(result)

                    if metric.graph_config.get('misc', {}).get('comparison_type', False) == 'fwa_fwoa':
                        fwoa_model_group = 'G500'
                        if validation_assignment.sr_id.sim_id.name == 'ICM IP2':
                            fwoa_model_group = 'G512'
                        elif validation_assignment.sr_id.sim_id.name == 'ICM FWMP':
                            fwoa_model_group = 'G514'
                        fwoa_result = None
                        for row in result[first_day:last_day]:
                            json_from_csv['fwa'].append({'value': row})

                        fwoa_file = file.replace(validation_assignment.sr_id.name.split('_')[1], fwoa_model_group)

                        fwoa_file_path = os.path.join(
                            validation_assignment.sr_id.sim_id.results_dir,
                            scenario,
                            fwoa_model_group,
                            metric.file_path,
                            fwoa_file
                        )

                        with open(fwoa_file_path, 'r') as fwoa_f:
                            if not cache.keys(f'{fwoa_file}_{int(file_name) - 1}'):
                                csv_reader = pa.read_csv(fwoa_f, header=None)
                                for col in csv_reader.columns:
                                    # Set the columns in Redis so that subsequent loads are faster
                                    cache.set(f'{fwoa_file}_{col}', csv_reader[col])
                                    if col == int(file_name) - 1:
                                        fwoa_result = csv_reader[col]

                            fwoa_result = cache.get(
                                f'{fwoa_file}_{int(file_name) - 1}') if fwoa_result is None else fwoa_result
                            for row in fwoa_result[first_day:last_day]:
                                json_from_csv['fwoa'].append({'value': row})
                    else:
                        for row in result[first_day:last_day]:
                            json_from_csv.append({'value': row})

    return HttpResponse(json.dumps(json_from_csv))


def get_map_metric(request):
    file_name = request.GET.get('file_name')
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    validation_assignment = models.SimulationRunValidation.objects.filter(
        id=validation_assignment_id).select_related(
        'sr_id').first()

    file_path = os.path.join(
        validation_assignment.sr_id.sim_id.results_dir,
        validation_assignment.sr_id.results_file_path,
        metric.file_path,
        file_name
    )

    try:
        with open(file_path, "rb") as f:
            return HttpResponse(f.read(), content_type="image/png")
    except:
        return HttpResponse(status=500)


def widget_review_status(request):
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric_id = request.GET.get('metric_id')

    validation_assignment = models.SimulationRunValidation.objects.filter(id=validation_assignment_id).first()

    metric_comments = models.ValidationAssignmentComment.objects.filter(metric_id=metric_id,
                                                                        srv_id=validation_assignment)

    response = {
        'Reviewed': 0,
        'Flagged': 0,
        'Intuitive': 0,
        'Not Intuitive': 0,
        'Misc': 0
    }
    # Prep the comments for response
    for comment in metric_comments:
        response['Reviewed'] += 1
        if comment.is_flag:
            response['Flagged'] += 1
        elif comment.review_option == 'not-intuitive':
            response['Not Intuitive'] += 1
        elif comment.review_option is None:
            response['Misc'] += 1
        else:
            response['Intuitive'] += 1

    return HttpResponse(json.dumps(response))


def get_comments(request):
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric_id = request.GET.get('metric_id')
    metric_options = json.loads(request.GET.get('metric_options'))

    validation_assignment = models.SimulationRunValidation.objects.filter(id=validation_assignment_id).first()

    metric_comments = models.ValidationAssignmentComment.objects.filter(metric_id=metric_id,
                                                                        srv_id=validation_assignment,
                                                                        metric_options=metric_options)

    response = []
    # Prep the comments for response
    for comment in metric_comments:
        user_name = comment.user_id.username
        comment_dict = model_to_dict(comment)
        comment_dict['user_name'] = user_name
        response.append(comment_dict)

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


class ValidationItemOverview(View):
    def get(self, request, id):
        context = {}

        srv = models.SimulationRunValidation.objects.filter(id=id).select_related('sr_id')\
            .select_related('sub_id').select_related('vi_id').first()

        context['validation_item'] = srv

        context['assignments'] = models.ValidationAssignment.objects.filter(srv_id=srv).all()
        context['metrics'] = []

        # Get related metrics
        for validation_item_metric in models.ValidationItemMetrics.objects.filter(
                vi_id=srv.vi_id).select_related('metric_id'):
            context['metrics'].append(
                {'id': validation_item_metric.metric_id.id, 'name': validation_item_metric.metric_id.name})

        validation_item_assignment = models.ValidationAssignment.objects.filter(srv_id=srv, user_id=request.user).first()
        context['validation_item_assignment'] = validation_item_assignment

        context['edit_permission'] = validation_item_assignment or request.user.groups.filter(name="Admin").exists()

        context['is_submitted'] = validation_item_assignment.is_submitted if validation_item_assignment \
            else (
                request.user.groups.filter(name="Admin").exists() and
                models.ValidationAssignmentComment.objects.filter(srv_id=srv, is_submission=1, user_id=request.user).first()
            )

        template = loader.get_template('validation_item_overview.html')
        if srv.sr_id.sim_id.name == 'ICM':
            context['project_information'] = utils.model_group_get_related_projects(srv.sr_id.name[-3:])

        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemDataViewerView(View):
    def get(self, request, id):
        context = {}

        if len(request.GET) > 0:
            context['metric_id'] = request.GET.get('metric_id')
            context['metric_options'] = request.GET.get('metric_options')


        srv = models.SimulationRunValidation.objects.filter(id=id).select_related('sr_id')\
            .select_related('sub_id').select_related('vi_id').first()

        context['validation_item'] = srv

        context['metrics'] = []

        # Get related metrics
        for validation_item_metric in models.ValidationItemMetrics.objects.filter(
                vi_id=srv.vi_id).select_related('metric_id'):
            context['metrics'].append(
                {'id': validation_item_metric.metric_id.id, 'name': validation_item_metric.metric_id.name})

        validation_item_assignment = models.ValidationAssignment.objects.filter(srv_id=srv, user_id=request.user).first()
        context['validation_item_assignment'] = validation_item_assignment

        context['edit_permission'] = validation_item_assignment is not None

        template = loader.get_template('validation_item_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class AdminConsole(View):
    def get(self, request):
        context = {}
        template = loader.get_template('admin_console.html')

        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_id_list = []
        for session in active_sessions:
            data = session.get_decoded()
            user_id_list.append(data.get('_auth_user_id', None))
        # Query all logged in users based on id list
        context['users'] = User.objects.filter(id__in=user_id_list).all()

        return HttpResponse(template.render(context, request))

    post = get


class DictionariesListView(View):
    def get(self, request):
        context = {
            'metrics': models.Metric.objects.all(),
            'validation_items': models.ValidationItem.objects.all(),
            'subroutines': models.Subroutine.objects.all(),
            'simulations': models.Simulation.objects.all()
        }

        template = loader.get_template('dictionaries_list_view.html')

        return HttpResponse(template.render(context, request))

    post = get


class Home(View):
    def get(self, request):
        context = {}
        template = loader.get_template('home.html')
        return HttpResponse(template.render(context, request))

    post = get


class Resources(View):
    def get(self, request, path=None):
        filepath = settings.RESOURCES_FILE_PATH
        if path:
            decoded_path = path.replace('%2f', '/')
            return FileResponse(open(os.path.join(filepath, decoded_path), 'rb'), as_attachment=True)

        # get all of the files
        context = {'resources': {}}
        for root, dirs, files in os.walk(filepath):
            dir_name = root.replace(filepath, '')[1:] if filepath != root else 'Main Directory'
            pruned_root = root.replace(filepath, '')[1:] + '/' if filepath != root else ''
            if files:
                context['resources'][dir_name] = {}
                for file in files:
                    context['resources'][dir_name][(pruned_root + file).replace('/','%2f')] = file

        template = loader.get_template('resources.html')
        return HttpResponse(template.render(context, request))

    post = get


class Tasks(View):
    def get(self, request):
        context = {
            'open_tasks': [],
            'flagged_tasks': [],
            'pending_admin_review_tasks': []
        }

        template = loader.get_template('tasks.html')
        tasks = models.ValidationAssignment.objects.all().filter(user_id=request.user) \
            .select_related('srv_id__sr_id__sim_id').select_related('srv_id__sub_id').select_related('srv_id__vi_id')

        filters = models.ValidationAssignment.get_list_view_filters()
        utils.populate_filters(filters)

        if len(request.GET) > 0:
            utils.set_filter_values(filters, request)

        tasks = utils.filter_queryset(tasks, filters)

        context['filters'] = filters

        for task in tasks:
            # Should check to see whether there are any comment flags for the SRV
            flag_comments = models.ValidationAssignmentComment.objects.filter(srv_id=task.srv_id, is_flag=1).all()
            if not task.is_submitted and not task.srv_id.is_approved:
                context['open_tasks'].append(task)

        # Grab the pending admin review tasks
        if request.user.groups.filter(name="Admin").exists():
            # Grab unapproved SRVs
            unapproved_srvs = models.SimulationRunValidation.objects.filter(is_approved=0, is_flagged=0).all()
            for unapproved_srv in unapproved_srvs:
                # We need to grab all of the validation assignments that have been submitted,
                # and check whether they all have is_approved set
                submitted_tasks = models.ValidationAssignment.objects.all().filter(srv_id=unapproved_srv,
                                                                                   is_submitted=1).aggregate(
                    num_related=Count('id'), num_approved=Sum('is_approved'))
                if submitted_tasks['num_approved'] is not None \
                        and submitted_tasks['num_related'] != submitted_tasks['num_approved']:
                    context['pending_admin_review_tasks'].append(unapproved_srv)

        return HttpResponse(template.render(context, request))

    post = get
