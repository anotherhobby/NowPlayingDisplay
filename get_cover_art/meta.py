class Meta:
    # a simple class called Meta with the same attributes as the MetaAudio class
    # mocking over the MetaAudio that was used in the original code
    def __init__(self, artist, album, title):
        self.artist = artist
        self.album = album
        self.title = title