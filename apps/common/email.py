import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_email(
    to_email,
    subject,
    html_content,
    plain_content=None
):
    """
    Send email using SendGrid HTTP API
    Works on both cPanel and cloud hosting
    """
    try:
        sg = SendGridAPIClient(
            api_key=os.getenv('SENDGRID_API_KEY')
        )

        from_email = Email(settings.DEFAULT_FROM_EMAIL)
        to_email = To(to_email)
        subject = subject
        content = Content("text/html", html_content)

        mail = Mail(
            from_email,
            to_email,
            subject,
            content
        )

        response = sg.client.mail.send.post(
            request_body=mail.get()
        )

        print(f"Email sent to {to_email} - Status: {response.status_code}")
        return True

    except Exception as e:
        logger.error(f"Email error: {str(e)}")
        print(f"Email error: {str(e)}")
        return False


def send_otp_email(to_email, otp, otp_type, name=None):
    """Send OTP email"""
    if otp_type == 'email_verification':
        subject = 'Verify Your Email Address'
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #4CAF50; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Email Verification</h1>
            </div>
            <div style="padding: 30px; background: #f9f9f9;">
                <h2>Hi {name or 'there'}!</h2>
                <p>Your email verification code is:</p>
                <div style="background: #fff; border: 2px solid #4CAF50; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #4CAF50; font-size: 48px; margin: 0; letter-spacing: 10px;">{otp}</h1>
                </div>
                <p>This code expires in <strong>10 minutes.</strong></p>
                <p style="color: #999; font-size: 12px;">If you didn't request this, please ignore this email.</p>
            </div>
        </div>
        """
    else:
        subject = 'Password Reset Code'
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #2196F3; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Password Reset</h1>
            </div>
            <div style="padding: 30px; background: #f9f9f9;">
                <h2>Hi {name or 'there'}!</h2>
                <p>Your password reset code is:</p>
                <div style="background: #fff; border: 2px solid #2196F3; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #2196F3; font-size: 48px; margin: 0; letter-spacing: 10px;">{otp}</h1>
                </div>
                <p>This code expires in <strong>10 minutes.</strong></p>
                <p style="color: #999; font-size: 12px;">If you didn't request this, please ignore this email.</p>
            </div>
        </div>
        """

    return send_email(to_email, subject, html_content)


def send_order_confirmation_email(order):
    """Send order confirmation email"""
    items_html = ''.join([
        f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">{item.product_name}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item.quantity}</td>
            <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">₦{item.subtotal}</td>
        </tr>
        """
        for item in order.items.all()
    ])

    subject = f'Order Confirmed - {order.reference}'
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #333; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Order Confirmed! 🎉</h1>
        </div>
        <div style="padding: 30px;">
            <h2>Hi {order.user.full_name}!</h2>
            <p>Your order has been confirmed.</p>

            <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Reference:</strong> {order.reference}</p>
                <p><strong>Status:</strong> {order.status}</p>
                <p><strong>Shipping to:</strong> {order.shipping_address}, {order.shipping_city}</p>
            </div>

            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f0f0f0;">
                        <th style="padding: 10px; text-align: left;">Item</th>
                        <th style="padding: 10px; text-align: center;">Qty</th>
                        <th style="padding: 10px; text-align: right;">Price</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="2" style="padding: 10px; text-align: right;"><strong>Subtotal:</strong></td>
                        <td style="padding: 10px; text-align: right;">₦{order.subtotal}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding: 10px; text-align: right;"><strong>Shipping:</strong></td>
                        <td style="padding: 10px; text-align: right;">₦{order.shipping_fee}</td>
                    </tr>
                    <tr style="background: #f9f9f9;">
                        <td colspan="2" style="padding: 10px; text-align: right;"><strong>Total:</strong></td>
                        <td style="padding: 10px; text-align: right;"><strong>₦{order.total}</strong></td>
                    </tr>
                </tfoot>
            </table>
        </div>
    </div>
    """

    return send_email(order.user.email, subject, html_content)


def send_booking_confirmation_email(booking):
    """Send booking confirmation email"""
    subject = f'Booking Confirmed - {booking.reference}'
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #9C27B0; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Booking Confirmed! 🏨</h1>
        </div>
        <div style="padding: 30px;">
            <h2>Hi {booking.guest_name}!</h2>
            <p>Your booking has been confirmed.</p>

            <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Reference:</strong> {booking.reference}</p>
                <p><strong>Item:</strong> {booking.item.name}</p>
                <p><strong>Check-in:</strong> {booking.check_in}</p>
                <p><strong>Check-out:</strong> {booking.check_out}</p>
                <p><strong>Duration:</strong> {booking.duration} nights</p>
                <p><strong>Guests:</strong> {booking.guests}</p>
                <p><strong>Total:</strong> ₦{booking.total}</p>
            </div>

            <p style="color: #999; font-size: 12px;">
                If you have any questions please contact us.
            </p>
        </div>
    </div>
    """

    return send_email(booking.guest_email, subject, html_content)


def send_shipment_confirmation_email(shipment):
    """Send shipment confirmation email"""
    subject = f'Shipment Created - {shipment.tracking_number}'
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #FF5722; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Shipment Created! 📦</h1>
        </div>
        <div style="padding: 30px;">
            <h2>Hi {shipment.sender.full_name}!</h2>
            <p>Your shipment has been created successfully.</p>

            <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Tracking Number:</strong>
                    <span style="font-size: 20px; font-weight: bold; color: #FF5722;">
                        {shipment.tracking_number}
                    </span>
                </p>
                <p><strong>Package:</strong> {shipment.package_name}</p>
                <p><strong>From:</strong> {shipment.pickup_city}, {shipment.pickup_state}</p>
                <p><strong>To:</strong> {shipment.delivery_city}, {shipment.delivery_state}</p>
                <p><strong>Receiver:</strong> {shipment.receiver_name}</p>
                <p><strong>Price:</strong> ₦{shipment.price}</p>
            </div>

            <p>Track your shipment using your tracking number above.</p>
        </div>
    </div>
    """

    return send_email(shipment.sender.email, subject, html_content)


def send_ride_confirmation_email(ride):
    """Send ride confirmation email"""
    subject = f'Ride Confirmed - {ride.reference}'
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #000; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Ride Confirmed! 🚗</h1>
        </div>
        <div style="padding: 30px;">
            <h2>Hi {ride.rider.full_name}!</h2>
            <p>Your ride has been confirmed.</p>

            <div style="background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Reference:</strong> {ride.reference}</p>
                <p><strong>Driver:</strong> {ride.driver.user.full_name if ride.driver else 'Searching...'}</p>
                <p><strong>Pickup:</strong> {ride.pickup_address}</p>
                <p><strong>Destination:</strong> {ride.destination_address}</p>
                <p><strong>Estimated Fare:</strong> ₦{ride.estimated_fare}</p>
                <p><strong>Distance:</strong> {ride.distance_km} km</p>
            </div>
        </div>
    </div>
    """

    return send_email(ride.rider.email, subject, html_content)