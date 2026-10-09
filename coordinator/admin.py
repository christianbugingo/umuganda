from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    Community,
    Participation,
    UmugandaProject,
    UserProfile,
    Volunteer,
)

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
    list_display = ('user', 'community', 'phone', 'update_account_link')
    search_fields = ('user__username', 'phone')

    @admin.display(description='Update account')
    def update_account_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user_id])
        return format_html('<a class="button" href="{}">Update</a>', url)

class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('volunteer', 'project', 'attended', 'hours_contributed', 'signed_up_at')
    list_filter = ('attended', 'project', 'volunteer')
    search_fields = ('volunteer__user__username', 'project__title')


class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'update_account_link',
        'role',
        'leader_type',
        'managed_area_label',
        'is_approved',
        'phone',
    )
    list_filter = ('role', 'leader_type', 'is_approved')
    list_editable = ('is_approved',)
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'phone',
        'district',
        'sector',
        'cell',
        'village',
    )

    @admin.display(description='Update account')
    def update_account_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user_id])
        return format_html('<a class="button" href="{}">Update</a>', url)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0
    fields = (
        'role',
        'leader_type',
        'community',
        'province',
        'district',
        'sector',
        'cell',
        'village',
        'is_approved',
        'phone',
        'photo',
    )


class VolunteerInline(admin.StackedInline):
    model = Volunteer
    extra = 0
    fields = ('community', 'phone')


class UserAdmin(DjangoUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'update_account_link',
    )
    inlines = (UserProfileInline, VolunteerInline)

    @admin.display(description='Update account')
    def update_account_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.pk])
        return format_html('<a class="button" href="{}">Update</a>', url)


admin.site.register(Community, CommunityAdmin)
admin.site.register(UmugandaProject, UmugandaProjectAdmin)
admin.site.register(Volunteer, VolunteerAdmin)
admin.site.register(Participation, ParticipationAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)



