from rest_framework import serializers
from .models import (
    Permission, Role, RolePermission, BusinessMember,
    StaffInvitation, StaffAccount, WorkSchedule,
    StaffActivityLog, Department, StaffShift,
    StaffAttendance, StaffDevice, TemporaryPermission,
    StaffNote, StaffLeave, StaffPIN,
)
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class RolePermissionSerializer(serializers.ModelSerializer):
    permission_code = serializers.CharField(
        source='permission.code', read_only=True
    )
    permission_name = serializers.CharField(
        source='permission.name', read_only=True
    )

    class Meta:
        model = RolePermission
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class RoleSerializer(serializers.ModelSerializer):
    permissions_detail = PermissionSerializer(
        source='permissions', many=True, read_only=True
    )
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = '__all__'
        read_only_fields = (
            'id', 'business', 'created_at', 'updated_at'
        )

    def get_members_count(self, obj):
        return obj.members.filter(status='active').count()


class WorkScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class BusinessMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source='user.full_name', read_only=True
    )
    user_email = serializers.CharField(
        source='user.email', read_only=True
    )
    user_phone = serializers.CharField(
        source='user.phone', read_only=True
    )
    user_avatar = serializers.ImageField(
        source='user.avatar', read_only=True
    )
    role_name = serializers.CharField(
        source='role.name', read_only=True
    )
    schedule = WorkScheduleSerializer(
        many=True, read_only=True
    )
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = BusinessMember
        fields = '__all__'
        read_only_fields = (
            'id', 'joined_at', 'invited_by',
            'created_at', 'updated_at'
        )

    def get_permissions(self, obj):
        """Return effective permissions for this member."""
        if not obj.role:
            return []
        perms = list(
            obj.role.permissions.values_list('code', flat=True)
        )
        extra = list(
            obj.extra_permissions.values_list('code', flat=True)
        )
        denied = list(
            obj.denied_permissions.values_list('code', flat=True)
        )
        effective = set(perms + extra) - set(denied)
        return list(effective)


class StaffInvitationSerializer(serializers.ModelSerializer):
    invited_by_name = serializers.CharField(
        source='invited_by.full_name', read_only=True
    )
    business_name = serializers.CharField(
        source='business.name', read_only=True
    )
    role_name = serializers.CharField(
        source='role.name', read_only=True
    )

    class Meta:
        model = StaffInvitation
        fields = '__all__'
        read_only_fields = (
            'id', 'token', 'status', 'invited_by',
            'accepted_by', 'accepted_at', 'expires_at',
            'created_at', 'updated_at'
        )


class StaffActivityLogSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(
        source='member.user.full_name', read_only=True
    )

    class Meta:
        model = StaffActivityLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.CharField(
        source='head.user.full_name', read_only=True
    )
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_members_count(self, obj):
        return obj.members.filter(
            member__status='active'
        ).count()


class StaffShiftSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(
        source='member.user.full_name', read_only=True
    )

    class Meta:
        model = StaffShift
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class StaffAttendanceSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(
        source='member.user.full_name', read_only=True
    )
    hours_worked = serializers.FloatField(read_only=True)

    class Meta:
        model = StaffAttendance
        fields = '__all__'
        read_only_fields = (
            'id', 'is_late', 'late_minutes',
            'overtime_minutes', 'created_at', 'updated_at'
        )


class StaffDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffDevice
        fields = '__all__'
        read_only_fields = (
            'id', 'last_login', 'created_at', 'updated_at'
        )


class TemporaryPermissionSerializer(
    serializers.ModelSerializer
):
    permission_code = serializers.CharField(
        source='permission.code', read_only=True
    )
    permission_name = serializers.CharField(
        source='permission.name', read_only=True
    )
    granted_by_name = serializers.CharField(
        source='granted_by.full_name', read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = TemporaryPermission
        fields = '__all__'
        read_only_fields = (
            'id', 'granted_by', 'created_at', 'updated_at'
        )


class StaffNoteSerializer(serializers.ModelSerializer):
    written_by_name = serializers.CharField(
        source='written_by.full_name', read_only=True
    )

    class Meta:
        model = StaffNote
        fields = '__all__'
        read_only_fields = (
            'id', 'written_by', 'created_at', 'updated_at'
        )


class StaffLeaveSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(
        source='member.user.full_name', read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.full_name', read_only=True
    )
    days_requested = serializers.IntegerField(read_only=True)

    class Meta:
        model = StaffLeave
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'reviewed_by',
            'reviewed_at', 'created_at', 'updated_at'
        )


class StaffPINSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffPIN
        exclude = ('pin_hash',)
        read_only_fields = (
            'id', 'last_used', 'failed_attempts',
            'locked_until', 'created_at', 'updated_at'
        )