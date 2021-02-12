from django.db import models
from django.contrib.auth.models import User


class Simulation(models.Model):
    name = models.CharField(max_length=64, default="")
    results_dir = models.CharField(max_length=64, default="")


class Subroutine(models.Model):
    name = models.CharField(max_length=64, default="")


class ValidationItem(models.Model):
    name = models.CharField(max_length=64, default="")
    description = models.TextField(null=True)


class Metric(models.Model):
    name = models.CharField(max_length=64, default="")
    type = models.CharField(max_length=64, default="")
    file_path = models.CharField(max_length=64, default="")
    graph_config = models.JSONField()


class WFSubroutineValidationItem(models.Model):
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    list_id = models.IntegerField()


class WFSimulationSubroutine(models.Model):
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE)
    sub_vi_list_id = models.IntegerField()


class WFAssignment(models.Model):
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE)
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)


class SimulationRun(models.Model):
    name = models.CharField(max_length=64, default="")
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE)
    datetime_created = models.DateTimeField()
    datetime_approved = models.DateTimeField(null=True)
    is_approved = models.SmallIntegerField(default=0)
    results_file_path = models.CharField(max_length=64, default="")


class ValidationAssignment(models.Model):
    sr_id = models.ForeignKey(SimulationRun, on_delete=models.CASCADE)
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    datetime_created = models.DateTimeField()
    datetime_approved = models.DateTimeField(null=True)
    is_approved = models.SmallIntegerField(default=0)


class ValidationAssignmentComment(models.Model):
    va_id = models.ForeignKey(ValidationAssignment, on_delete=models.CASCADE)
    comments = models.TextField()
    snapshot_url = models.CharField(max_length=100, default="")


class ValidationItemMetrics(models.Model):
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    metric_id = models.ForeignKey(Metric, on_delete=models.CASCADE)
