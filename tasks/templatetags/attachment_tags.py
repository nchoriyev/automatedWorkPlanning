from django import template

register = template.Library()

_IMAGE_EXT = frozenset(
    {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "avif"}
)
_VIDEO_EXT = frozenset({"mp4", "webm", "mov", "ogg", "ogv", "m4v", "mkv"})


def _ext(filefield):
    name = getattr(filefield, "name", "") or ""
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1].lower()


@register.filter
def mtms_is_image(filefield):
    """True if FileField looks like a raster/SVG image by extension."""
    return _ext(filefield) in _IMAGE_EXT


@register.filter
def mtms_is_video(filefield):
    """True if FileField looks like video by extension."""
    return _ext(filefield) in _VIDEO_EXT
