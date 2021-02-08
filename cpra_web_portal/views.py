from django.http import HttpResponse
from django.template import loader
from django.views import View

from . import models
# Create your views here.


class Home(View):
    def get(self, request):
        context = {}
        template = loader.get_template('home.html')
        return HttpResponse(template.render(context, request))

    post = get


class MetricEditView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('metric_edit_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class SubroutineEditView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('subroutine_edit_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemEditView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('validation_item_edit_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class SimulationEditView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('simulation_edit_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class AdminConsole(View):
    def get(self, request):
        context = {}
        template = loader.get_template('admin_console.html')
        return HttpResponse(template.render(context, request))

    post = get


class DictionariesListView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('dictionaries_list_view.html')
        return HttpResponse(template.render(context, request))

    post = get


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

        subroutines = models.ValidationAssignment.objects

        if simulation_run_id:
            subroutines = subroutines.filter(sr_id=simulation_run_id)

        subroutines = list(subroutines.values('sub_id').distinct())

        context['subroutines'] = subroutines

        template = loader.get_template('subroutines_list_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class Tasks(View):
    def get(self, request):
        context = {}
        template = loader.get_template('tasks.html')
        return HttpResponse(template.render(context, request))

    post = get


class UserItemView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('user_item_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class UsersListView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('users_list_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemView(View):
    def get(self, request, id):
        context = {}

        validation_item = models.ValidationAssignment.objects.filter(id=id).select_related('sr_id__sim_id')\
            .select_related('sub_id').select_related('vi_id').select_related('user_id').first()

        validation_item.validation_item_metrics = validation_item.vi_id.validationitemmetrics_set.all()

        context['validation_item'] = validation_item

        # We also need to get all of the validation assignments that have the same sr_id,
        # sub_id, and vi_id (as this is how the comments and approvals would be tracked)

        related_validation_items = models.ValidationAssignment.objects.filter(
            sr_id=validation_item.sr_id, sub_id=validation_item.sub_id, vi_id=validation_item.vi_id
        ).select_related('user_id').all()

        context['comments'] = []
        context['approvals'] = []

        for rvi in related_validation_items:
            for comment in rvi.validationassignmentcomment_set.all():
                context['comments'].append({'user': rvi.user_id, 'comment': comment.comments})
            if rvi.is_approved:
                context['approvals'].append({'user': rvi.user_id, 'datetime_approved': rvi.datetime_approved})

        template = loader.get_template('validation_item_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemsListView(View):
    def get(self, request):
        context = {}
        simulation_run_id = request.GET.get('sr_id')
        sub_id = request.GET.get('sub_id')

        validation_assignments = models.ValidationAssignment.objects

        if simulation_run_id:
            validation_assignments = validation_assignments.filter(sr_id=simulation_run_id)

        if sub_id:
            validation_assignments = validation_assignments.filter(sub_id=sub_id)

        context['validation_assignments'] = validation_assignments.select_related('sr_id__sim_id').select_related('sub_id').select_related('vi_id').all()

        template = loader.get_template('validation_items_list_view.html')
        return HttpResponse(template.render(context, request))

    post = get

