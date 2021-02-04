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
        return HttpResponse(template.render(context, request))

    post = get


class SubroutinesListView(View):
    def get(self, request):
        context = {}
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
    def get(self, request):
        context = {}
        template = loader.get_template('validation_item_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class ValidationItemsListView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('validation_items_list_view.html')
        return HttpResponse(template.render(context, request))

    post = get

