class ParserFindTagException(Exception):
    """Exception calls when parser could not find HTML tag."""
    pass


class UnexpectedPEPStatus(Exception):
    """Exception calls when unexpected status has been found."""
    pass
