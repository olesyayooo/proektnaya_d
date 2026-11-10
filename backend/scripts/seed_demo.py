"""Add library tables and demo data to the configured local PostgreSQL database."""
import asyncio
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect, select, text
from src.database import engine, Base
import src.models
from src.auth.models import UsersModel
from src.auth.schemas import UserRole
from src.auth.security import hash_password, verify_password
from src.books.models import BooksModel, BookCopiesModel
from src.auth.repository import AuthRepository
from sqlalchemy.ext.asyncio import AsyncSession

BOOKS = [
    ('Война и мир', 'Лев Толстой', 2018, 'АСТ'),
    ('Война и мир', 'Лев Толстой', 2023, 'Эксмо'),
    ('Анна Каренина', 'Лев Толстой', 2021, 'Азбука'),
    ('Преступление и наказание', 'Фёдор Достоевский', 2019, 'АСТ'),
    ('Преступление и наказание', 'Фёдор Достоевский', 2024, 'Эксмо'),
    ('Идиот', 'Фёдор Достоевский', 2022, 'Азбука'),
    ('Мастер и Маргарита', 'Михаил Булгаков', 2020, 'АСТ'),
    ('Мастер и Маргарита', 'Михаил Булгаков', 2025, 'Эксмо'),
    ('Евгений Онегин', 'Александр Пушкин', 2022, 'Азбука'),
    ('Отцы и дети', 'Иван Тургенев', 2023, 'АСТ'),
]


async def main():
    if engine.url.host not in {'localhost', '127.0.0.1', 'db'}:
        raise RuntimeError('Expected the local Docker database')
    print(f'Database: {engine.url.host}:{engine.url.port}/{engine.url.database}')
    async with engine.begin() as conn:
        tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
        print('Existing tables:', ', '.join(tables))
        if '--inspect' in sys.argv:
            if 'users' in tables:
                print('User columns:', await conn.run_sync(lambda c: [x['name'] for x in inspect(c).get_columns('users')]))
            return
        if 'users' in tables:
            columns = await conn.run_sync(lambda c: [x['name'] for x in inspect(c).get_columns('users')])
            if 'reader_card' not in columns:
                await conn.execute(text('ALTER TABLE users ADD COLUMN reader_card BIGINT'))
            constraints = await conn.run_sync(lambda c: inspect(c).get_unique_constraints('users'))
            if not any(x['name'] == 'uq_users_reader_card' for x in constraints):
                await conn.execute(text('ALTER TABLE users ADD CONSTRAINT uq_users_reader_card UNIQUE (reader_card)'))
        await conn.run_sync(Base.metadata.create_all)
        # Backfill existing readers with collision retry, without changing existing cards.
        await conn.execute(text('''DO $$
        DECLARE r RECORD; violated TEXT;
        BEGIN
            FOR r IN SELECT id FROM users WHERE role = 'reader' AND reader_card IS NULL LOOP
                LOOP
                    BEGIN
                        UPDATE users SET reader_card = floor(random()*9000000000+1000000000)::bigint WHERE id=r.id;
                        EXIT;
                    EXCEPTION WHEN unique_violation THEN
                        GET STACKED DIAGNOSTICS violated = CONSTRAINT_NAME;
                        IF violated <> 'uq_users_reader_card' THEN RAISE; END IF;
                    END;
                END LOOP;
            END LOOP;
        END $$'''))
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            credentials = []
            for role, name in [(UserRole.reader, 'Тестовый читатель'), (UserRole.librarian, 'Тестовый библиотекарь')]:
                email = f'{role.value}@library.test'
                if await session.scalar(select(UsersModel.id).where(UsersModel.email == email)):
                    email = f'{role.value}.{secrets.token_hex(3)}@library.test'
                password = secrets.token_urlsafe(15)
                user = UsersModel(name=name, email=email, role=role, hashed_password=hash_password(password))
                if role == UserRole.reader:
                    # Nested transaction keeps a card collision from rolling back the seed.
                    for _ in range(20):
                        try:
                            async with session.begin_nested():
                                user.reader_card = secrets.randbelow(9_000_000_000) + 1_000_000_000
                                session.add(user)
                                await session.flush()
                            break
                        except Exception as exc:
                            from sqlalchemy.exc import IntegrityError
                            if not isinstance(exc, IntegrityError) or 'uq_users_reader_card' not in str(exc):
                                raise
                    else:
                        raise RuntimeError('Unable to allocate a reader card')
                else:
                    session.add(user)
                    await session.flush()
                assert verify_password(password, user.hashed_password)
                credentials.append({'role': role.value, 'email': email, 'password': password, 'reader_card': user.reader_card})
            book_ids = []
            for title, author, year, publisher in BOOKS:
                book = BooksModel(title=title, author=author, publication_year=year, publisher=publisher)
                session.add(book)
                await session.flush()
                session.add(BookCopiesModel(book_id=book.id))
                book_ids.append(book.id)
            await session.flush()
            from src.books.service import BooksService
            from src.books.repository import BooksRepository
            from src.loans.repository import LoansRepository
            service = BooksService(BooksRepository(), LoansRepository())
            result = await service.catalog(session, 'Толстой Война', True, 0, 100)
            assert len([b for b in result['data'] if b.id in book_ids]) == 2
            stored = (await session.scalars(select(BooksModel).where(BooksModel.id.in_(book_ids)))).all()
            assert len(stored) == 10
            await session.commit()
    print('Committed: 10 books, 10 copies, 2 users; search and passwords verified.')
    print(json.dumps(credentials, ensure_ascii=False, indent=2))
    await engine.dispose()


if __name__ == '__main__':
    # Avoid logging bound SQL parameters (including password hashes).
    engine.echo = False
    asyncio.run(main())
