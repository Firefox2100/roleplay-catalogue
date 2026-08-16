from io import BytesIO

import pytest
from PIL import Image

from roleplay_catalogue.routers.images import convert_to_clean_png


def test_source_image_is_reencoded_as_clean_png() -> None:
    source = BytesIO()
    Image.new('RGB', (12, 8), '#6d3bc1').save(source, format='JPEG', comment=b'remove me')

    png, width, height = convert_to_clean_png(source.getvalue())

    assert png.startswith(b'\x89PNG\r\n\x1a\n')
    assert (width, height) == (12, 8)
    with Image.open(BytesIO(png)) as cleaned:
        assert cleaned.format == 'PNG'
        assert 'comment' not in cleaned.info


def test_non_image_is_rejected() -> None:
    with pytest.raises(ValueError, match='supported image'):
        convert_to_clean_png(b'not an image')


def test_clean_png_hash_is_independent_of_source_metadata() -> None:
    first = BytesIO()
    second = BytesIO()
    image = Image.new('RGB', (5, 5), 'purple')
    image.save(first, format='PNG')
    image.save(second, format='PNG', comment='embedded card or other metadata')

    first_cleaned, _, _ = convert_to_clean_png(first.getvalue())
    second_cleaned, _, _ = convert_to_clean_png(second.getvalue())

    assert first_cleaned == second_cleaned
