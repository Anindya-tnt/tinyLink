from django.conf.urls import include, url
from tiny_link import views
from django.contrib import admin

urlpatterns = [
    url(r'^$', views.home),
    url(r'^admin', admin.site.urls),
    url(r'^(?P<id>\w+)$', views.link),
    url(r'^statistics/(\w+)$', views.stats),
    url(r'^statistics/$', views.allStats)]

