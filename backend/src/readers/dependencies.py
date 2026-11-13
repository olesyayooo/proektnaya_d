from typing import Annotated
from fastapi import Depends
from src.readers.repository import ReadersRepository
from src.readers.service import ReadersService
from src.loans.dependencies import get_loans_service
from src.loans.service import LoansService


def get_readers_repository():
    return ReadersRepository()


def get_readers_service(
    readers_repo: ReadersRepository = Depends(get_readers_repository),
    loans_service: LoansService = Depends(get_loans_service),
):
    return ReadersService(readers_repo, loans_service)


ReadersServiceDep = Annotated[ReadersService, Depends(get_readers_service)]
