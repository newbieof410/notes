class Middleware:

    def __init__(self, app):
        self.status = None
        self.headers = None
        self.app = app

    def my_start_response(self, status, headers):
        self.status = status
        self.headers = headers

    def __call__(self, environ, start_response):

        response_body = [b'Upper middleware:<br/>']
        content_len = len(response_body[0])

        for data in self.app(environ, self.my_start_response):
            response_body.append(data.upper())

        response_headers = []

        for header, value in self.headers:
            if header == 'Content-Length':
                value = str(int(value) + content_len)
            response_headers.append((header, value))

        start_response(self.status, response_headers)

        return response_body


@Middleware
def application(environ, start_response):
    response_body = '{}: {}'.format('request method',
                                    environ.get('REQUEST_METHOD'))

    status = '200 OK'
    response_headers = [
        ('Content-Type', 'text/html'),
        ('Content-Length', str(len(response_body)))
    ]
    start_response(status, response_headers)

    return [response_body.encode('utf-8')]
