import os
import tornado.web
import tornado.httpserver
import tornado.ioloop
from backend.tools.get_host_ip import host_ip
from backend.webInterface import run, index
from backend.tools import log
import logging


def init_logger():
    logger = logging.getLogger(f"{log.LOGGER_ROOT_NAME}.{__name__}")
    return logger


logger = init_logger()

current_path = os.path.dirname(__file__)
settings = {
    "static_path": os.path.join(current_path, "dist/fontend")
}


def make_app():
    return tornado.web.Application([
        (r"/api/run/", run.Run),
        (r"/", index.Index),
        (r"/(.*)", tornado.web.StaticFileHandler, {
            "path": settings["static_path"],
            "default_filename": "index.html"
        })
    ], **settings)


if __name__ == "__main__":
    port = 8089
    app = make_app()
    server = tornado.httpserver.HTTPServer(app)
    server.bind(port)
    server.start(1)
    print(f'server is running: {host_ip()}:{port}')
    tornado.ioloop.IOLoop.current().start()
