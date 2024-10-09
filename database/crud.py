from contextlib import contextmanager
from datetime import datetime

from database.config import Session
from database.models import ShortLink


@contextmanager
def get_session():
    session = Session()
    session.expire_on_commit = False
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def add_new_link(original_url: str, short_url_code: str, created_at: datetime) -> ShortLink:
    with get_session() as session:
        data = ShortLink(
            original_url=original_url,
            short_url=short_url_code,
            created_at=created_at
        )
        session.add(data)
        session.commit()
        return data


def renew_url_record(data: str):
    with get_session() as session:
        link = session.query(ShortLink).filter_by(original_url=data).first()
        link.created_at = datetime.now()
        session.commit()

def get_existing_record(data: str) -> ShortLink:
    with get_session() as session:
        return session.query(ShortLink).filter(ShortLink.original_url == data).first()


def get_record_by_short_code(data: str) -> ShortLink:
    with get_session() as session:
        return session.query(ShortLink).filter(ShortLink.short_url == data).first()
