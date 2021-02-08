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

        validation_item = models.ValidationAssignment.objects.filter(id=id).first()

        context['validation_item'] = validation_item

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

        validation_assignments = validation_assignments.select_related('sr_id__sim_id').select_related('sub_id').select_related('vi_id').all()

        for validation_assignment in validation_assignments:
            validation_assignment.simulation_run = validation_assignment.sr_id
            validation_assignment.subroutine = validation_assignment.sub_id
            validation_assignment.simulation = validation_assignment.simulation_run.sim_id

        context['validation_assignments'] = validation_assignments

        template = loader.get_template('validation_items_list_view.html')
        return HttpResponse(template.render(context, request))

    post = get

