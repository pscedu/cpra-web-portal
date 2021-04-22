from django.contrib import admin

from . import models

admin.site.register(model_or_iterable=models.Simulation)
admin.site.register(model_or_iterable=models.Subroutine)
admin.site.register(model_or_iterable=models.ValidationItem)
admin.site.register(model_or_iterable=models.WFSubroutineValidationItem)
admin.site.register(model_or_iterable=models.WFSimulationSubroutine)
admin.site.register(model_or_iterable=models.WFAssignment)
admin.site.register(model_or_iterable=models.SimulationRun)
admin.site.register(model_or_iterable=models.ValidationAssignment)
admin.site.register(model_or_iterable=models.ValidationAssignmentComment)
admin.site.register(model_or_iterable=models.ValidationItemMetrics)
admin.site.register(model_or_iterable=models.Metric)
admin.site.register(model_or_iterable=models.SimulationRunValidation)
admin.site.register(model_or_iterable=models.Team)
admin.site.register(model_or_iterable=models.UserTeam)
admin.site.site_header = "CPRA Portal"