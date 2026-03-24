def _first_forwarded_value(value):
    if not value:
        return ''
    return value.split(',', 1)[0].strip()


def _request_origin(request):
    forwarded_host = _first_forwarded_value(request.META.get('HTTP_X_FORWARDED_HOST'))
    host = forwarded_host or request.get_host()

    forwarded_proto = _first_forwarded_value(request.META.get('HTTP_X_FORWARDED_PROTO'))
    scheme = forwarded_proto or ('https' if request.is_secure() else 'http')

    return f'{scheme}://{host}'.rstrip('/')


def public_urls(request):
    request_origin = _request_origin(request)

    return {
        'public_app_base_url': request_origin,
        'public_api_base_url': request_origin,
    }
