from typing import Annotated
from fastapi import Depends
from src.loans.repository import LoansRepository
from src.loans.service import LoansService


def get_loans_repository():
    return LoansRepository()


def get_loans_service(loans_repo: LoansRepository = Depends(get_loans_repository)):
    return LoansService(loans_repo)


LoansServiceDep = Annotated[LoansService, Depends(get_loans_service)]
