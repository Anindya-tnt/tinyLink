from django.contrib import admin
from .models import *


class LinkAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['link', 'shortLink']}),
    ]


class HitsDatePointAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['hits', 'link' ]})
    ]
    list_display = ('link', 'hits', 'day')


admin.site.register(Link, LinkAdmin)
admin.site.register(HitsDatePoint, HitsDatePointAdmin)
