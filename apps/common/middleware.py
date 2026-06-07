from django.http import JsonResponse
from django_ratelimit.core import is_ratelimited


class GlobalRateLimitMiddleware:
    """
    Global rate limiting middleware
    Applies to all API endpoints
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only rate limit API endpoints
        if request.path.startswith('/api/'):
            limited = is_ratelimited(
                request=request,
                group='global',
                key='ip',
                rate='200/m',
                method='ALL',
                increment=True
            )

            if limited:
                return JsonResponse(
                    {
                        'status': 'error',
                        'message': 'Too many requests. Please slow down.',
                        'retry_after': '60 seconds'
                    },
                    status=429
                )

        response = self.get_response(request)
        return response