"""Changelog data class module."""

from marshmallow import Schema, fields


class Changelog(Schema):
    """Changelog data class."""

    timestamp = fields.DateTime()
    user_id = fields.String()
    comment = fields.String()
