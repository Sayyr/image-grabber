class GrabbedImage:
    """Small data holder for a grabbed image.

    Kept for backward compatibility. With the icrawler-based engine, images are
    downloaded directly by the crawlers, so this class is now optional.
    """
    url = None
    extension = None
    base64 = None
    source = None

    def __init__(self):
        pass
