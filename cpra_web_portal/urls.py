"""cpra_web_portal URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from cpra_web_portal.views import datatable_views, list_views, misc_views, modal_views, model_views, report_views

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('', misc_views.Home.as_view(), name='home'),
    path('subroutine_edit_view/', model_views.Subroutine.as_view(), name='subroutine_new_view'),
    path('subroutine_edit_view/<int:id>/', model_views.Subroutine.as_view(), name='subroutine_edit_view'),
    path('validation_item_edit_view/', model_views.ValidationItem.as_view(), name='validation_item_new_view'),
    path('validation_item_edit_view/<int:id>/', model_views.ValidationItem.as_view(), name='validation_item_edit_view'),
    path('simulation_edit_view/', model_views.Simulation.as_view(), name='simulation_new_view'),
    path('simulation_edit_view/<int:id>/', model_views.Simulation.as_view(), name='simulation_edit_view'),
    path('admin_console/', misc_views.AdminConsole.as_view(), name='admin_console'),
    path('dictionaries_list_view/', misc_views.DictionariesListView.as_view(), name='dictionaries_list_view'),
    path('simulation_runs_list_view/', list_views.SimulationRunsListView.as_view(), name='simulation_runs_list_view'),
    path('subroutines_list_view/', list_views.SubroutinesListView.as_view(), name='subroutines_list_view'),
    path('resources/', misc_views.Resources.as_view(), name='resources'),
    path('resources/<str:path>/', misc_views.Resources.as_view(), name='resource_download'),
    path('tasks/', misc_views.Tasks.as_view(), name='tasks'),
    path('user_view/', model_views.User.as_view(), name='user_new_view'),
    path('user_view/<int:id>/', model_views.User.as_view(), name='user_edit_view'),
    path('users_list_view/', list_views.UsersListView.as_view(), name='users_list_view'),
    path('validation_item_overview/<int:id>/', misc_views.ValidationItemOverview.as_view(), name='validation_item_overview'),
    path('validation_item_view/<int:id>/', misc_views.ValidationItemDataViewerView.as_view(), name='validation_item_view'),
    path('validation_items_list_view/', list_views.ValidationItemsListView.as_view(), name='validation_items_list_view'),
    path('metric/', misc_views.get_metric, name='get_metric'),
    path('static_metric/', misc_views.get_static_metric, name='get_metric'),
    path('dynamic_graph_metric/', misc_views.get_dynamic_graph_metric, name='get_metric'),
    path('map_metric/', misc_views.get_map_metric, name='get_metric'),
    path('export_metric/', misc_views.export_metric, name='export_metric'),
    path('validation_item/<int:id>/', model_views.ValidationAssignment.as_view(), name='validation_assignment'),
    path('validation_item/<int:id>/<str:method>/', model_views.ValidationAssignment.as_view(),
         name='validation_assignment_methods'),
    path('validation_item_comment/', model_views.ValidationAssignmentComment.as_view(),
         name='validation_assignment_comment'),
    path('validation_item_comment/<int:id>', model_views.ValidationAssignmentComment.as_view(),
         name='validation_assignment_comment'),
    path('metric_view/', model_views.Metric.as_view(), name='metric_new_view'),
    path('metric_view/<int:id>/', model_views.Metric.as_view(), name='metric_edit_view'),
    path('validation_item/modal/<str:type>/', modal_views.ValidationItemModal.as_view(), name='validation_item_modal_view'),
    path('subroutine/modal/<str:type>/', modal_views.SubroutineModal.as_view(), name='subroutine_modal_view'),
    path('simulation/modal/<str:type>/', modal_views.SimulationModal.as_view(), name='simulation_modal_view'),
    path('comment/modal/<str:type>/', modal_views.CommentModal.as_view(), name='comment_modal_view'),
    path('comment/modal/<str:type>/<int:id>', modal_views.CommentModal.as_view(), name='comment_modal_view'),
    path('comment/', misc_views.get_comments, name='get_comments'),
    path('team_view/', model_views.Team.as_view(), name='team_new_view'),
    path('team_view/<int:id>/', model_views.Team.as_view(), name='team_edit_view'),
    path('team/modal/<str:type>', modal_views.TeamModal.as_view(), name='team_modal_view'),
    path('widget/review_status', misc_views.widget_review_status, name='widget_review_status'),
    path('datatables/validation_item_comments_table', datatable_views.ValidationItemCommentAjaxDatatableView.as_view(), name='ajax_datatable_validation_item_comments'),
    path('datatables/validation_assignment_table', datatable_views.ValidationAssignmentAjaxDatatableView.as_view(), name='ajax_datatable_validation_assignments'),
    path('datatables/comments_table', datatable_views.CommentAjaxDatatableView.as_view(), name='ajax_datatable_comments'),
    path('reports/comments/', report_views.CommentsReportView.as_view(), name='comments_report_view'),
    path('reports/tasks/', report_views.TasksReportView.as_view(), name='tasks_report_view')
]
