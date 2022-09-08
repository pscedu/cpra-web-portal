import json
import datetime
import urllib

from django.contrib.auth.models import User as user_model, Group
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.template import loader
from django.views import View
from django.urls import reverse
from django.core.serializers.json import DjangoJSONEncoder

from cpra_web_portal import models, utils


class User(View):
    def get(self, request, id=None):
        context = {}
        template = loader.get_template('user_item_view.html')

        context['user_model'] = user_model.objects.filter(id=id).first() if id is not None else user_model()

        context['recent_submitted_tasks'] = models.ValidationAssignment.objects.filter(user_id=id).order_by(
            '-datetime_submitted') \
                                               .select_related('user_id').select_related(
            'srv_id__sr_id').select_related('srv_id__sub_id').select_related('srv_id__vi_id')[:5]

        return HttpResponse(template.render(context, request))

    def post(self, request):
        body = json.loads(request.body)

        group = body.pop('group')

        if 'id' in body:
            user = user_model.objects.filter(id=body['id']).first()
            for attr, value in body.items():
                if attr != 'id':
                    setattr(user, attr, value)
        else:
            user = user_model(**body)
            pw = user_model.objects.make_random_password()
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


class Team(View):
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


class Simulation(View):
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


class Subroutine(View):
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


class ValidationItem(View):
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
            comment = models.ValidationAssignmentComment.objects.filter(srv_id=srv, user_id=request.user, is_submission=1).all()
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
            'project_information': body.get('project_information', ''),
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
        email_url = f"{request.get_host()}{reverse('validation_item_view', args=[validation_assignment.id])}?" \
                    f"metric_id={validation_assignment_comment_data['metric_id_id']}&metric_options=" \
                    f"{urllib.parse.quote_plus(json.dumps(validation_assignment_comment_data['metric_options']))}"

        for user_id in body.get('users_to_notify', {}):
            user = user_model.objects.get(pk=user_id)
            user.email_user(
                'New QA/QC Assignments',
                "Hello " + user.username + f",\n\n{request.user.username} would like you to review the following comment:"
                                           f"\n\n{body['comments']}"
                                           f"\n\nYou can review this at the following link {email_url}"
            )

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

        context['metric'].graph_config = json.dumps(context['metric'].graph_config)

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
