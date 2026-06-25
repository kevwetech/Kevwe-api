def send_booking_checkin_notification(booking):
    """
    Send check-in code + Google Maps directions to customer
    via email, SMS, and WhatsApp after booking is paid.
    """
    from apps.common.email import send_booking_checkin_email
    from apps.common.termii import (
        send_booking_confirmation_sms,
        send_booking_confirmation_whatsapp,
    )

    import os
    from urllib.parse import quote

    business = booking.business
    frontend_url = os.environ.get('FRONTEND_URL', 'https://kovolt.com')

    maps_link = None
    if business and business.latitude and business.longitude:
        maps_link = (
            f"{frontend_url}/map"
            f"?lat={business.latitude}"
            f"&lng={business.longitude}"
            f"&name={quote(str(business.name))}"
            f"&address={quote(str(business.address or ''))}"
        )
    elif business and business.address:
        maps_link = (
            f"{frontend_url}/map"
            f"?name={quote(str(business.name))}"
            f"&address={quote(str(business.address or ''))}"
        )
    # Email
    try:
        send_booking_checkin_email(booking)
    except Exception as e:
        print(f"Booking email error: {e}")

    # SMS
    phone = booking.guest_phone
    if phone:
        try:
            send_booking_confirmation_sms(phone, booking, maps_link)
        except Exception as e:
            print(f"Booking SMS error: {e}")

        # WhatsApp
        try:
            send_booking_confirmation_whatsapp(
                phone, booking, maps_link
            )
        except Exception as e:
            print(f"Booking WhatsApp error: {e}")