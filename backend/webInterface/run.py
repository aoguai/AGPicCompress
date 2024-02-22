import base64
import json
import logging
import time
from io import BytesIO

import tornado.gen
import tornado.web
from PIL import Image

from ImageCompressor import ImageCompressor
from backend.tools import log
from backend.tools.np_encoder import NpEncoder

logger = logging.getLogger(log.LOGGER_ROOT_NAME + '.' + __name__)

image_compressor = ImageCompressor()

request_time = {}
now_time = time.strftime("%Y-%m-%d", time.localtime(time.time()))


class Run(tornado.web.RequestHandler):
    """
    Use the compress_image_from_bytes method of ImageCompressor
    """

    def get(self):
        self.set_status(404)
        self.write("404 : Please use POST")

    @tornado.gen.coroutine
    def post(self):
        start_time = time.time()

        img_up = self.request.files.get('file', None)
        img_b64 = self.get_argument('img', None)

        if img_up is not None and len(img_up) > 0:
            img_up = img_up[0]
            img_content_type = img_up.content_type
            img_body = img_up.body
            img_name = img_up.filename
            img = Image.open(BytesIO(img_body))
        elif img_b64 is not None:
            img_data = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_data))
        else:
            self.set_status(400)
            self.finish(json.dumps({'code': 400, 'msg': 'No parameters provided'}, cls=NpEncoder))
            return

        try:
            # Compress the image
            quality = int(self.get_argument('quality', default=80))
            webp = bool(self.get_argument('webp', default=''))
            img_format = img.format
            if img_format not in ['JPEG', 'PNG']:
                raise ValueError(f"Unsupported image format: {img_format}")
            compressed_img = ImageCompressor.compress_image_from_bytes(img_body, quality, img_format, webp)

            if webp:
                img_format = 'webp'

            # Set response header information
            self.set_header('Content-Type', f'image/{img_format.lower()}')
            self.set_header('Content-Disposition',
                            f'attachment; filename="compressed_image.{img_format.lower()}"')
            self.set_header('Content-Length', str(len(compressed_img)))

            self.write(compressed_img)
        except Exception as e:
            self.set_status(500)
            self.write(f"An error occurred: {str(e)}")

        finally:
            # Logging
            end_time = time.time()
            log_info = {
                'ip': self.request.remote_ip,
                'img_name': img_name if 'img_name' in locals() else None,
                'img_content_type': img_content_type if 'img_content_type' in locals() else None,
                'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                'elapsed_time': round(end_time - start_time, 2)
            }
            logger.info(json.dumps(log_info))

            # Finish the request
            self.finish()
