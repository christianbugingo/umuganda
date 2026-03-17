from django.contrib import admin
from .models import Community, UmugandaProject, Volunteer, Participation

class CommunityAdmin(admin.ModelAdmin):
    list_display = ('village', 'cell', 'sector', 'district', 'get_province_display', 'population', 'leader')
    list_filter = ('province', 'district', 'sector')
    search_fields = ('village', 'cell', 'sector', 'district')
    fieldsets = (
        ('Administrative Information', {
            'fields': ('province', 'district', 'sector', 'cell', 'village')
        }),
        ('Community Details', {
            'fields': ('population', 'households', 'leader', 'leader_phone')
        }),
    )

class UmugandaProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'community', 'date', 'status')
    list_filter = ('status', 'date', 'community__province', 'community__district')
    search_fields = ('title', 'description', 'location')
    raw_id_fields = ('community',)

class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'phone')
    search_fields = ('user__username', 'phone')

class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'project', 'attended', 'hours_contributed', 'signed_up_at')
    list_filter = ('attended', 'project', 'volunteer')
    search_fields = ('volunteer__user__username', 'project__title')

admin.site.register(Community, CommunityAdmin)
admin.site.register(UmugandaProject, UmugandaProjectAdmin)
admin.site.register(Volunteer, VolunteerAdmin)
admin.site.register(Participation, ParticipationAdmin)





