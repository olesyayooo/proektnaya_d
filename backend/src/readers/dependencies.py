from typing import Annotated
from fastapi import Depends
from src.readers.repository import ReadersRepository
from src.readers.service import ReadersService


def get_readers_repository():
    return ReadersRepository()


def get_readers_service(readers_repo: ReadersRepository = Depends(get_readers_repository)):
    return ReadersService(readers_repo)


ReadersServiceDep = Annotated[ReadersService, Depends(get_readers_service)]
