from rest_framework.exceptions import APIException
from rest_framework import status


class IdempotencyConflict(APIException):
    """Same key, different request body — the client is misusing the key."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        'This Idempotency-Key was already used with a different '
        'request. Use a new key for a new action.'
    )
    default_code = 'idempotency_conflict'


class IdempotencyInProgress(APIException):
    """Same key still being processed — a rapid double-submit."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = (
        'A request with this Idempotency-Key is still being '
        'processed. Please wait.'
    )
    default_code = 'idempotency_in_progress'