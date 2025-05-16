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


class Run(tornado.web.RequestHandler):
    """
    Use the compress_image_from_bytes method of ImageCompressor
    """

    image_compressor = ImageCompressor()

    def get(self):
        self.set_status(404)
        self.write("404 : Please use POST")

    @tornado.gen.coroutine
    def post(self):
        start_time = time.time()

        try:
            img, img_body, img_name, img_content_type = self._get_image_from_request()
            if img is None:
                self.set_status(400)
                self.finish(json.dumps({'code': 400, 'msg': 'No parameters provided'}, cls=NpEncoder))
                return

            quality = int(self.get_argument('quality', default=80))
            webp = bool(self.get_argument('webp', default=''))
            webp_quality = int(self.get_argument('webp_quality', default=100))
            
            target_size = self.get_argument('target_size', default=None)
            target_size = int(target_size) if target_size else None
            
            min_size = self.get_argument('min_size', default=None)
            max_size = self.get_argument('max_size', default=None)
            
            size_range = None
            if min_size is not None and max_size is not None:
                min_size = int(min_size)
                max_size = int(max_size)
                size_range = (min_size, max_size)
            
            img_format = img.format if not webp else 'webp'

            if img_format not in ['JPEG', 'PNG', 'webp']:
                raise ValueError(f"Unsupported image format: {img_format}")

            compressed_img = Run.image_compressor.compress_image_from_bytes(
                img_body, 
                quality, 
                img.format, 
                webp=webp,
                target_size=target_size,
                size_range=size_range,
                webp_quality=webp_quality
            )

            # Set response header information
            self._set_response_headers(img_format, len(compressed_img))
            self.write(compressed_img)
        except Exception as e:
            self.set_status(500)
            self.write(f"An error occurred: {str(e)}")
            logger.error(f"Error during processing: {e}", exc_info=True)
        finally:
            self._log_request(start_time, img_name, img_content_type)
            self.finish()

    def _get_image_from_request(self):
        img_up = self.request.files.get('file', None)
        img_b64 = self.get_argument('img', None)

        if img_up is not None and len(img_up) > 0:
            img_up = img_up[0]
            return Image.open(BytesIO(img_up.body)), img_up.body, img_up.filename, img_up.content_type
        elif img_b64 is not None:
            img_data = base64.b64decode(img_b64)
            return Image.open(BytesIO(img_data)), img_data, None, None
        return None, None, None, None

    def _set_response_headers(self, img_format, content_length):
        self.set_header('Content-Type', f'image/{img_format.lower()}')
        self.set_header('Content-Disposition', f'attachment; filename="compressed_image.{img_format.lower()}"')
        self.set_header('Content-Length', str(content_length))

    def _log_request(self, start_time, img_name, img_content_type):
        end_time = time.time()
        log_info = {
            'ip': self.request.remote_ip,
            'img_name': img_name,
            'img_content_type': img_content_type,
            'time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            'elapsed_time': round(end_time - start_time, 2)
        }
        logger.info(json.dumps(log_info))
