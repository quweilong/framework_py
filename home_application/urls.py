# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import views

urlpatterns = (
    url(r'^$', views.home),
    url(r'^dev-guide/$', views.dev_guide),
    url(r'^contact/$', views.contact),
    url(r'^screen/$',views.screen),
    url(r'^detailspage/$', views.detailspage),
    url(r'^get_data/$', views.get_data),
    url(r'^get_detailspage_info/$', views.get_detailspage_info),



)
