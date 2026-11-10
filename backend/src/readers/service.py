from src.readers.repository import ReadersRepository


class ReadersService:
    def __init__(self, readers_repo: ReadersRepository):
        self.readers_repo = readers_repo
