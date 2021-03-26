import os
import csv

from django.forms.models import model_to_dict
from django.db.models import Sum, Count
from django.apps import apps

from . import models


def populate_filters(filters):
    for filter_id, filter in filters.items():
        filter['options'] = []
        if filter['data_source'] == 'query':
            for filter_option in apps.get_model('cpra_web_portal', filter['data_source_model']).objects.all():
                filter_option = model_to_dict(filter_option)
                filter['options'].append({
                    'value': str(filter_option[filter['data_source_value']]),
                    'text': filter_option[filter['data_source_text']]
                })


def set_filter_values(filters, request):
    for query_object in request.GET:
        if query_object in filters:
            value = request.GET.get(query_object)
            filter_type = filters[query_object]['data_source_value_type']
            if filter_type == 'list':
                value = value.split(",")
            elif filter_type == 'int':
                value = int(value)
            filters[query_object]['value'] = value


def filter_queryset(queryset, request):
    filter_dict = {}
    for query_object in request.GET:
        if 'in' in query_object:
            value = request.GET.get(query_object).split(',')
        else:
            value = request.GET.get(query_object)
        filter_dict[query_object] = value

    return queryset.filter(**filter_dict)


def update_approval(validation_assignment):
    # Get all of the related validation assignments
    srv = models.SimulationRunValidation.objects.get(id=validation_assignment.srv_id_id)
    sim_run = models.SimulationRun.objects.get(id=srv.sr_id_id)

    # Get
    sum_count_related_vas = models.ValidationAssignment.objects.filter(srv_id=validation_assignment.srv_id).aggregate(
        num_related=Count('id'), num_approved=Sum('is_approved'))

    srv.is_approved = sum_count_related_vas['num_related'] == sum_count_related_vas['num_approved']
    srv.save()

    sum_count_related_srvs = models.SimulationRunValidation.objects.filter(sr_id=srv.sr_id).aggregate(
        num_related=Count('id'), num_approved=Sum('is_approved'))
    sim_run.is_approved = sum_count_related_srvs['num_related'] == sum_count_related_srvs['num_approved']
    sim_run.save()


def update_related_tables(related_tables):
    from django.apps import apps
    parent_table = related_tables.pop('parent_table')
    for related_table, actions in related_tables.items():
        related_table_model = apps.get_model('cpra_web_portal', related_table)
        for action in actions:
            if action == 'delete':
                related_table_model.objects.filter(id__in=actions[action]).delete()
            elif action == 'add':
                items_to_add = []
                for item_to_add in actions[action]:
                    item_to_add[parent_table['id_field']] = parent_table['id_value']
                    items_to_add.append(related_table_model(**item_to_add))
                related_table_model.objects.bulk_create(items_to_add)


def get_metric_files(metric, file_path):
    if metric.type == "dynamic_graph" and metric.graph_config['misc']['data_model'] != 'extraction_points':
        return get_dynamic_graph_metric_files(metric, file_path)

    if "map" in metric.type:
        parent_index = 0
        child_index = 9
    else:
        parent_index = 12
        child_index = 11

    # files will be structured as follows
    # files = {'region': {'point': 'filename'}}
    files = {}
    # I also need to get all of the files listed under this metric

    for file in os.listdir(file_path):
        if os.path.isdir(os.path.join(file_path, file)):
            continue

        file_name_list = file.split("_")
        parent = file_name_list[parent_index]
        if parent in files:
            files[parent][file_name_list[child_index]] = file
        else:
            files[parent] = {file_name_list[child_index]: file}

    return files


def get_dynamic_graph_metric_files(metric, file_path):
    files = {'Coastwide': {}}

    dynamic_graph_data_model = metric.graph_config['misc']['data_model']
    first_file = [f for f in os.listdir(file_path) if metric.file_name_regex in f][0]

    first_file_path = os.path.join(file_path, first_file)

    with open(first_file_path, 'r') as f:
        dict_reader = csv.DictReader(f)
        num_compartments = len(list(dict_reader)) if dynamic_graph_data_model == 'hydro_compartments' else len(next(dict_reader))

    for x in range(1, num_compartments+1):
        files['Coastwide'][str(x)] = str(x)

    return files
