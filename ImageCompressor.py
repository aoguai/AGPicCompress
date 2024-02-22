import os
import platform
import shutil
import subprocess
import tempfile
import time
import warnings
from io import BytesIO
from pathlib import Path

import click
import mozjpeg_lossless_optimization
from PIL import Image


class QualityInteger(click.ParamType):
    name = "QualityInteger"

    @staticmethod
    def _parse_int(value):
        try:
            return int(value)
        except ValueError:
            return None

    def convert(self, value, param, ctx):
        """
        Convert a string to an integer or an integer range.

        :param value: The value to convert.
        :type value: str
        :param param: The parameter.
        :type param: XXX
        :param ctx: The context.
        :type ctx: XXX
        :return: The converted integer or integer range.
        :rtype: int or tuple[int, int]
        """
        if value.isdigit():
            return self._parse_int(value)

        parts = value.split('-')
        if len(parts) != 2:
            raise click.BadParameter('The parameter does not conform to the format like 80-90 or 90')

        min_v = self._parse_int(parts[0])
        max_v = self._parse_int(parts[1])

        if min_v is None or max_v is None:
            raise click.BadParameter('The parameter does not conform to the format like 80-90 or 90')

        if min_v > max_v or min_v <= 0 or max_v <= 0:
            raise click.BadParameter('The parameter does not conform to the format like 80-90 or 90')

        return min_v, max_v


def generate_output_path(fp, output=None):
    """
    Generate the output path.

    :param fp: The file path.
    :type fp: Path
    :param output: The output path.
    :type output: Path or None
    :return: The output path.
    :rtype: Path
    """
    new_fp = Path(fp.parent, f"{fp.stem}_{int(time.time())}_compressed{fp.suffix}")

    if output:
        if output.is_dir():
            # If it is a directory, check if it exists, create it if it doesn't
            output.mkdir(parents=True, exist_ok=True)
            new_fp = output / new_fp.name
        elif output.exists():
            # If it is a file, check if it exists, throw an exception if it does
            raise FileExistsError(f'{output} already exists')
        else:
            new_fp = output

    return new_fp


def optimize_output_path(fp, output=None, force=False):
    """
    Optimize the output path.

    :param fp: File path.
    :type fp: Path
    :param output: Output path.
    :type output: Path
    :param force: Whether to force overwrite.
    :type force: bool
    :return: Output path.
    :rtype: Path
    """
    if force and output:
        if output.is_dir():
            output.mkdir(parents=True, exist_ok=True)
            new_fp = output / fp.name
        else:
            new_fp = output
    elif not force and output:
        new_fp = generate_output_path(fp, output)
    else:
        new_fp = generate_output_path(fp)

    return new_fp


def find_pngquant_cmd():
    """
    Find and return the executable file path of pngquant.

    :return: The executable file path of pngquant, or None if not found.
    :rtype: str or None
    """
    pngquant_cmd = shutil.which('pngquant')
    if pngquant_cmd:
        return pngquant_cmd

    exe_extension = '.exe' if platform.system() == 'Windows' else ''
    search_paths = [Path(__file__).resolve().parent,
                    Path(__file__).resolve().parent / 'ext']
    for search_path in search_paths:
        pngquant_exe_path = search_path / f'pngquant{exe_extension}'
        if pngquant_exe_path.exists():
            return str(pngquant_exe_path)

    return None


class ImageCompressor:
    def __init__(self):
        pass

    @staticmethod
    def compress_image(fp, force=False, quality=None, output=None, webp=False):
        """
        Compression function.

        :param fp: File name or directory name.
        :type fp: Path
        :param force: Whether to overwrite if a file with the same name exists.
        :type force: bool
        :param quality: Compression quality. 80-90, or 90.
        :type quality: int or tuple[int, int]
        :param output: Output path or output directory
        :type output: Path
        :param webp: Whether to convert to WebP format.
        :type webp: bool
        """

        if output:
            # Check if output is a file
            if not output.is_dir():
                # Check if the suffix is an image format
                if output.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.webp']:
                    raise ValueError('Unsupported output file format')
                # Check if the suffix is webp
                if output.suffix.lower() == '.webp':
                    webp = True
                    # Change the suffix to match the input file, and add "_2webp" to the file name to avoid errors in subsequent operations
                    output = Path(output.parent, f"{output.stem}_2webp{fp.suffix}")
                # Check if the suffix is consistent with the input file
                if output.suffix.lower() != fp.suffix.lower():
                    raise ValueError('Inconsistent output file format with input file format')

        # If fp is a directory, process all images in the directory
        if fp.is_dir():
            files = (file for file in fp.iterdir() if
                     file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg'])
            for file in files:
                ImageCompressor.compress_image(file, force, quality, output, webp)
            return

        # Continue compressing a single file
        ext = fp.suffix.lower()
        if ext == '.png':
            ImageCompressor._compress_png(fp, force, quality, output, webp)
        elif ext in ['.jpg', '.jpeg']:
            ImageCompressor._compress_jpg(fp, force, quality, output, webp)
        else:
            raise ValueError('Unsupported file format')

    @staticmethod
    def _convert_to_webp(fp):
        """
        Convert an image to WebP format.

        :param fp: Image file path.
        :type fp: Path
        :return: WebP image file path.
        :rtype: Path or None
        """
        # 判断文件是否存在
        if Path(fp).exists():
            img = Image.open(fp)
            webp_fp = Path(fp).with_suffix('.webp')
            img.save(webp_fp, 'webp')
            # 删除原始文件
            os.remove(fp)
            return webp_fp
        return None

    @staticmethod
    def _compress_png(fp, force=False, quality=None, output=None, wepb=False):
        """
        Compress PNG images and specify compression quality.

        :param fp: Path of the image file.
        :type fp: Path
        :param force: Whether to overwrite if a file with the same name exists. Defaults to False.
        :type force: bool
        :param quality: Compression quality. Defaults to None.
        :type quality: int or tuple[int, int]
        :param output: Output path.
        :type output: Path
        :param wepb: Whether to convert to WebP format.
        :type wepb: bool
        """
        new_fp = optimize_output_path(fp, output, force)

        quality_command = ''
        if quality:
            if isinstance(quality, int):
                quality_command = f'--quality {quality}'
            elif isinstance(quality, tuple):
                min_quality, max_quality = quality
                quality_command = f'--quality {min_quality}-{max_quality}'
            else:
                raise ValueError('Unsupported type for quality parameter')

        pngquant_cmd = find_pngquant_cmd()

        if not pngquant_cmd:
            raise FileNotFoundError(
                'pngquant not found. Please make sure pngquant is installed or add it to the environment variable')

        try:
            command = f'{pngquant_cmd} {fp} --skip-if-larger -f -o {new_fp} {quality_command}'
            subprocess.run(command, shell=True)
        except FileNotFoundError:
            raise FileNotFoundError(
                'pngquant not found. Please make sure pngquant is installed or add it to the environment variable')

        if not Path(new_fp).exists():
            warning_msg = f'{fp}: The compressed image file was not generated successfully. It may no longer be compressible or no longer exist'
            warnings.warn(warning_msg, Warning)
            return

        if wepb:
            ImageCompressor._convert_to_webp(new_fp)

    @staticmethod
    def _compress_jpg(fp, force=False, quality=None, output=None, wepb=False):
        """
        Compress JPG images and specify compression quality.

        :param fp: Image file path.
        :type fp: Path
        :param force: Whether to overwrite if a file with the same name already exists, default is False.
        :type force: bool
        :param quality: Compression quality, default is None.
        :type quality: int or None
        :param output: Output path.
        :type output: Path
        :param wepb: Whether to convert to WebP format.
        :type wepb: bool
        """
        # If quality is not None and is not of integer type, raise an exception
        if quality is not None and not isinstance(quality, int):
            raise ValueError('quality parameter type is not supported')

        new_fp = optimize_output_path(fp, output, force)

        # Open the image and convert it to RGB mode
        with Image.open(fp) as img:
            img = img.convert("RGB")

            # Save the image to memory
            with BytesIO() as buffer:
                # If quality parameter is not None, use the specified compression quality
                if quality:
                    img.save(buffer, format="JPEG", quality=quality)
                else:
                    img.save(buffer, format="JPEG")
                input_jpeg_bytes = buffer.getvalue()

        # Use the mozjpeg_lossless_optimization library for lossless optimization
        optimized_jpeg_bytes = mozjpeg_lossless_optimization.optimize(input_jpeg_bytes)

        # Write the optimized image to file
        with open(new_fp, "wb") as output_jpeg_file:
            output_jpeg_file.write(optimized_jpeg_bytes)

        if not Path(new_fp).exists():
            warning_msg = f'{fp}: The compressed image file was not generated successfully. It may no longer be compressible or no longer exist'
            warnings.warn(warning_msg, Warning)
            return

        if wepb:
            ImageCompressor._convert_to_webp(new_fp)

    @staticmethod
    def compress_image_from_bytes(image_bytes, quality=80, output_format='JPEG', webp=False):
        """
        Compresses image data and returns the compressed image data.

        :param image_bytes: The byte representation of the image data.
        :type image_bytes: bytes
        :param quality: The compression quality, ranging from 1 to 100.
        :type quality: int
        :param output_format: The output format of the image, default is 'JPEG'.
        :type output_format: str
        :param webp: Whether to convert to WebP format.
        :type webp: bool
        :return: The byte representation of the compressed image data.
        :rtype: bytes
        """
        # Load the image data into a PIL image object in memory
        with BytesIO(image_bytes) as img_buffer:
            img = Image.open(img_buffer)

            # Convert the image to RGB mode for compatibility with different input image formats
            img = img.convert('RGB')

            # Create a new byte stream to store the compressed image data
            output_buffer = BytesIO()

            # Compress the image based on the output format
            if output_format.upper() == 'JPEG':
                img.save(output_buffer, format=output_format, quality=quality, optimize=True)
                compressed_img_bytes = output_buffer.getvalue()
                # Use the mozjpeg_lossless_optimization library for lossless optimization
                try:
                    compressed_img_bytes = mozjpeg_lossless_optimization.optimize(compressed_img_bytes)
                    if webp:
                        # Create a new byte stream to store the converted image data
                        output_buffer = BytesIO()
                        # Read the compressed image data into Image
                        img = Image.open(BytesIO(compressed_img_bytes))
                        # Save the image as webp format in memory
                        img.save(output_buffer, format='webp')
                        compressed_img_bytes = output_buffer.getvalue()
                except Exception as e:
                    raise e
            elif output_format.upper() == 'PNG':
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_png_file_path = os.path.join(temp_dir, f'temp_{int(time.time())}.png')
                    with open(temp_png_file_path, 'wb') as temp_png_file:
                        temp_png_file.write(image_bytes)
                        temp_png_file.flush()
                        new_fp = optimize_output_path(temp_png_file.name, Path(temp_dir), False)
                        pngquant_cmd = find_pngquant_cmd()

                        if not pngquant_cmd:
                            raise FileNotFoundError('pngquant not found. Please make sure pngquant is installed or add it to the environment variables.')
                        try:
                            command = [pngquant_cmd, temp_png_file.name, '-f', '--output', new_fp, '--skip-if-larger',
                                       f'--quality={quality}']
                            subprocess.run(command)
                        except FileNotFoundError:
                            raise FileNotFoundError('pngquant not found. Please make sure pngquant is installed or add it to the environment variables.')

                        if not Path(new_fp).exists():
                            raise FileNotFoundError (f'The compressed image file was not generated successfully. It may no longer be compressible or no longer exist')

                        if webp:
                            new_fp = ImageCompressor._convert_to_webp(new_fp)

                        with open(new_fp, 'rb') as compressed_png_file:
                            compressed_img_bytes = compressed_png_file.read()

                    # Delete the temporary directory
                    shutil.rmtree(temp_dir)
            else:
                raise ValueError('Unsupported output format. Supported formats are JPEG and PNG.')

            return compressed_img_bytes

    @staticmethod
    @click.command()
    @click.argument('fp')
    @click.option(
        "--force", "-f", "--violent",
        is_flag=True,
        help="Whether to overwrite if a file with the same name exists, defaults to False."
    )
    @click.option('--quality', "-q", default="80", type=QualityInteger(),
                  help="Compression quality. 80-90, or 90, default is 80.")
    @click.option('--output', '-o', help='Output path or output directory.')
    @click.option('--webp', is_flag=True, help='Convert images to WebP format.')
    def cli_compress(fp, force=False, quality=None, output=None, webp=False):
        """
        Compress images via command line.

        :param fp: Image file path or directory path.
        :type fp: str

        :param force: Whether to overwrite if a file with the same name exists, defaults to False.
        :type force: bool

        :param quality: Compression quality. 80-90, or 90, default is 80.
        :type quality: int or tuple[int, int]

        :param output: Output path or output directory.
        :type output: str

        :param webp: Convert images to WebP format.
        :type webp: bool
        """
        if len(fp) <= 0:
            raise ValueError('The file path cannot be empty')
        else:
            fp = Path(fp)
        if len(output) <= 0:
            output = None
        else:
            output = Path(output)

        ImageCompressor.compress_image(fp, force, quality, output, webp)


if __name__ == "__main__":
    ImageCompressor.cli_compress()
    # ImageCompressor.compress_image(Path('./images/'), force=False, quality=80, output=Path('./images/'))
