from django.contrib import admin
from .models import (
    Permission, Role, RolePermission, BusinessMember,
    StaffInvitation, StaffAccount, WorkSchedule,
    StaffActivityLog, Department, StaffShift,
    StaffAttendance, StaffDevice, TemporaryPermission,
    StaffNote, StaffLeave, StaffPIN,
)

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'name', 'category',
        'is_owner_only', 'is_active'
    )
    list_filter = ('category', 'is_owner_only', 'is_active')
    search_fields = ('code', 'name')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'business', 'parent_role',
        'is_default', 'is_active'
    )
    list_filter = ('is_default', 'is_active')
    search_fields = ('name', 'business__name')

@admin.register(BusinessMember)
class BusinessMemberAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'business', 'role', 'department',
        'branch', 'status', 'joined_at'
    )
    list_filter = ('status',)
    search_fields = ('user__email', 'business__name')

@admin.register(StaffInvitation)
class StaffInvitationAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'phone', 'business',
        'role', 'status', 'expires_at'
    )
    list_filter = ('status',)
    search_fields = ('email', 'phone', 'business__name')

@admin.register(StaffActivityLog)
class StaffActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'action', 'object_type',
        'object_id', 'ip_address', 'created_at'
    )
    list_filter = ('action',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'head', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'business__name')

@admin.register(StaffShift)
class StaffShiftAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'shift_type', 'date',
        'start_time', 'end_time', 'status'
    )
    list_filter = ('shift_type', 'status')

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'date', 'clock_in',
        'clock_out', 'is_late', 'overtime_minutes'
    )
    list_filter = ('is_late',)

@admin.register(StaffDevice)
class StaffDeviceAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'device_name', 'ip_address',
        'is_trusted', 'last_login', 'is_active'
    )
    list_filter = ('is_trusted', 'is_active')

@admin.register(TemporaryPermission)
class TemporaryPermissionAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'permission', 'granted_by',
        'expires_at', 'is_active'
    )
    list_filter = ('is_active',)

@admin.register(StaffNote)
class StaffNoteAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'note_type', 'written_by',
        'is_private', 'created_at'
    )
    list_filter = ('note_type', 'is_private')

@admin.register(StaffLeave)
class StaffLeaveAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'leave_type', 'start_date',
        'end_date', 'status', 'days_requested'
    )
    list_filter = ('leave_type', 'status')

@admin.register(StaffPIN)
class StaffPINAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'pin_enabled',
        'last_used', 'failed_attempts'
    )
    list_filter = ('pin_enabled',)

admin.site.register(RolePermission)
admin.site.register(StaffAccount)
admin.site.register(WorkSchedule)