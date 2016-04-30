from __future__ import print_function

from json import loads
import operator

from iris import load_cube
from tornado.ioloop import IOLoop
from tornado.web import Application, RequestHandler


PATH_FMT = 'sample_data/{}.2098.pp'


class CoverageHandler(RequestHandler):
    def _as_html(self, cube):
        self.write('<html><body><pre>')
        self.write(str(cube))
        self.write('</pre></body></html>')

    def _as_json(self, cube):
        def coord_json(name):
            p = cube.coord(name).points
            p = ', '.join([str(v) for v in p])
            return p

        self.set_header('Content-Type', 'application/prs.coverage+json')
        self.render('grid.json', x=coord_json('longitude'),
                    y=coord_json('latitude'),
                    # TODO: Format time as readable string
                    t=coord_json('time'))

    def _converter(self):
        headers = self.request.headers
        accepts = headers['Accept'].split(';')[0].split(',')
        converters = {
            'text/html': self._as_html,
            'application/prs.coverage+json': self._as_json
        }
        for accept in accepts:
            converter = converters.get(accept)
            if converter is not None:
                break
        if converter is None:
            raise RuntimeError('Unsupported content types: {}'.format(accepts))
        return converter


class FileHandler(CoverageHandler):
    def get(self, scenario):
        converter = self._converter()
        cube = load_cube(PATH_FMT.format(scenario))
        # Set Content-Location to format-specific URL?
        converter(cube)


class ExpressionHandler(CoverageHandler):
    OPERATORS = {
        '+': operator.add,
        '-': operator.sub
    }
    
    def _cube_from_url(self, url):
        # TODO: The essence of this mapping should be shared with the
        # FileHandler.
        scenario = url.split('/')[-1]
        air_temp = load_cube(PATH_FMT.format(scenario))
        return air_temp

    def _eval(self, expression):
        op = self.OPERATORS[expression['operation']]
        args = map(self._cube_from_url, expression['args'])
        return op(*args)

    def post(self):
        converter = self._converter()
        expression = loads(self.request.body)
        result = self._eval(expression)
        converter(result)


def make_app():
    return Application([
        (r'/scenario/(\w+)', FileHandler),
        (r'/expression', ExpressionHandler),
    ])


if __name__ == '__main__':
    app = make_app()
    app.listen(8888)
    IOLoop.current().start()
