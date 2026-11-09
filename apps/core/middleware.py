from urllib.parse import urlparse

ATTRIBUTION_SESSION_KEY = "attribution"
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign")


class AttributionMiddleware:
    """Remember where a visitor first came from (UTM tags or external referrer) for sales reports.

    Only touches the session when there's something to record, so ordinary page views don't create sessions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET" and not request.path.startswith(("/admin/", "/static/", "/media/")):
            self._capture(request)
        return self.get_response(request)

    def _capture(self, request):
        utm = {k: request.GET.get(k, "")[:100] for k in UTM_KEYS if request.GET.get(k)}
        referrer = request.META.get("HTTP_REFERER", "")
        external = referrer and urlparse(referrer).hostname not in (request.get_host().split(":")[0], None)
        if not utm and not external:
            return
        if ATTRIBUTION_SESSION_KEY in request.session:  # first touch wins
            return
        data = dict(utm)
        if external:
            data["referrer"] = referrer[:500]
            data.setdefault("utm_source", urlparse(referrer).hostname or "")
        request.session[ATTRIBUTION_SESSION_KEY] = data
