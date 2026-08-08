"""
IdempotencyMixin — opt a DRF APIView into idempotency by inheritance:

    class CreateOrderView(IdempotencyMixin, APIView):
        permission_classes = [IsAuthenticated]
        def post(self, request):
            ...

Behaviour:
  - Only guards methods in `idempotency_methods` (default: POST).
  - Reads the key from the `Idempotency-Key` header.
  - Idempotency is user-scoped → an anonymous request carrying a key
    is rejected (401).
  - If `idempotency_required` is True, a missing key → 400.
  - On a completed duplicate, returns the ORIGINAL response (via a
    raised replay exception so the handler never runs twice).
  - On success (2xx), stores the response. On any non-2xx, releases
    the key so the client can retry (with a fixed payload for 4xx).

Implementation note: short-circuiting a DRF view from initial() is
done by RAISING. DRF's exception handler turns the raise into the
response. We use a small internal exception carrying the stored
response, handled in handle_exception().
"""
from rest_framework.response import Response
from rest_framework.exceptions import APIException, NotAuthenticated, ValidationError

from .services import IdempotencyService


class _IdempotencyReplay(APIException):
    """Internal: carries a stored response to short-circuit the view."""
    status_code = 200

    def __init__(self, response_status, response_body):
        self.replay_status = response_status
        self.replay_body = response_body
        super().__init__(detail='replay')


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
                raise ValidationError(
                    {self.idempotency_header:
                        f'{self.idempotency_header} header is required.'})
            return

        # Idempotency is user-scoped → must be authenticated
        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated(
                'Authentication is required to use an Idempotency-Key.')

        # Stash for finalize_response to store/release the outcome
        self._idempotency_key = key

        result = IdempotencyService.begin(
            key=key,
            user=request.user,
            endpoint=request.path,
            method=method,
            body=request.data,
        )
        if result is not None:
            # Completed duplicate → replay the stored response.
            # We already have the final outcome, so don't let
            # finalize_response touch the key again.
            self._idempotency_key = None
            replay_status, replay_body = result
            raise _IdempotencyReplay(replay_status, replay_body)

    def handle_exception(self, exc):
        if isinstance(exc, _IdempotencyReplay):
            return Response(exc.replay_body, status=exc.replay_status)
        return super().handle_exception(exc)

    def finalize_response(self, request, response, *args, **kwargs):
        key = getattr(self, '_idempotency_key', None)
        if key and hasattr(response, 'data'):
            endpoint = request.path
            status_code = response.status_code
            if 200 <= status_code < 300:
                # Success → store for replay
                IdempotencyService.complete(
                    key=key, user=request.user, endpoint=endpoint,
                    response_status=status_code,
                    response_body=response.data,
                )
            else:
                # 4xx or 5xx → nothing was created; release so the
                # client can retry (with a fixed payload for 4xx).
                IdempotencyService.release(
                    key=key, user=request.user, endpoint=endpoint)

        return super().finalize_response(request, response, *args, **kwargs)