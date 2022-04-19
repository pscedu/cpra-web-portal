import json
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.template import loader
from django.views import View

from cpra_web_portal import models, utils


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
        srv = models.SimulationRunValidation.objects.filter(id=srv_id).first()
        if srv.sr_id.sim_id.name == 'ICM':
            context['project_information'] = utils.model_group_get_related_projects(srv.sr_id.name[-3:])
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