from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """Strict throttle for auth endpoints - 5/minute"""
    scope = 'auth'

    def get_rate(self):
        return '5/minute'


class UploadRateThrottle(UserRateThrottle):
    """Throttle for upload endpoints - 10/minute"""
    scope = 'upload'

    def get_rate(self):
        return '10/minute'


class StrictAnonThrottle(AnonRateThrottle):
    """Strict throttle for anonymous endpoints"""
    scope = 'anon'

    def get_rate(self):
        return '30/minute'