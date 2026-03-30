"""Wiki.js GraphQL client — smoke import (integration covers live GraphQL)."""

from wikijs_api import WikiJsGraphQL  # noqa: F401


def test_client_importable():
    assert WikiJsGraphQL is not None
