from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("sim/<int:sim_id>/assign-plan/", views.assign_plan, name="assign_plan"),
    path("sim/<int:sim_id>/renew/", views.renew, name="renew"),
    path("sim/<int:sim_id>/change-plan/", views.change_plan, name="change_plan"),
    path("sim/<int:sim_id>/suspend/", views.suspend, name="suspend"),
    path("sim/<int:sim_id>/cancel/", views.cancel, name="cancel"),
]
