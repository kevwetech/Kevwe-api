"""
IdempotencyMixin — opt a DRF APIView into idempotency by inheritance:

    class CreateOrderView(IdempotencyMixin, APIView):
        permission_classes = [IsAuthenticated]
        def post(self, request):
            ...

Behaviour:
  - Only guards methods in `idempotency_methods` (default: POST).
  - Reads the key from the `Idempotency-Key` header.
  - Idempotency requires an authenticated user (the key is scoped to
    the user). An anonymous request carrying a key → 401.
  - If `idempotency_required` is True, a missing key → 400.
    If False (default), a missing key just skips the check.
  - On a completed duplicate, returns the ORIGINAL response.
  - On success, stores the response. On 5xx, releases the key so the
    client can retry.
"""
from rest_framework.response import Response

from .services import IdempotencyService


class IdempotencyMixin:
    idempotency_methods = ('POST',)
    idempotency_required = False
    idempotency_header = 'Idempotency-Key'

    def initial(self, request, *args, **kwargs):
        """Runs after auth + parsing, before the handler."""
        super().initial(request, *args, **kwargs)

        method = request.method.upper()
        if method not in self.idempotency_methods:
            return

        key = request.headers.get(self.idempotency_header)

        if not key:
            if self.idempotency_required:
                from apps.common.views import api_response
                from rest_framework import status as http_status
                # Raise via a stashed response (finalize will return it)
                self._idempotency_replay = api_response(
                    'error',
                    f'{self.idempotency_header} header is required',
                    http_status=http_status.HTTP_400_BAD_REQUEST,
                )
            return

        # Idempotency is user-scoped → must be authenticated
        if not request.user or not request.user.is_authenticated:
            from apps.common.views import api_response
            from rest_framework import status as http_status
            self._idempotency_replay = api_response(
                'error',
                'Authentication is required to use an Idempotency-Key',
                http_status=http_status.HTTP_401_UNAUTHORIZED,
            )
            return

        self._idempotency_key = key
        endpoint = request.path
        result = IdempotencyService.begin(
            key=key,
            user=request.user,
            endpoint=endpoint,
            method=method,
            body=request.data,
        )
        if result is not None:
            # Replay: short-circuit with the stored response
            replay_status, replay_body = result
            self._idempotency_replay = Response(
                replay_body, status=replay_status)

    def finalize_response(self, request, response, *args, **kwargs):
        # If we prepared a replay/short-circuit in initial(), return it
        replay = getattr(self, '_idempotency_replay', None)
        if replay is not None:
            return super().finalize_response(
                request, replay, *args, **kwargs)

        key = getattr(self, '_idempotency_key', None)
        if key and hasattr(response, 'data'):
            endpoint = request.path
            status_code = response.status_code
            if 200 <= status_code < 300:
                IdempotencyService.complete(
                    key=key, user=request.user, endpoint=endpoint,
                    response_status=status_code,
                    response_body=response.data,
                )
            elif status_code >= 500:
                # Server error → let the client retry the same key
                IdempotencyService.release(
                    key=key, user=request.user, endpoint=endpoint)
            # 4xx → keep the reservation; client must fix + use a new key

        return super().finalize_response(request, response, *args, **kwargs)