from django.db import models
from django.contrib.auth.models import User


class Simulation(models.Model):
    name = models.CharField(max_length=64, default="")
    results_dir = models.CharField(max_length=64, default="")

    def __str__(self):
        return self.name


class Subroutine(models.Model):
    name = models.CharField(max_length=64, default="")

    def __str__(self):
        return self.name

    @staticmethod
    def get_list_view_filters():
        return {
            'srv_id__sr_id__in': {
                'name': 'Simulation Run',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'SimulationRun',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            },
            'srv_id__sub_id__in': {
                'name': 'Subroutine',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'Subroutine',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            }
        }


class ValidationItem(models.Model):
    name = models.CharField(max_length=64, default="")
    description = models.TextField(null=True)

    def __str__(self):
        return self.name

    @staticmethod
    def get_list_view_filters():
        return {
            'srv_id__sr_id__in': {
                'name': 'Simulation Run',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'SimulationRun',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            },
            'srv_id__sub_id__in': {
                'name': 'Subroutine',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'Subroutine',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            },
            'srv_id__vi_id__in': {
                'name': 'Validation Item',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'ValidationItem',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            }
        }


class Metric(models.Model):
    name = models.CharField(max_length=64, default="")
    type = models.CharField(max_length=64, default="",  choices=[
        ('static', 'Static'),
        ('dynamic_graph', 'Live Graph'),
        ('map', 'Map')
    ])
    file_path = models.CharField(max_length=64, default="")
    graph_config = models.JSONField()
    file_name_regex = models.CharField(max_length=64, default="")

    def __str__(self):
        return self.name


class WFSubroutineValidationItem(models.Model):
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)


class WFSimulationSubroutine(models.Model):
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE)
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)


class WFAssignment(models.Model):
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE, null=True)
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE, null=True)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE, null=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)


class SimulationRun(models.Model):
    name = models.CharField(max_length=64, default="")
    sim_id = models.ForeignKey(Simulation, on_delete=models.CASCADE)
    datetime_created = models.DateTimeField()
    datetime_approved = models.DateTimeField(null=True)
    is_approved = models.SmallIntegerField(default=0)
    results_file_path = models.CharField(max_length=64, default="")

    def __str__(self):
        return self.name

    @staticmethod
    def get_list_view_filters():
        return {
            'sim_id_id__in': {
                'name': 'Simulation',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'Simulation',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            }
        }


class SimulationRunValidation(models.Model):
    sr_id = models.ForeignKey(SimulationRun, on_delete=models.CASCADE)
    sub_id = models.ForeignKey(Subroutine, on_delete=models.CASCADE)
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    datetime_created = models.DateTimeField()
    datetime_approved = models.DateTimeField(null=True)
    is_approved = models.SmallIntegerField(default=0)
    is_flagged = models.SmallIntegerField(default=0)


class ValidationAssignment(models.Model):
    srv_id = models.ForeignKey(SimulationRunValidation, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    is_approved = models.SmallIntegerField(default=0)
    datetime_approved = models.DateTimeField(null=True)

    @staticmethod
    def get_list_view_filters():
        return {
            'srv_id__sr_id__in': {
                'name': 'Simulation Run',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'SimulationRun',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            },
            'srv_id__sub_id__in': {
                'name': 'Subroutine',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'Subroutine',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            },
            'srv_id__vi_id__in': {
                'name': 'Validation Item',
                'type': 'multiselect',
                'data_source': 'query',
                'data_source_model': 'ValidationItem',
                'data_source_value': 'id',
                'data_source_text': 'name',
                'data_source_value_type': 'list'
            }
        }


class ValidationAssignmentComment(models.Model):
    srv_id = models.ForeignKey(SimulationRunValidation, on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    comments = models.TextField()
    snapshot_url = models.CharField(max_length=100, default="")


class ValidationItemMetrics(models.Model):
    vi_id = models.ForeignKey(ValidationItem, on_delete=models.CASCADE)
    metric_id = models.ForeignKey(Metric, on_delete=models.CASCADE)
