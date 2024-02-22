import os
import sys

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH)

import tornado
from backend.tools.get_host_ip import host_ip
from backend.webInterface import run
from backend.webInterface import index
from backend.tools import log
import logging

logger = logging.getLogger(log.LOGGER_ROOT_NAME + '.' + __name__)

current_path = os.path.dirname(__file__)
settings = dict(
    # debug=True,
    static_path=os.path.join(current_path, "dist/fontend")  # Static file path
)


def make_app():
    return tornado.web.Application([
        (r"/api/run/", run.Run),
        (r"/", index.Index),
        (r"/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(current_path, "dist/fontend"), "default_filename": "index.html"}),

    ], **settings)


if __name__ == "__main__":
    port = 8089
    app = make_app()
    server = tornado.httpserver.HTTPServer(app)
    # server.listen(port)
    server.bind(port)
    server.start(1)
    print(f'server is running: {host_ip()}:{port}')

    # tornado.ioloop.IOLoop.instance().start()
    tornado.ioloop.IOLoop.current().start()
