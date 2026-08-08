"""
IdempotencyService — all the DB logic lives here so the mixin stays
a thin DRF adapter.

Flow:
  begin()   → looks up the key. Returns a REPLAY (stored response) if
              this action already completed, raises if in progress or
              if the body changed. Otherwise reserves the key
              (status=processing) and returns None to proceed.
  complete()→ stores the response against the key.
  release() → deletes a reserved key after a 5xx so retry is safe.

user is always an authenticated user (the mixin enforces auth on
idempotent endpoints), so no null handling here.
"""
import hashlib
import json

from django.db import IntegrityError, transaction

from .models import IdempotencyKey
from .exceptions import IdempotencyConflict, IdempotencyInProgress


def _fingerprint(body) -> str:
    """Stable SHA-256 of the request body for same-key/diff-body detection."""
    try:
        raw = json.dumps(body, sort_keys=True, default=str)
    except (TypeError, ValueError):
        raw = str(body)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class IdempotencyService:

    @staticmethod
    def begin(key, user, endpoint, method, body):
        """
        Reserve the key or return the stored response for a replay.

        Returns:
          (replay_status, replay_body)  → caller returns this as-is
          None                          → caller processes normally
        Raises:
          IdempotencyConflict   — same key, different body
          IdempotencyInProgress — same key, still processing
        """
        fingerprint = _fingerprint(body)

        existing = IdempotencyKey.objects.filter(
            key=key, user=user, endpoint=endpoint,
        ).first()

        if existing:
            # Expired key → treat as fresh: drop it and fall through
            if existing.is_expired:
                existing.delete()
            else:
                # Same key reused with a different payload → client bug
                if existing.request_fingerprint and \
                        existing.request_fingerprint != fingerprint:
                    raise IdempotencyConflict()
                if existing.status == IdempotencyKey.STATUS_PROCESSING:
                    raise IdempotencyInProgress()
                # Completed → replay the original response
                return existing.response_status, existing.response_body

        # Reserve it. Unique constraint guards against a race where two
        # identical requests arrive at the same instant.
        try:
            with transaction.atomic():
                IdempotencyKey.objects.create(
                    key=key, user=user, endpoint=endpoint,
                    method=method, request_fingerprint=fingerprint,
                    status=IdempotencyKey.STATUS_PROCESSING,
                )
        except IntegrityError:
            # Lost the race — the other request reserved it first
            raise IdempotencyInProgress()

        return None

    @staticmethod
    def complete(key, user, endpoint, response_status, response_body):
        """Store the final response so future retries replay it."""
        IdempotencyKey.objects.filter(
            key=key, user=user, endpoint=endpoint,
        ).update(
            status=IdempotencyKey.STATUS_COMPLETED,
            response_status=response_status,
            response_body=response_body,
        )

    @staticmethod
    def release(key, user, endpoint):
        """
        Delete a reserved key when processing failed (5xx / exception),
        so the client can safely retry the SAME key.
        """
        IdempotencyKey.objects.filter(
            key=key, user=user, endpoint=endpoint,
            status=IdempotencyKey.STATUS_PROCESSING,
        ).delete()