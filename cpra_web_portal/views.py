import json
import os
import datetime

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.template import loader
from django.utils import timezone, dateformat
from django.views import View

from . import models


# These are miscellaneous views? They are really Metrics requests though
# so they could be merged under a "class Metric"
def get_metric(request):
    metric_id = request.GET.get('metric_id')
    validation_assignment_id = request.GET.get('validation_assignment_id')
    metric = models.Metric.objects.filter(id=metric_id).first()

    files = []

    # I also need to get all of the files listed under this metric
    validation_assignment = models.ValidationAssignment.objects.filter(id=validation_assignment_id) \
        .select_related('srv_id__sr_id').first()

    file_path = os.path.join(
        validation_assignment.srv_id.sr_id.sim_id.results_dir,
        validation_assignment.srv_id.sr_id.results_file_path,
        metric.file_path
    )

    for file in os.listdir(file_path):
        files.append(file)

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


# Individual Item Views (Edit and Review)
class MetricEditView(View):
    def get(self, request, id):
        context = {}
        template = loader.get_template('metric_edit_view.html')

        context['metric'] = models.Metric.objects.filter(id=id).first()

        return HttpResponse(template.render(context, request))

    post = get


class SimulationEditView(View):
    def get(self, request, id):
        context = {}
        template = loader.get_template('simulation_edit_view.html')

        context['simulation'] = models.Simulation.objects.filter(id=id).first()

        context['wf_simulation_subroutines'] = []

        for wf_simulation_subroutine in models.WFSimulationSubroutine.objects.filter(sim_id=id).all():
            for subroutine_id in models.WFSubroutineValidationItem.objects.filter(
                    list_id=wf_simulation_subroutine.sub_vi_list_id).select_related('sub_id').values(
                    'sub_id').distinct():
                context['wf_simulation_subroutines'].append(
                    models.Subroutine.objects.filter(id=subroutine_id['sub_id']).first())

        context['wf_assignments'] = models.WFAssignment.objects.filter(sim_id=id).select_related('user_id').all()

        return HttpResponse(template.render(context, request))

    post = get


class SubroutineEditView(View):
    def get(self, request, id):
        context = {}
        template = loader.get_template('subroutine_edit_view.html')

        context['subroutine'] = models.Subroutine.objects.filter(id=id).first()

        context['wf_subroutine_validation_items'] = models.WFSubroutineValidationItem.objects.filter(
            sub_id=id).select_related('vi_id').all()

        context['wf_assignments'] = models.WFAssignment.objects.filter(sub_id=id).select_related('user_id').all()

        return HttpResponse(template.render(context, request))

    post = get


class UserItemView(View):
    def get(self, request, id):
        context = {}
        template = loader.get_template('user_item_view.html')

        user = User.objects.filter(id=id).first()

        context['user'] = user

        context['recent_approved_tasks'] = models.ValidationAssignment.objects.filter(user_id=id).order_by(
            '-datetime_approved') \
                                               .select_related('user_id').select_related(
            'srv_id__sr_id').select_related('srv_id__sub_id').select_related('srv_id__vi_id')[:5]

        return HttpResponse(template.render(context, request))

    post = get


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
    def get(self, request, id):
        context = {}
        template = loader.get_template('validation_item_edit_view.html')

        context['validation_item'] = models.ValidationItem.objects.filter(id=id).first()

        context['validation_item_metrics'] = models.ValidationItemMetrics.objects.filter(vi_id=id).select_related(
            'metric_id').all()

        context['wf_assignments'] = models.WFAssignment.objects.filter(vi_id=id).select_related('user_id').all()

        return HttpResponse(template.render(context, request))

    post = get


class ValidationAssignment(View):
    def put(self, request, id, method):
        validation_item = models.ValidationAssignment.objects.get(pk=id)
        if method == 'approve':
            validation_item.is_approved = 1
            validation_item.datetime_approved = datetime.datetime.now()
        elif method == 'deny':
            validation_item.is_approved = -1
        else:
            return HttpResponse(status=500)

        validation_item.save()

        # TODO: Add something here that updates related items

        df = dateformat.DateFormat(validation_item.datetime_approved)
        response = {'datetime_approved': df.format('N j, Y, P')}

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
        context = {}
        template = loader.get_template('simulation_runs_list_view.html')
        sim_runs = models.SimulationRun.objects.all().select_related('sim_id')
        for sim_run in sim_runs:
            sim_run.simulation = sim_run.sim_id

        context['simulation_runs'] = sim_runs
        return HttpResponse(template.render(context, request))

    post = get


class SubroutinesListView(View):
    def get(self, request):
        simulation_run_id = request.GET.get('sr_id')
        context = {}

        subroutines = models.ValidationAssignment.objects.filter(user_id=request.user.id).select_related(
            'srv_id__sub_id')

        if simulation_run_id:
            subroutines = subroutines.filter(srv_id__sr_id=simulation_run_id)

        subroutines = list(subroutines.values('id', 'srv_id__sub_id').distinct())

        grouped_validation_assignments = []
        for subroutine in subroutines:
            validation_assignment = models.ValidationAssignment.objects.filter(id=subroutine['id']). \
                select_related('srv_id__sr_id').select_related('srv_id__sub_id').first()
            grouped_validation_assignments.append({
                'sr_id': validation_assignment.srv_id.sr_id,
                'sub_id': validation_assignment.srv_id.sub_id,
                'sim_id': validation_assignment.srv_id.sr_id.sim_id
            })

        context['grouped_validation_assignments'] = grouped_validation_assignments

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
        context = {}
        simulation_run_id = request.GET.get('sr_id')
        sub_id = request.GET.get('sub_id')

        validation_assignments = models.ValidationAssignment.objects.filter(user_id=request.user.id)

        if simulation_run_id:
            validation_assignments = validation_assignments.filter(srv_id__sr_id=simulation_run_id)

        if sub_id:
            validation_assignments = validation_assignments.filter(srv_id__sub_id=sub_id)

        context['validation_assignments'] = validation_assignments.select_related('srv_id__sr_id').select_related(
            'srv_id__sub_id').select_related('srv_id__vi_id').all()

        template = loader.get_template('validation_items_list_view.html')
        return HttpResponse(template.render(context, request))

    post = get
