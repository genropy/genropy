"""Decode the primary image in a HEIC or HEIF attachment."""

from io import BytesIO
from os.path import isabs, splitext

HEIF_EXTENSIONS = ('heic', 'heif')


def is_heif_path(path):
    return bool(path) and splitext(path)[1].lower().lstrip('.') in HEIF_EXTENSIONS


def heif_storage_path(path):
    # Legacy attachment URLs use /_vol/<volume>/<file>.
    if is_heif_path(path) and ':' not in path and not isabs(path):
        return f'vol:{path}'
    return path


def read_heif_image(storage_node, preview_size=None):
    from PIL import Image
    from pillow_heif import HeifImageFile

    with storage_node.open('rb') as source, HeifImageFile(source) as image:
        if Image.MAX_IMAGE_PIXELS and image.width * image.height > Image.MAX_IMAGE_PIXELS:
            raise ValueError("HEIF image exceeds the configured pixel limit")
        if preview_size:
            image.thumbnail(preview_size)
        return image.convert('RGB')


def heif_preview_jpeg(storage_node):
    with read_heif_image(storage_node, (2560, 2560)) as image, BytesIO() as output:
        image.save(output, format='JPEG', quality=88)
        return output.getvalue()
