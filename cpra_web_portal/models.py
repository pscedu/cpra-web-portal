from django.db import models


class Simulation(models.Model):
    name = models.CharField(max_length=64, default="")
    results_dir = models.CharField(max_length=64, default="")


class Subroutine(models.Model):
    name = models.CharField(max_length=64, default="")


class ValidationItem(models.Model):
    name = models.CharField(max_length=64, default="")


class User(models.Model):
    group = models.CharField(max_length=64, default="")
    name = models.CharField(max_length=64, default="")
    username = models.CharField(max_length=64, default="")
    password = models.CharField(max_length=64, default="")
    email = models.EmailField


class WFSubroutineValidationItem(models.Model):
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    list_id = models.IntegerField


class WFSimulationSubroutine(models.Model):
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE)
    sub_vi_list_id = models.ForeignKey(WFSubroutineValidationItem.list_id, on_delete=models.CASCADE)


class WFAssignment(models.Model):
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE)
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)


class SimulationRun(models.Model):
    name = models.CharField(max_length=64, default="")
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE)
    datetime_created = models.DateTimeField
    datetime_approved = models.DateTimeField
    is_approved = models.SmallIntegerField
    results_file_path = models.CharField(max_length=64, default="")


class ValidationAssignment(models.Model):
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    datetime_created = models.DateTimeField
    datetime_approved = models.DateTimeField
    is_approved = models.SmallIntegerField
(())

class ValidationAssignmentComment(models.Model):
    va_id = models.ForeignKey(ValidationAssignment, on_delete=models.CASCADE)
    comments = models.TextField
    snapshot_url = models.CharField(max_length=100, default="")
