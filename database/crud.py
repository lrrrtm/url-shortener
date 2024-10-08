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


def add_new_link(full_url: str, short_url: str) -> ShortLink:
    with get_session() as session:
        data = ShortLink(
            full_url=full_url,
            short_url=short_url
        )
        session.add(data)
        session.commit()
        return data


def get_existing_link(full_url: str) -> ShortLink:
    with get_session() as session:
        return session.query(ShortLink).filter(ShortLink.full_url == full_url).first()


def get_full_link_by_short_code(short_code: str):
    with get_session() as session:
        return session.query(ShortLink).filter(ShortLink.short_url == short_code).first()
