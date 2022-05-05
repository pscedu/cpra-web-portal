from ajax_datatable.views import AjaxDatatableView
from cpra_web_portal import models
import json
from django.template import loader
from django.urls import reverse
import urllib


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
        {'name': 'project_information', 'title': 'Project'},
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

    def export_row(self, row, obj):
        self.customize_row(row, obj)

    def render_row_details(self, pk, request=None):
        model = self.model.objects.get(pk=pk)

        return loader.render_to_string('ajax_datatables/validation_assignment_comment_render_row_details.html', {
            'model': model,
            'request': request
        })


class ValidationAssignmentAjaxDatatableView(AjaxDatatableView):

    model = models.ValidationAssignment
    title = 'Tasks'
    initial_order = [["datetime_approved", "desc"], ]
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    search_values_separator = '+'
    show_column_filters = True

    column_defs = [
        {'name': 'id', 'visible': False, },
        {'name': 'link', 'title': 'Link','placeholder': True},
        {'name': 'simulation_run', 'title': 'Simulation Run', 'foreign_field': 'srv_id__sr_id__name'},
        {'name': 'subroutine', 'title': 'Subroutine', 'foreign_field': 'srv_id__sub_id__name'},
        {'name': 'validation_item', 'title': 'Validation Item', 'foreign_field': 'srv_id__vi_id__name'},
        {'name': 'user', 'title': 'User', 'foreign_field': 'user_id__username'},
        {'name': 'is_submitted', 'title': 'Submitted', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'is_approved', 'title': 'Approved', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'datetime_submitted', 'title': 'Time Submitted', 'visible': True},
        {'name': 'datetime_approved', 'title': 'Time Approved', 'visible': True},
    ]

    def customize_row(self, row, obj):
        row['link'] = f"""
            <a href="{reverse('validation_item_overview', args=[obj.srv_id_id])}">
               Go To
            </a>
        """
        row['is_submitted'] = 'Yes' if obj.is_submitted else 'No'
        row['is_approved'] = 'Yes' if obj.is_approved else 'No'

    def export_row(self, row, obj):
        row['link'] = f"{reverse('validation_item_overview', args=[obj.srv_id_id])}"
        row['is_submitted'] = 'Yes' if obj.is_submitted else 'No'
        row['is_approved'] = 'Yes' if obj.is_approved else 'No'


class CommentAjaxDatatableView(AjaxDatatableView):

    model = models.ValidationAssignmentComment
    title = 'Comments'
    initial_order = [["datetime_modified", "desc"], ]
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    search_values_separator = '+'
    show_column_filters = True

    column_defs = [
        {'name': 'id', 'visible': False, },
        {'name': 'link', 'title': 'Link', 'placeholder': True},
        {'name': 'model_group', 'title': 'Model Group', 'foreign_field': 'srv_id__sr_id__name'},
        {'name': 'subroutine', 'title': 'Subroutine', 'foreign_field': 'srv_id__sub_id__name'},
        {'name': 'validation_item', 'title': 'Validation Item', 'foreign_field': 'srv_id__vi_id__name'},
        {'name': 'comments', 'title': 'Comment', 'max_length': 25},
        {'name': 'user', 'title': 'User', 'foreign_field': 'user_id__username'},
        {'name': 'project_information', 'title': 'Project', 'max_length': 25},
        {'name': 'is_submission', 'title': 'Submission', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'is_approval', 'title': 'Approved', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'is_flag', 'title': 'Flag', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'is_review', 'title': 'Review', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'metric', 'title': 'Metric', 'foreign_field': 'metric_id__name'},
        {'name': 'metric_options', 'title': 'Datapoint Details', 'max_length': 25},
        {'name': 'datetime_modified', 'title': 'Last Modified', 'visible': True},
    ]

    def get_initial_queryset(self, request=None):
        if not getattr(request, 'REQUEST', None):
            request.REQUEST = request.GET if request.method=='GET' else request.POST

        queryset = self.model.objects.all()

        return queryset

    def customize_row(self, row, obj):
        row['metric_options'] = json.dumps(obj.metric_options) if obj.metric_options else ''
        # print(urlencode(row.get('metric_options')))
        if row['metric_options']:
            row['link'] = f"""
                <a href="{reverse('validation_item_view', args=[obj.srv_id_id])}?metric_id={obj.metric_id_id}&metric_options={urllib.parse.quote_plus(row['metric_options'])}">
                   Go To
                </a>
            """
        else:
            row['link'] = f"""
                <a href="{reverse('validation_item_overview', args=[obj.srv_id_id])}">
                   Go To
                </a>
            """
        row['is_submission'] = 'Yes' if obj.is_submission else 'No'
        row['is_approval'] = 'Yes' if obj.is_approval else 'No'
        row['is_flag'] = 'Yes' if obj.is_flag else 'No'
        row['is_review'] = 'Yes' if obj.is_review else 'No'

    def export_row(self, row, obj):
        row['metric_options'] = json.dumps(obj.metric_options) if obj.metric_options else ''
        # print(urlencode(row.get('metric_options')))
        if row['metric_options']:
            row['link'] = f"{reverse('validation_item_view', args=[obj.srv_id_id])}?metric_id={obj.metric_id_id}&metric_options={urllib.parse.quote_plus(row['metric_options'])}"
        else:
            row['link'] = f"{reverse('validation_item_overview', args=[obj.srv_id_id])}"
        row['is_submission'] = 'Yes' if obj.is_submission else 'No'
        row['is_approval'] = 'Yes' if obj.is_approval else 'No'
        row['is_flag'] = 'Yes' if obj.is_flag else 'No'
        row['is_review'] = 'Yes' if obj.is_review else 'No'


class MassApprovalAjaxDatatableView(AjaxDatatableView):

    model = models.SimulationRunValidation
    title = 'Mass Approval'
    initial_order = [["is_approved", "asc"], ]
    length_menu = [[10, 20, 50, 100, -1], [10, 20, 50, 100, 'all']]
    search_values_separator = '+'
    show_column_filters = True

    column_defs = [
        {'name': 'id', 'visible': False, },
        {'name': 'link', 'title': 'Link', 'placeholder': True},
        {'name': 'model_group', 'title': 'Model Group', 'foreign_field': 'sr_id__name'},
        {'name': 'subroutine', 'title': 'Subroutine', 'foreign_field': 'sub_id__name'},
        {'name': 'validation_item', 'title': 'Validation Item', 'foreign_field': 'vi_id__name'},
        {'name': 'is_approved', 'title': 'Approved', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'is_flagged', 'title': 'Flag', 'choices': ((1, 'Yes'), (0, 'No'))},
        {'name': 'datetime_approved', 'title': 'Datetime Approved', 'visible': True},
    ]

    def get_initial_queryset(self, request=None):
        if not getattr(request, 'REQUEST', None):
            request.REQUEST = request.GET if request.method=='GET' else request.POST

        queryset = self.model.objects.all()

        return queryset

    def customize_row(self, row, obj):
        row['link'] = f"""
            <a href="{reverse('validation_item_overview', args=[obj.id])}">
               Go To
            </a>
        """
        row['is_approved'] = 'Yes' if obj.is_approved else 'No'
        row['is_flagged'] = 'Yes' if obj.is_flagged else 'No'

    def export_row(self, row, obj):
        row['link'] = f"{reverse('validation_item_overview', args=[obj.id])}"
        row['is_approved'] = 'Yes' if obj.is_approved else 'No'
        row['is_flagged'] = 'Yes' if obj.is_flagged else 'No'