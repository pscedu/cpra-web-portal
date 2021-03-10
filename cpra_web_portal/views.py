import json
import os
import datetime
import csv

from django.contrib.auth.models import User, Group
from django.contrib.sessions.models import Session
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.utils import timezone, dateformat
from django.views import View
from django.urls import reverse
from django.db.models import Sum, Count
from django.apps import apps

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
    for query_object in request.GET:
        if 'in' in query_object:
            value = request.GET.get(query_object).split(',')
        else:
            value = request.GET.get(query_object)
        filter_dict[query_object] = value

    return queryset.filter(**filter_dict)


def update_approval(validation_assignment):
    # Get all of the related validation assignments
    srv = models.SimulationRunValidation.objects.get(id=validation_assignment.srv_id_id)
    sim_run = models.SimulationRun.objects.get(id=srv.sr_id_id)

    # Get
    sum_count_related_vas = models.ValidationAssignment.objects.filter(srv_id=validation_assignment.srv_id).aggregate(
        num_related=Count('id'), num_approved=Sum('is_approved'))

    srv.is_approved = sum_count_related_vas['num_related'] == sum_count_related_vas['num_approved']
    srv.save()

    sum_count_related_srvs = models.SimulationRunValidation.objects.filter(sr_id=srv.sr_id).aggregate(
        num_related=Count('id'), num_approved=Sum('is_approved'))
    sim_run.is_approved = sum_count_related_srvs['num_related'] == sum_count_related_srvs['num_approved']
    sim_run.save()


# TODO: Move to utility.py
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


# These are miscellaneous views? They are really Metrics requests though
# so they could be merged under a "class Metric"
def get_metric(request):
    region_index = 12
    datapoint_index = 11

    # / MP2023_S04_G030_C000_U00_V00_SLA_O_10_10_W_lndtyp30.png

    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    if "map" in metric.type:
        # TODO: for maps, we just need the year since its coastwide
        parent_index = 0
        child_index = 9
    else:
        parent_index = 12
        child_index = 11

    # files will be structured as follows
    # files = {'region': {'point': 'filename'}}
    files = {}

    # I also need to get all of the files listed under this metric
    validation_assignment = models.ValidationAssignment.objects.filter(id=validation_assignment_id) \
        .select_related('srv_id__sr_id').first()

    file_path = os.path.join(
        validation_assignment.srv_id.sr_id.sim_id.results_dir,
        validation_assignment.srv_id.sr_id.results_file_path,
        metric.file_path
    )

    for file in os.listdir(file_path):
        if os.path.isdir(os.path.join(file_path, file)):
            continue

        file_name_list = file.split("_")
        parent = file_name_list[parent_index]
        if parent in files:
            files[parent][file_name_list[child_index]] = file
        else:
            files[parent] = {file_name_list[child_index]: file}

    response = {
        'metric': model_to_dict(metric),
        'files': files
    }

    return HttpResponse(json.dumps(response))


def get_static_metric(request):
    file_name = request.GET.get('file_name')
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    validation_assignment = models.ValidationAssignment.objects.filter(id=validation_assignment_id) \
        .select_related('srv_id__sr_id').first()

    file_path = os.path.join(
        validation_assignment.srv_id.sr_id.sim_id.results_dir,
        validation_assignment.srv_id.sr_id.results_file_path,
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

    validation_assignment = models.ValidationAssignment.objects.filter(id=validation_assignment_id) \
        .select_related('srv_id__sr_id').first()

    file_path = os.path.join(
        validation_assignment.srv_id.sr_id.sim_id.results_dir,
        validation_assignment.srv_id.sr_id.results_file_path,
        metric.file_path,
        file_name
    )


    try:
        with open(file_path, "r") as f:
            dict_reader = csv.DictReader(f)
            json_from_csv = json.dumps(list(dict_reader))
            return HttpResponse(json_from_csv)
    except:
        return HttpResponse(status=500)


def get_static_map(request):
    file_name = request.GET.get('file_name')
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    validation_assignment = models.ValidationAssignment.objects.filter(id=validation_assignment_id) \
        .select_related('srv_id__sr_id').first()

    file_path = os.path.join(
        validation_assignment.srv_id.sr_id.sim_id.results_dir,
        validation_assignment.srv_id.sr_id.results_file_path,
        metric.file_path,
        file_name
    )

    try:
        with open(file_path, "rb") as f:
            return HttpResponse(f.read(), content_type="image/jpeg")
    except:
        return HttpResponse(status=500)


# Individual Item Views
class SimulationEditView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('simulation_edit_view.html')

        simulation = models.Simulation.objects.filter(id=id).first() if id is not None else models.Simulation()

        context['simulation'] = simulation

        context['wf_simulation_subroutines'] = []

        for wf_simulation_subroutine in models.WFSimulationSubroutine.objects.filter(sim_id=simulation.id).select_related('sub_id').all():
            context['wf_simulation_subroutines'].append(wf_simulation_subroutine.sub_id)

        context['wf_assignments'] = models.WFAssignment.objects.filter(sim_id=simulation.id).select_related('user_id').all()

        return HttpResponse(template.render(context, request))

    def post(self, request):
        body = json.loads(request.body)
        print(body)

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
        update_related_tables(related_tables)

        return HttpResponse(json.dumps({'url': reverse('simulation_edit_view', args=(simulation.id,))}))


class SubroutineEditView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('subroutine_edit_view.html')

        subroutine = models.Subroutine.objects.filter(id=id).first() if id is not None else models.Subroutine()

        context['subroutine'] = subroutine

        context['wf_subroutine_validation_items'] = models.WFSubroutineValidationItem.objects.filter(
            sub_id=subroutine.id).select_related('vi_id').all()

        context['wf_assignments'] = models.WFAssignment.objects.filter(sub_id=subroutine.id).select_related('user_id').all()

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
        update_related_tables(related_tables)

        return HttpResponse(json.dumps({'url': reverse('subroutine_edit_view', args=(subroutine.id,))}))


class UserView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('user_item_view.html')

        context['user_model'] = User.objects.filter(id=id).first() if id is not None else User()

        context['recent_approved_tasks'] = models.ValidationAssignment.objects.filter(user_id=id).order_by(
            '-datetime_approved') \
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
            user.set_password(User.objects.make_random_password())
            # TODO: send email w/ password and how to login/change pw

        user.save()

        group_to_add = Group.objects.get(name=group)
        group_to_add.user_set.add(user)

        return HttpResponse(json.dumps({'url': reverse('user_edit_view', args=(user.id,))}))


class ValidationItemView(View):
    def get(self, request, id):
        context = {}

        validation_item = models.ValidationAssignment.objects.filter(id=id).select_related('srv_id__sr_id') \
            .select_related('srv_id__sub_id').select_related('srv_id__vi_id').first()

        context['validation_item'] = validation_item

        context['comments'] = []
        context['approvals'] = []
        context['metrics'] = []

        for comment in models.ValidationAssignmentComment.objects.filter(srv_id=validation_item.srv_id):
            context['comments'].append({'user': comment.user_id, 'comment': comment.comments})

        for approval in models.ValidationAssignment.objects.filter(srv_id=validation_item.srv_id, is_approved=1):
            context['approvals'].append({'user': approval.user_id, 'datetime_approved': approval.datetime_approved})

        # Get related metrics
        for validation_item_metric in models.ValidationItemMetrics.objects.filter(
                vi_id=validation_item.srv_id.vi_id).select_related('metric_id'):
            context['metrics'].append(
                {'id': validation_item_metric.metric_id.id, 'name': validation_item_metric.metric_id.name})

        template = loader.get_template('validation_item_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemEditView(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('validation_item_edit_view.html')

        validation_item = models.ValidationItem.objects.filter(id=id).first() if id is not None else models.ValidationItem()

        context['validation_item'] = validation_item

        context['validation_item_metrics'] = models.ValidationItemMetrics.objects.filter(vi_id=validation_item.id).select_related(
            'metric_id').all()

        context['wf_assignments'] = models.WFAssignment.objects.filter(vi_id=validation_item.id).select_related('user_id').all()

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
        update_related_tables(related_tables)

        return HttpResponse(json.dumps({'url': reverse('validation_item_edit_view', args=(validation_item.id,))}))


class ValidationAssignment(View):
    def put(self, request, id, method):
        response = {}
        validation_item = models.ValidationAssignment.objects.get(pk=id)
        srv = validation_item.srv_id
        if method == 'approve':
            validation_item.is_approved = 1
            validation_item.datetime_approved = datetime.datetime.now()
            df = dateformat.DateFormat(validation_item.datetime_approved)
            response['datetime_approved'] = df.format('N j, Y, P')
        elif method == 'remove_approval':
            validation_item.is_approved = 0
            validation_item.datetime_approved = None
        elif method == 'flag':
            srv.is_flagged = 1
            srv.save()
        elif method == 'unflag':
            srv.is_flagged = 0
            srv.save()
        else:
            return HttpResponse(status=500)

        validation_item.save()

        # TODO: Add something here that updates related items
        if method in ['approve', 'remove_approval']:
            update_approval(validation_item)

        return HttpResponse(json.dumps(response))


class ValidationAssignmentComment(View):
    def post(self, request):
        body = json.loads(request.body)

        validation_assignment = models.ValidationAssignment.objects.get(pk=body['validation_assignment_id'])

        validation_assignment_comment_data = {
            'srv_id': validation_assignment.srv_id,
            'user_id': request.user,
            'comments': body['comment']
        }

        validation_assignment_comment = models.ValidationAssignmentComment(**validation_assignment_comment_data)
        validation_assignment_comment.save()

        # Need to return a template with the approval/denial details.
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

        context['recent_approved_tasks'] = models.ValidationAssignment.objects.order_by('-datetime_approved') \
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


# List Views of items
class SimulationRunsListView(View):
    def get(self, request):
        template = loader.get_template('simulation_runs_list_view.html')
        sim_runs = models.SimulationRun.objects.filter(is_approved=False).select_related('sim_id')

        filters = models.SimulationRun.get_list_view_filters()

        populate_filters(filters)

        if len(request.GET) > 0:
            set_filter_values(filters, request)
            sim_runs = filter_queryset(sim_runs, request)

        context = {
            'filters': filters,
            'simulation_runs': sim_runs
        }
        return HttpResponse(template.render(context, request))

    post = get


class SubroutinesListView(View):
    def get(self, request):
        validation_assignments = models.ValidationAssignment.objects.filter(user_id=request.user.id, is_approved=False).select_related(
            'srv_id__sub_id')

        filters = models.Subroutine.get_list_view_filters()
        populate_filters(filters)
        if len(request.GET) > 0:
            set_filter_values(filters, request)
            validation_assignments = filter_queryset(validation_assignments, request)

        subroutines = []
        grouped_validation_assignments = []
        for validation_assignment in validation_assignments:
            sub_id_sr_id_combo = validation_assignment.srv_id.sr_id.name + validation_assignment.srv_id.sub_id.name
            if sub_id_sr_id_combo not in subroutines:
                grouped_validation_assignments.append({
                    'sr_id': validation_assignment.srv_id.sr_id,
                    'sub_id': validation_assignment.srv_id.sub_id,
                    'sim_id': validation_assignment.srv_id.sr_id.sim_id
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
            'flagged_tasks': []
        }
        template = loader.get_template('tasks.html')
        tasks = models.ValidationAssignment.objects.all().filter(user_id=request.user) \
            .select_related('srv_id__sr_id__sim_id').select_related('srv_id__sub_id').select_related('srv_id__vi_id')
        for task in tasks:
            # We need to get all of the Validation Assignments with the same sr_id, sub_id, and vi_id
            # check whether they've been flagged by other users
            if task.srv_id.is_flagged:
                context['flagged_tasks'].append(task)
            # If the user has not approved this task, then we need to add it to that list as well
            if not task.is_approved:
                context['open_tasks'].append(task)

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

        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemsListView(View):
    def get(self, request):
        validation_assignments = models.ValidationAssignment.objects.filter(user_id=request.user.id, is_approved=False)

        filters = models.ValidationItem.get_list_view_filters()
        populate_filters(filters)
        if len(request.GET) > 0:
            set_filter_values(filters, request)
            validation_assignments = filter_queryset(validation_assignments, request)

        context = {
            'validation_assignments': validation_assignments.select_related('srv_id__sr_id').select_related(
                                        'srv_id__sub_id').select_related('srv_id__vi_id').all(),
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
            template = loader.get_template('modals/wf_assignment.html')
        elif type == 'wf_simulation_subroutines':
            context['subroutines'] = models.Subroutine.objects.all()
            template = loader.get_template('modals/wf_simulation_subroutines.html')

        return HttpResponse(template.render(context, request))
