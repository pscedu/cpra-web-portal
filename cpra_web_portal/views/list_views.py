from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.template import loader
from django.utils import timezone
from django.views import View
from django.db.models import Sum, Count

from cpra_web_portal import models, utils


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
