import secrets
from django.utils import timezone
from datetime import timedelta


def generate_invitation_token():
    return secrets.token_urlsafe(32)


def generate_temp_password():
    """Generate a readable temporary password."""
    import random
    import string
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=10))


def send_staff_invitation(invitation):
    """
    Send invitation via email and/or SMS/WhatsApp.
    """
    from apps.common.email import send_email
    from apps.common.termii import send_sms, send_whatsapp

    business = invitation.business
    invite_url = (
        f"{__import__('os').environ.get('FRONTEND_URL', 'https://kovolt.com')}"
        f"/staff/accept-invite/{invitation.token}"
    )

    # Email
    if invitation.email:
        try:
            subject = (
                f"You're invited to join "
                f"{business.name} on Kovolt"
            )
            html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #1a1a2e; padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Staff Invitation</h1>
                </div>
                <div style="padding: 30px; background: #f9f9f9;">
                    <h2>Hi {invitation.name or 'there'}!</h2>
                    <p>
                        <strong>{invitation.invited_by.full_name}</strong>
                        has invited you to join
                        <strong>{business.name}</strong>
                        as <strong>{invitation.role.name if invitation.role else invitation.job_title or 'Staff'}</strong>.
                    </p>
                    {f'<p><em>"{invitation.message}"</em></p>' if invitation.message else ''}
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invite_url}"
                           style="background: #FF6600; color: white; padding: 14px 28px;
                                  border-radius: 6px; text-decoration: none;
                                  font-weight: bold; font-size: 16px;">
                            Accept Invitation
                        </a>
                    </div>
                    <p style="color: #999; font-size: 12px;">
                        This invitation expires in 7 days.
                        If you didn't expect this, you can ignore it.
                    </p>
                </div>
            </div>
            """
            send_email(invitation.email, subject, html)
        except Exception as e:
            print(f"[STAFF] Email invite error: {e}")

    # SMS
    if invitation.phone:
        try:
            msg = (
                f"You're invited to join {business.name} "
                f"as {invitation.role.name if invitation.role else 'Staff'}. "
                f"Accept here: {invite_url}"
            )
            send_sms(invitation.phone, msg)
            send_whatsapp(invitation.phone, msg)
        except Exception as e:
            print(f"[STAFF] SMS invite error: {e}")


def send_temp_password_notification(user, business, temp_password):
    """Send temporary password to newly created staff."""
    from apps.common.email import send_email
    from apps.common.termii import send_sms

    subject = f"Your {business.name} staff account"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Staff Account Created</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2>Hi {user.full_name}!</h2>
            <p>A staff account has been created for you at <strong>{business.name}</strong>.</p>
            <div style="background: #fff; border: 2px solid #1a1a2e; border-radius: 8px;
                        padding: 20px; text-align: center; margin: 20px 0;">
                <p><strong>Email:</strong> {user.email}</p>
                <p><strong>Temporary Password:</strong>
                   <span style="font-size: 24px; font-weight: bold; color: #FF6600;">
                     {temp_password}
                   </span>
                </p>
            </div>
            <p>Please log in and change your password immediately.</p>
            <p style="color: #999; font-size: 12px;">
                Do not share your password with anyone.
            </p>
        </div>
    </div>
    """
    try:
        send_email(user.email, subject, html)
    except Exception as e:
        print(f"[STAFF] Temp password email error: {e}")

    if user.phone:
        try:
            send_sms(
                user.phone,
                f"Your {business.name} staff account: "
                f"Email: {user.email}, "
                f"Temp password: {temp_password}. "
                f"Please change it on first login."
            )
        except Exception as e:
            print(f"[STAFF] Temp password SMS error: {e}")


def check_permission(user, business, permission_code):
    """
    Check if a user has a permission within a business.
    Returns True/False.
    """
    from .models import BusinessMember

    # Business owner has all permissions
    if business.owner == user:
        return True

    try:
        member = BusinessMember.objects.get(
            user=user,
            business=business,
            status='active'
        )
        return member.has_permission(permission_code)
    except BusinessMember.DoesNotExist:
        return False


def log_staff_action(
    user, business, action,
    description='', metadata=None,
    ip_address=None
):
    """Log a staff action for audit trail."""
    from .models import BusinessMember, StaffActivityLog
    try:
        member = BusinessMember.objects.get(
            user=user, business=business
        )
        StaffActivityLog.objects.create(
            member=member,
            action=action,
            description=description,
            ip_address=ip_address,
            metadata=metadata or {},
        )
    except BusinessMember.DoesNotExist:
        pass