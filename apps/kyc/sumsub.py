import os
import hmac
import hashlib
import time
import requests
import json

SUMSUB_APP_TOKEN = os.environ.get('SUMSUB_APP_TOKEN', '')
SUMSUB_SECRET_KEY = os.environ.get('SUMSUB_SECRET_KEY', '')
SUMSUB_BASE_URL = os.environ.get(
    'SUMSUB_BASE_URL', 'https://api.sumsub.com'
)


def _sign_request(method, path, body=b''):
    """Generate Sumsub HMAC signature."""
    ts = str(int(time.time()))
    data = ts.encode() + method.upper().encode() + path.encode()
    if body:
        data += body if isinstance(body, bytes) else body.encode()
    signature = hmac.new(
        SUMSUB_SECRET_KEY.encode(),
        data,
        digestmod=hashlib.sha256
    ).hexdigest()
    return ts, signature


def _headers(method, path, body=b''):
    ts, signature = _sign_request(method, path, body)
    return {
        'X-App-Token': SUMSUB_APP_TOKEN,
        'X-App-Access-Sig': signature,
        'X-App-Access-Ts': ts,
        'Accept': 'application/json',
    }


def is_configured():
    return bool(
        SUMSUB_APP_TOKEN
        and SUMSUB_SECRET_KEY
        and SUMSUB_APP_TOKEN != 'your_app_token_here'
        and SUMSUB_SECRET_KEY != 'your_secret_key_here'
    )

def create_applicant(user, use_case='booking'):
    """
    Create a Sumsub applicant for a user.
    Returns applicant_id or stub value.
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Create applicant for "
            f"{user.email} ({use_case})"
        )
        return f"STUB-{user.id}-{use_case}"

    path = '/resources/applicants?levelName=basic-kyc-level'
    payload = {
        'externalUserId': f"{user.id}-{use_case}",
        'email': user.email,
        'phone': getattr(user, 'phone', ''),
        'fixedInfo': {'country': 'NGA'},
    }

    body = json.dumps(payload).encode()
    headers = _headers('POST', path, body)
    headers['Content-Type'] = 'application/json'

    try:
        response = requests.post(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            data=body,
            timeout=15
        )
        data = response.json()
        return data.get('id')
    except Exception as e:
        print(f"[SUMSUB] Create applicant error: {e}")
        return None


def create_company_applicant(business):
    """
    Create a Sumsub company applicant for BusinessKYC.
    Returns company_id or stub value.
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Create company applicant "
            f"for {business.name}"
        )
        return f"STUB-BIZ-{business.id}"

    path = (
        '/resources/applicants'
        '?levelName=basic-kyc-level-for-companies'
    )
    payload = {
        'externalUserId': f"biz-{business.id}",
        'type': 'company',
        'fixedInfo': {
            'companyInfo': {
                'companyName': business.name,
                'country': 'NGA',
            }
        }
    }

    body = json.dumps(payload).encode()
    headers = _headers('POST', path, body)
    headers['Content-Type'] = 'application/json'

    try:
        response = requests.post(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            data=body,
            timeout=15
        )
        data = response.json()
        return data.get('id')
    except Exception as e:
        print(f"[SUMSUB] Create company applicant error: {e}")
        return None


def get_access_token(applicant_id, user_id, use_case='booking'):
    """
    Get a short-lived SDK access token for the frontend
    to initialize the Sumsub Web SDK.
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Get access token for "
            f"applicant {applicant_id}"
        )
        return f"STUB-TOKEN-{applicant_id}"

    path = (
        f'/resources/accessTokens'
        f'?userId={user_id}-{use_case}'
        f'&levelName=basic-kyc-level'
    )
    headers = _headers('POST', path)

    try:
        response = requests.post(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            timeout=15
        )
        data = response.json()
        return data.get('token')
    except Exception as e:
        print(f"[SUMSUB] Access token error: {e}")
        return None


def get_applicant_status(applicant_id):
    """
    Get the current review status of an applicant.
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Get status for {applicant_id}"
        )
        return {
            'reviewStatus': 'completed',
            'reviewResult': {
                'reviewAnswer': 'GREEN',
                'riskLabels': [],
            }
        }

    path = (
        f'/resources/applicants/{applicant_id}'
        f'/requiredIdDocsStatus'
    )
    headers = _headers('GET', path)

    try:
        response = requests.get(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            timeout=15
        )
        return response.json()
    except Exception as e:
        print(f"[SUMSUB] Get status error: {e}")
        return None


def get_applicant_data(applicant_id):
    """
    Get full applicant data including extracted fields.
    Used to populate verified identity fields.
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Get applicant data "
            f"for {applicant_id}"
        )
        return {
            'info': {
                'firstNameEn': 'Test',
                'lastNameEn': 'User',
                'dob': '1990-01-01',
                'gender': 'M',
                'country': 'NGA',
                'nationality': 'Nigerian',
            },
            'review': {
                'reviewAnswer': 'GREEN',
                'riskLabels': [],
                'reviewRejectType': None,
            }
        }

    path = f'/resources/applicants/{applicant_id}/one'
    headers = _headers('GET', path)

    try:
        response = requests.get(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            timeout=15
        )
        return response.json()
    except Exception as e:
        print(f"[SUMSUB] Get applicant data error: {e}")
        return None


def upload_document(applicant_id, file, document_type):
    """
    Upload an ID document to Sumsub.
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Upload {document_type} "
            f"for applicant {applicant_id}"
        )
        return f"STUB-DOC-{applicant_id}-{document_type}"

    path = (
        f'/resources/applicants/{applicant_id}'
        f'/info/idDoc'
    )
    headers = _headers('POST', path)

    type_map = {
        'passport': 'PASSPORT',
        'drivers_license': 'DRIVERS',
        'nin': 'ID_CARD',
        'voters_card': 'ID_CARD',
        'cac': 'COMPANY_DOC',
        'tin': 'COMPANY_DOC',
    }

    file.seek(0)
    files = {
        'content': (
            file.name, file.read(), file.content_type
        )
    }
    data = {
        'metadata': (
            None,
            json.dumps({
                'idDocType': type_map.get(
                    document_type, 'ID_CARD'
                ),
                'country': 'NGA'
            }),
            'application/json'
        )
    }

    try:
        response = requests.post(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )
        result = response.json()
        return result.get('idDocSetType', str(result))
    except Exception as e:
        print(f"[SUMSUB] Upload document error: {e}")
        return None


def upload_selfie(applicant_id, file):
    """
    Upload a selfie/liveness photo to Sumsub.
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Upload selfie for "
            f"applicant {applicant_id}"
        )
        return {
            'id': f"STUB-SELFIE-{applicant_id}",
            'livenessScore': 98.5,
            'faceMatchScore': 95.2,
        }

    path = (
        f'/resources/applicants/{applicant_id}'
        f'/info/idDoc'
    )
    headers = _headers('POST', path)

    file.seek(0)
    files = {
        'content': (
            file.name, file.read(), file.content_type
        )
    }
    data = {
        'metadata': (
            None,
            json.dumps({
                'idDocType': 'SELFIE',
                'country': 'NGA'
            }),
            'application/json'
        )
    }

    try:
        response = requests.post(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            files=files,
            data=data,
            timeout=30
        )
        return response.json()
    except Exception as e:
        print(f"[SUMSUB] Upload selfie error: {e}")
        return None


def check_watchlist(applicant_id):
    """
    Get watchlist/PEP/sanctions screening results
    for an applicant.
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Check watchlist for "
            f"{applicant_id}"
        )
        return {
            'items': [],
            'status': 'clear'
        }

    path = (
        f'/resources/applicants/{applicant_id}'
        f'/checks/latest'
    )
    headers = _headers('GET', path)

    try:
        response = requests.get(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            timeout=15
        )
        return response.json()
    except Exception as e:
        print(f"[SUMSUB] Watchlist check error: {e}")
        return None


def reset_applicant(applicant_id):
    """
    Reset an applicant for re-verification (on retry).
    """
    if not is_configured():
        print(
            f"[SUMSUB STUB] Reset applicant {applicant_id}"
        )
        return True

    path = (
        f'/resources/applicants/{applicant_id}'
        f'/resetAll'
    )
    headers = _headers('POST', path)

    try:
        response = requests.post(
            f"{SUMSUB_BASE_URL}{path}",
            headers=headers,
            timeout=15
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[SUMSUB] Reset applicant error: {e}")
        return False


def verify_webhook_signature(payload, signature, secret=None):
    """Verify incoming Sumsub webhook signature."""
    secret = secret or SUMSUB_SECRET_KEY
    if not secret:
        return True  # Skip verification in dev
    expected = hmac.new(
        secret.encode(),
        payload if isinstance(payload, bytes)
        else payload.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)