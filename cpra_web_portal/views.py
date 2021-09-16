import json
import os
import datetime
import csv

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.sessions.models import Session
from django.forms.models import model_to_dict
from django.http import HttpResponse, FileResponse
from django.template import loader
from django.utils import timezone
from django.views import View
from django.urls import reverse
from django.core.cache import cache
from django.db.models import Sum, Count
from django.db import connections
from django.core.serializers.json import DjangoJSONEncoder
import pandas as pa
import zipfile

from . import models, utils


# These are miscellaneous views? They are really Metrics requests though
# so they could be merged under a "class Metric"
def get_metric(request):
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    validation_assignment = models.SimulationRunValidation.objects.filter(id=validation_assignment_id).select_related('sr_id').first()

    file_path = os.path.join(
        validation_assignment.sr_id.sim_id.results_dir,
        validation_assignment.sr_id.results_file_path,
        metric.file_path
    )

    files = utils.get_metric_files(metric, file_path)

    response = {
        'metric': model_to_dict(metric),
        'files': files
    }

    if metric.type == 'dynamic_graph' and metric.graph_config.get('misc', {}).get('comparison_type', False):
        response['columns'] = utils.get_comparison_cols(metric, file_path)

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


def get_comments(request):
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric_id = request.GET.get('metric_id')
    metric_options = json.loads(request.GET.get('metric_options'))

    validation_assignment = models.SimulationRunValidation.objects.filter(id=validation_assignment_id).first()

    metric_comments = models.ValidationAssignmentComment.objects.filter(metric_id=metric_id, srv_id=validation_assignment, metric_options=metric_options)

    response = []
    # Prep the comments for response
    for comment in metric_comments:
        user_name = comment.user_id.username
        comment_dict = model_to_dict(comment)
        comment_dict['user_name'] = user_name
        response.append(comment_dict)

    return HttpResponse(json.dumps(response, cls=DjangoJSONEncoder))


def export_metric(request):
    response = None
    file_name = request.GET.get('file_name')
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()
    metric_data_model = metric.graph_config['misc']['data_model'] if metric.type == 'dynamic_graph' else ''

    validation_assignment = models.SimulationRunValidation.objects.filter(id=validation_assignment_id).select_related(
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
                for file in (file for file in sorted(os.listdir(file_path)) if metric.file_name_regex in file):
                    response.write(os.path.join(file_path, file), file)
                response.close()
            response = open(archive_file_path, 'rb')
        elif metric_data_model == 'daily_hydro_compartments':
            for file in (file for file in sorted(os.listdir(file_path)) if metric.file_name_regex in file):
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

    validation_assignment = models.SimulationRunValidation.objects.filter(id=validation_assignment_id).select_related(
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

    validation_assignment = models.SimulationRunValidation.objects.filter(id=validation_assignment_id).select_related('sr_id').first()

    file_path = os.path.join(
        validation_assignment.sr_id.sim_id.results_dir,
        validation_assignment.sr_id.results_file_path,
        metric.file_path,
        file_name if metric_data_model == 'extraction_points' else ''
    )

    json_from_csv = []

    if metric_data_model == 'extraction_points':
        with open(file_path, "r") as f:
            dict_reader = csv.DictReader(f)
            if metric.graph_config.get('misc', {}).get('comparison_type', False) == 'fwa_fwoa':
                json_from_csv = {'fwa': list(dict_reader)}
                # In this case, we need to load data from another file as well
                fwoa_file_path = os.path.join(
                    validation_assignment.sr_id.sim_id.results_dir,
                    validation_assignment.sr_id.name.split('_')[0],
                    'G500',
                    metric.file_path,
                    file_name.replace(validation_assignment.sr_id.name.split('_')[1], 'G500')
                )
                with open(fwoa_file_path, 'r') as fwoa_f:
                    fwoa_dict_reader = csv.DictReader(fwoa_f)
                    json_from_csv['fwoa'] = list(fwoa_dict_reader)
            else:
                # Otherwise, just load the data from this file
                json_from_csv = list(dict_reader)
    else:
        for file in (file for file in sorted(os.listdir(file_path)) if metric.file_name_regex in file):
            with open(os.path.join(file_path, file), 'r') as f:
                if metric_data_model == 'hydro_compartments':
                    # This iterates over yearly files, and grabs the column that is being viewed
                    csv_reader = list(csv.DictReader(f))
                    json_from_csv.append(csv_reader[int(file_name)-1])
                elif metric_data_model == 'daily_hydro_compartments':
                    # This iterates over the columns in a file, and grabs the column that is being viewed
                    result = None
                    if not cache.keys(f'{file}_{int(file_name)-1}'):
                        csv_reader = pa.read_csv(f, header=None)
                        for col in csv_reader.columns:
                            # Set the columns in Redis so that subsequent loads are faster
                            cache.set(f'{file}_{col}', csv_reader[col])
                            if col == int(file_name)-1:
                                result = csv_reader[col]

                    result = cache.get(f'{file}_{int(file_name)-1}') if result is None else result

                    # We only want to get a set of years (if the year is not -1)
                    year = int(request.GET.get('year'))
                    first_day = (year-1)*365 if year > 0 else 0
                    last_day = year*365 if year > 0 else len(result)

                    for row in result[first_day:last_day]:
                        json_from_csv.append({'value': row})

    return HttpResponse(json.dumps(json_from_csv))


def get_map_metric(request):
    file_name = request.GET.get('file_name')
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    validation_assignment = models.SimulationRunValidation.objects.filter(id=validation_assignment_id).select_related(
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

    metric_comments = models.ValidationAssignmentComment.objects.filter(metric_id=metric_id, srv_id=validation_assignment)

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


from ajax_datatable.views import AjaxDatatableView


class ValidationItemCommentAjaxDatatableView(AjaxDatatableView):

    model = models.ValidationAssignmentComment
    title = 'Comments'
    initial_order = [["datetime_modified", "desc"], ]
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    search_values_separator = '+'
    show_column_filters = True

    column_defs = [
        {'name': 'id', 'visible': False, },
        {'name': 'user', 'title': 'User', 'foreign_field': 'user_id__username'},
        {'name': 'is_submission', 'title': 'Submission', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'is_approval', 'title': 'Approved', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'is_flag', 'title': 'Flag', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'is_review', 'title': 'Review', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'metric', 'title': 'Metric', 'foreign_field': 'metric_id__name'},
        {'name': 'metric_options', 'title': 'Datapoint Details'},
        {'name': 'datetime_modified', 'title': 'Last Modified', 'visible': True},
    ]

    def get_initial_queryset(self, request=None):
        if not getattr(request, 'REQUEST', None):
            request.REQUEST = request.GET if request.method=='GET' else request.POST

        queryset = self.model.objects.all()

        if 'validation_item_id' in request.REQUEST:
            validation_item_id = int(request.REQUEST.get('validation_item_id'))
            queryset = queryset.filter(srv_id__id=validation_item_id)

        return queryset

    def customize_row(self, row, obj):
        row['metric_options'] = json.dumps(obj.metric_options) if obj.metric_options else ''
        row['is_submission'] = 'Yes' if obj.is_submission else 'No'
        row['is_approval'] = 'Yes' if obj.is_approval else 'No'
        row['is_flag'] = 'Yes' if obj.is_flag else 'No'
        row['is_review'] = 'Yes' if obj.is_review else 'No'

    def render_row_details(self, pk, request=None):
        model = self.model.objects.get(pk=pk)

        return loader.render_to_string('ajax_datatables/validation_assignment_comment_render_row_details.html', {
            'model': model,
            'request': request
        })


# Individual Item Views
class SimulationEditView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('simulation_edit_view.html')

        simulation = models.Simulation.objects.filter(id=id).first() if id is not None else models.Simulation()

        context['simulation'] = simulation

        context['wf_simulation_subroutines'] = []

        for wf_simulation_subroutine in models.WFSimulationSubroutine.objects.filter(
                sim_id=simulation.id).select_related('sub_id').order_by('step').all():
            context['wf_simulation_subroutines'].append(wf_simulation_subroutine)

        context['wf_assignments'] = models.WFAssignment.objects.filter(sim_id=simulation.id).select_related(
            'user_id').all()

        return HttpResponse(template.render(context, request))

    def post(self, request):
        body = json.loads(request.body)

        # Pop the related tables
        related_tables = {
            'WFSimulationSubroutine': body.pop('wf_simulation_subroutines'),
            'WFAssignment': body.pop('wf_assignments')
        }

        if body['id']:
            simulation = models.Simulation.objects.filter(id=body['id']).first()
            for attr, value in body.items():
                if attr != 'id':
                    setattr(simulation, attr, value)
        else:
            simulation = models.Simulation(**body)

        simulation.save()

        # Update related tables
        related_tables['parent_table'] = {'id_field': 'sim_id_id', 'id_value': simulation.id}
        utils.update_related_tables(related_tables)
        related_tables['parent_table'] = {'id_field': 'sr_id__sim_id_id', 'id_value': simulation.id}
        utils.create_tasks(related_tables)

        return HttpResponse(json.dumps({'url': reverse('simulation_edit_view', args=(simulation.id,))}))


class SubroutineEditView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('subroutine_edit_view.html')

        subroutine = models.Subroutine.objects.filter(id=id).first() if id is not None else models.Subroutine()

        context['subroutine'] = subroutine

        context['wf_subroutine_validation_items'] = models.WFSubroutineValidationItem.objects.filter(
            sub_id=subroutine.id).select_related('vi_id').all()

        context['wf_assignments'] = models.WFAssignment.objects.filter(sub_id=subroutine.id).select_related(
            'user_id').all()

        return HttpResponse(template.render(context, request))

    def post(self, request):
        body = json.loads(request.body)

        # Pop the related tables
        related_tables = {
            'WFSubroutineValidationItem': body.pop('wf_subroutine_validation_items'),
            'WFAssignment': body.pop('wf_assignments')
        }

        if body['id']:
            subroutine = models.Subroutine.objects.filter(id=body['id']).first()
            for attr, value in body.items():
                if attr != 'id':
                    setattr(subroutine, attr, value)
        else:
            subroutine = models.Subroutine(**body)

        subroutine.save()

        # Update related tables
        related_tables['parent_table'] = {'id_field': 'sub_id_id', 'id_value': subroutine.id}
        utils.update_related_tables(related_tables)
        related_tables['parent_table'] = {'id_field': 'sub_id_id', 'id_value': subroutine.id}
        utils.create_tasks(related_tables)

        return HttpResponse(json.dumps({'url': reverse('subroutine_edit_view', args=(subroutine.id,))}))


class UserView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('user_item_view.html')

        context['user_model'] = User.objects.filter(id=id).first() if id is not None else User()

        context['recent_submitted_tasks'] = models.ValidationAssignment.objects.filter(user_id=id).order_by(
            '-datetime_submitted') \
                                               .select_related('user_id').select_related(
            'srv_id__sr_id').select_related('srv_id__sub_id').select_related('srv_id__vi_id')[:5]

        return HttpResponse(template.render(context, request))

    def post(self, request):
        body = json.loads(request.body)

        group = body.pop('group')

        if 'id' in body:
            user = User.objects.filter(id=body['id']).first()
            for attr, value in body.items():
                if attr != 'id':
                    setattr(user, attr, value)
        else:
            user = User(**body)
            pw = User.objects.make_random_password()
            user.set_password(pw)

            user.email_user(
                'Welcome to the CPRA QA/QC Portal',
                "Hello " + user.username + ",\n\nYou have been added to the CPRA Web Portal."
                                           "\n\nPlease visit the following URL to setup your password: " + request.build_absolute_uri(
                    reverse('password_reset')) +
                "\n\nHappy QA/QCing!"
            )

        user.save()

        group_to_add = Group.objects.get(name=group)
        group_to_add.user_set.add(user)

        return HttpResponse(json.dumps({'url': reverse('user_edit_view', args=(user.id,))}))


class TeamView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('team_edit_view.html')

        team = models.Team.objects.filter(
            id=id).first() if id is not None else models.Team()

        context['team'] = team

        context['user_teams'] = models.UserTeam.objects.filter(team_id=team).select_related(
            'user_id').all()

        return HttpResponse(template.render(context, request))

    def post(self, request):
        body = json.loads(request.body)

        # Pop the related tables
        related_tables = {
            'UserTeam': body.pop('user_team'),
        }

        if body['id']:
            team = models.Team.objects.filter(id=body['id']).first()
            for attr, value in body.items():
                if attr != 'id':
                    setattr(team, attr, value)
        else:
            team = models.Team(**body)

        team.save()

        # Update related tables
        related_tables['parent_table'] = {'id_field': 'team_id_id', 'id_value': team.id}
        utils.update_related_tables(related_tables)
        related_tables['parent_table'] = {'id_field': 'team_id_id', 'id_value': team.id}
        utils.create_tasks(related_tables)

        return HttpResponse(json.dumps({'url': reverse('team_edit_view', args=(team.id,))}))


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
            with connections['mp23'].cursor() as cursor:
                model_group = srv.sr_id.name[-3:]
                cursor.execute('SELECT md."ModelGroup", '
                               'md."ModelImplementation", '
                               'pm."DisplayID", '
                               'pm."LegacyProjectNumber", '
                               'pm."TypeCode", '
                               'pm."ProjectName", '
                               'pm."Description", '
                               'ed."Ecoregion", '
                               'epa."ExtractionPoint", '
                               'epa."Distance_m" '
                               'FROM pdd."ModelDefinition" as md '
                               'JOIN pct."ProjectMetadata" as pm ON md."ProjectID" = pm."ProjectID" '
                               'JOIN icm."ecoregion_definition" as ed ON md."ProjectID" = ed."ProjectID" '
                               'JOIN pdd."ExtractionPointDefinition" as epd ON ed."Ecoregion" = epd."Ecoregion" '
                               'JOIN pdd."ExtractionPointAssignment" as epa '
                               '    ON epd."ExtractionPoint" = epa."ExtractionPoint"  '
                               '    AND pm."ProjectID" = epa."ProjectID" '
                               'WHERE md."ModelGroup" = %s', [model_group])
                project_information = {}
                rows = cursor.fetchall()

                for row in rows:
                    if row[3] in project_information:
                        project_information[row[3]]['ExtractionPoints'].append(
                            {
                                'Ecoregion': row[7],
                                'ExtractionPoint': row[8],
                                'Distance_m': row[9]
                            }
                        )
                    else:
                        project_information[row[3]] = {
                            'ModelGroup': row[0],
                            'ModelImplementation': row[1],
                            'DisplayID': row[2],
                            'LegacyProjectNumber': row[3],
                            'TypeCode': row[4],
                            'ProjectName': row[5],
                            'Description': row[6],
                            'ExtractionPoints': [
                                {
                                    'Ecoregion': row[7],
                                    'ExtractionPoint': row[8],
                                    'Distance_m': row[9]
                                }
                            ]
                        }

                context['project_information'] = project_information


        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemView(View):
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


class ValidationItemEditView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('validation_item_edit_view.html')

        validation_item = models.ValidationItem.objects.filter(
            id=id).first() if id is not None else models.ValidationItem()

        context['validation_item'] = validation_item

        context['validation_item_metrics'] = models.ValidationItemMetrics.objects.filter(
            vi_id=validation_item.id).select_related(
            'metric_id').all()

        context['wf_assignments'] = models.WFAssignment.objects.filter(vi_id=validation_item.id).select_related(
            'user_id').all()

        return HttpResponse(template.render(context, request))

    def post(self, request):
        body = json.loads(request.body)

        # Pop the related tables
        related_tables = {
            'ValidationItemMetrics': body.pop('validation_item_metrics'),
            'WFAssignment': body.pop('wf_assignments')
        }

        if body['id']:
            validation_item = models.ValidationItem.objects.filter(id=body['id']).first()
            for attr, value in body.items():
                if attr != 'id':
                    setattr(validation_item, attr, value)
        else:
            validation_item = models.ValidationItem(**body)

        validation_item.save()

        # Update related tables
        related_tables['parent_table'] = {'id_field': 'vi_id_id', 'id_value': validation_item.id}
        utils.update_related_tables(related_tables)
        related_tables['parent_table'] = {'id_field': 'vi_id_id', 'id_value': validation_item.id}
        utils.create_tasks(related_tables)

        return HttpResponse(json.dumps({'url': reverse('validation_item_edit_view', args=(validation_item.id,))}))


class ValidationAssignment(View):
    def put(self, request, id, method):
        response = {}

        user = request.user
        srv = models.SimulationRunValidation.objects.get(pk=id)
        validation_assignment = models.ValidationAssignment.objects.filter(srv_id=srv, user_id=user).first()

        body = json.loads(request.body) if request.body else {}
        is_override = body.get('is_override', False)

        if validation_assignment:
            if method == 'submit':
                validation_assignment.is_submitted = 1
                validation_assignment.datetime_submitted = datetime.datetime.now()
                validation_assignment.is_approved = body['is_approved']
                validation_assignment.datetime_approved = datetime.datetime.now() if body['is_approved'] else None
            elif method == 'remove_submission':
                validation_assignment.is_submitted = 0
                validation_assignment.is_approved = 0
                validation_assignment.datetime_approved = None
                validation_assignment.datetime_submitted = None

            validation_assignment.save()

        if method == 'remove_submission':
            comment = models.ValidationAssignmentComment.objects.get(srv_id=srv, user_id=request.user, is_submission=1)
            comment.delete()

        if user.groups.filter(name="Admin").exists():
            if method == 'submit' and is_override:
                srv.is_approved = body['is_approved']
                srv.is_flagged = not body['is_approved']
                srv.datetime_approved = datetime.datetime.now() if body['is_approved'] else None
            elif method == 'remove_submission':
                srv.is_approved = 0
                # We need to remove the approval here, since it will not go through in the update_approval routine
                srv.sr_id.is_approved = 0
                srv.is_flagged = 0
                srv.datetime_approved = None
            srv.save()

        utils.update_approval(srv)

        return HttpResponse(json.dumps(response))


class ValidationAssignmentComment(View):
    def post(self, request):
        body = json.loads(request.body)

        validation_assignment = models.SimulationRunValidation.objects.get(pk=body['validation_assignment_id'])

        validation_assignment_comment_data = {
            'srv_id': validation_assignment,
            'user_id': request.user,
            'comments': body['comments'],
            'is_flag': body.get('is_flag', 0),
            'is_submission': body.get('is_submission', 0),
            'is_approval': body.get('is_approval', 0),
            'is_review': body.get('is_review', 0),
            'review_option': body.get('review_option', None),
            'metric_id_id': body.get('metric_id', None),
            'metric_options': body.get('metric_options', None),
            'datetime_modified': datetime.datetime.now()
        }

        # For review comments, we should update an existing review comment if it exists.
        if validation_assignment_comment_data['is_review']:
            validation_assignment_comment = models.ValidationAssignmentComment.objects.filter(
                srv_id=validation_assignment_comment_data['srv_id'],
                metric_id_id=validation_assignment_comment_data['metric_id_id'],
                metric_options=validation_assignment_comment_data['metric_options'],
                user_id=validation_assignment_comment_data['user_id'],
                is_review=1).first()
            if validation_assignment_comment:
                validation_assignment_comment_data['id'] = validation_assignment_comment.id

        validation_assignment_comment = models.ValidationAssignmentComment(**validation_assignment_comment_data)
        validation_assignment_comment.save()

        # Need to return a template with the approval/denial details.
        return HttpResponse(json.dumps(model_to_dict(validation_assignment_comment), cls=DjangoJSONEncoder))

    def delete(self, request, id):
        validation_assignment_comment = models.ValidationAssignmentComment.objects.get(pk=id)
        if validation_assignment_comment and not(validation_assignment_comment.is_flag
                                                 or validation_assignment_comment.is_submission
                                                 or validation_assignment_comment.is_review):
            validation_assignment_comment.delete()
        return HttpResponse(status=200)


class Metric(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('metric_edit_view.html')
        context['metric'] = models.Metric.objects.filter(id=id).first() if id is not None else models.Metric()

        return HttpResponse(template.render(context, request))

    def post(self, request):
        body = json.loads(request.body)

        if 'id' in body:
            metric = models.Metric.objects.filter(id=body['id']).first()
            for attr, value in body.items():
                if attr != 'id':
                    setattr(metric, attr, value)
        else:
            metric = models.Metric(**body)

        metric.save()

        return HttpResponse(json.dumps({'url': reverse('metric_edit_view', args=(metric.id,))}))


# Strictly HTML views (collection of multiple items)
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

        context['recent_submitted_tasks'] = models.ValidationAssignment.objects.order_by('-datetime_submitted') \
                                               .select_related('user_id').select_related(
            'srv_id__sr_id').select_related('srv_id__sub_id').select_related('srv_id__vi_id')[:5]

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


# List Views of items
class SimulationRunsListView(View):
    def get(self, request):
        template = loader.get_template('simulation_runs_list_view.html')
        sim_runs = models.SimulationRun.objects.all().select_related('sim_id')

        filters = models.SimulationRun.get_list_view_filters()

        utils.populate_filters(filters)

        if len(request.GET) > 0:
            utils.set_filter_values(filters, request)

        sim_runs = utils.filter_queryset(sim_runs, filters)

        context = {
            'filters': filters,
            'simulation_runs': sim_runs
        }
        return HttpResponse(template.render(context, request))

    post = get


class SubroutinesListView(View):
    def get(self, request):
        validation_assignments = models.SimulationRunValidation.objects.select_related('sr_id').select_related('sub_id').all()

        filters = models.Subroutine.get_list_view_filters()
        utils.populate_filters(filters)
        if len(request.GET) > 0:
            utils.set_filter_values(filters, request)

        validation_assignments = utils.filter_queryset(validation_assignments, filters)

        subroutines = []
        grouped_validation_assignments = []
        for validation_assignment in validation_assignments:
            sub_id_sr_id_combo = validation_assignment.sr_id.name + validation_assignment.sub_id.name
            if sub_id_sr_id_combo not in subroutines:
                grouped_validation_assignments.append({
                    'sr_id': validation_assignment.sr_id,
                    'sub_id': validation_assignment.sub_id,
                    'sim_id': validation_assignment.sr_id.sim_id
                })
                subroutines.append(sub_id_sr_id_combo)

        context = {
            'grouped_validation_assignments': grouped_validation_assignments,
            'filters': filters
        }

        template = loader.get_template('subroutines_list_view.html')
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


class UsersListView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('users_list_view.html')

        users = User.objects.all()

        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_id_list = []
        for session in active_sessions:
            data = session.get_decoded()
            user_id_list.append(data.get('_auth_user_id', None))

        for user in users:
            user.is_logged_in = str(user.id) in user_id_list

        context['users'] = users
        context['teams'] = models.Team.objects.all()

        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemsListView(View):
    def get(self, request):
        validation_assignments = models.SimulationRunValidation.objects.all()

        filters = models.SimulationRunValidation.get_list_view_filters()
        utils.populate_filters(filters)
        if len(request.GET) > 0:
            utils.set_filter_values(filters, request)

        validation_assignments = utils.filter_queryset(validation_assignments, filters).select_related('sr_id').select_related(
                'sub_id').select_related('vi_id').all()

        for validation_assignment in validation_assignments:
            stats = models.ValidationAssignment.objects.filter(srv_id=validation_assignment).aggregate(
                num_related=Count('id'), num_approved=Sum('is_approved'), num_submitted=Sum('is_submitted'))
            validation_assignment.stats = stats

        context = {
            'validation_assignments': validation_assignments,
            'filters': filters
        }

        template = loader.get_template('validation_items_list_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemModal(View):
    def get(self, request, type):
        context = {}
        if type == 'wf_assignment':
            context['users'] = User.objects.all()
            context['teams'] = models.Team.objects.all()
            template = loader.get_template('modals/wf_assignment.html')
        elif type == 'validation_item_metrics':
            context['metrics'] = models.Metric.objects.all()
            template = loader.get_template('modals/validation_item_metrics.html')

        return HttpResponse(template.render(context, request))


class SubroutineModal(View):
    def get(self, request, type):
        context = {}
        if type == 'wf_assignment':
            context['users'] = User.objects.all()
            context['teams'] = models.Team.objects.all()
            template = loader.get_template('modals/wf_assignment.html')
        elif type == 'wf_subroutine_validation_items':
            context['validation_items'] = models.ValidationItem.objects.all()
            template = loader.get_template('modals/wf_subroutine_validation_items.html')

        return HttpResponse(template.render(context, request))


class SimulationModal(View):
    def get(self, request, type):
        context = {}
        if type == 'wf_assignment':
            context['users'] = User.objects.all()
            context['teams'] = models.Team.objects.all()
            template = loader.get_template('modals/wf_assignment.html')
        elif type == 'wf_simulation_subroutines':
            context['subroutines'] = models.Subroutine.objects.all()
            template = loader.get_template('modals/wf_simulation_subroutines.html')

        return HttpResponse(template.render(context, request))


class CommentModal(View):
    def get(self, request, type, id=None):
        context = {}
        srv_id = request.GET.get('validation_assignment_id')
        if type == 'misc':
            context['comment'] = models.ValidationAssignmentComment.objects.get(pk=id) if id else None
            template = loader.get_template('modals/misc_comment.html')
        elif type == 'submission':
            template = loader.get_template('modals/submit_comment.html')
            # Check for whether it has an assignment
            validation_assignment = models.ValidationAssignment.objects.filter(srv_id=srv_id,
                                                                               user_id=request.user).first()
            context['is_not_assigned'] = validation_assignment is None

        elif type == 'review':
            metric_id = request.GET.get('metric_id')
            metric_options = json.loads(request.GET.get('metric_options', '{}'))
            # Check to see if a review of this output item already exists. If so, grab it.
            srv = models.SimulationRunValidation.objects.filter(id=srv_id).first()
            comment = models.ValidationAssignmentComment.objects.filter(metric_id=metric_id,
                                                                        srv_id=srv,
                                                                        metric_options=metric_options,
                                                                        is_review=1,
                                                                        user_id=request.user).first()
            context['comment'] = comment
            template = loader.get_template('modals/review_comment.html')

        return HttpResponse(template.render(context, request))


class TeamModal(View):
    def get(self, request, type):
        context = {}
        if type == 'user_team':
            context['users'] = User.objects.all()
            template = loader.get_template('modals/user_team.html')

        return HttpResponse(template.render(context, request))
