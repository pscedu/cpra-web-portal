from django.http import HttpResponse
from django.template import loader
from django.views import View
from cpra_web_portal import models


class TasksReportView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('reports/tasks_report_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class CommentsReportView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('reports/comments_report_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class MassApprovalReportView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('reports/mass_approval_report_view.html')
        return HttpResponse(template.render(context, request))

    post = get


class CustomExtractionPointReportView(View):
    def get(self, request):
        context = {}
        template = loader.get_template('reports/custom_extraction_point_report_view.html')

        context['srs'] = models.SimulationRun.objects.filter(sim_id__name__in=['ICM', 'ICM FWOA', 'ICM FWIP1',
                                                                               'ICM IP2', 'ICM FWOCPP']).all()

        return HttpResponse(template.render(context, request))

    post = get
