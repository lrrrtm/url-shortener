from sqlalchemy import Column, Integer, DateTime, BigInteger, VARCHAR, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class ShortLink(Base):
    __tablename__ = 'short_links'

    id = Column(BigInteger, primary_key=True, index=True, nullable=False)
    full_url = Column(Text, unique=True, index=True, nullable=False)
    short_url = Column(VARCHAR(50), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ttl = Column(Integer, default=600)
