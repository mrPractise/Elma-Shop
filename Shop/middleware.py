class RemoveNoindexMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.path == '/sitemap.xml':
            # Remove the x-robots-tag header for sitemap
            response.headers.pop('x-robots-tag', None)
            # Optionally, add a new header to explicitly allow indexing
            response.headers['X-Robots-Tag'] = 'index, follow'
        
        return response