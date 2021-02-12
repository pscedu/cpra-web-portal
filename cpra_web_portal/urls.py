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
from . import views

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('', views.Home.as_view(), name='home'),
    path('metric_edit_view/', views.MetricEditView.as_view(), name='metric_edit_view'),
    path('subroutine_edit_view/', views.SubroutineEditView.as_view(), name='subroutine_edit_view'),
    path('validation_item_edit_view/', views.ValidationItemEditView.as_view(), name='validation_item_edit_view'),
    path('simulation_edit_view/', views.SimulationEditView.as_view(), name='simulation_edit_view'),
    path('admin_console/', views.AdminConsole.as_view(), name='admin_console'),
    path('dictionaries_list_view/', views.DictionariesListView.as_view(), name='dictionaries_list_view'),
    path('simulation_runs_list_view/', views.SimulationRunsListView.as_view(), name='simulation_runs_list_view'),
    path('subroutines_list_view/', views.SubroutinesListView.as_view(), name='subroutines_list_view'),
    path('tasks/', views.Tasks.as_view(), name='tasks'),
    path('user_item_view/', views.UserItemView.as_view(), name='user_item_view'),
    path('users_list_view/', views.UsersListView.as_view(), name='users_list_view'),
    path('validation_item_view/<int:id>', views.ValidationItemView.as_view(), name='validation_item_view'),
    path('validation_items_list_view/', views.ValidationItemsListView.as_view(), name='validation_items_list_view'),
    path('metric/', views.get_metric, name='get_metric'),
    path('static_metric/', views.get_static_metric, name='get_metric')
]
