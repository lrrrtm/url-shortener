from os import getenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from database.models import Base

load_dotenv()

DATABASE_URL = f"mysql+mysqlconnector://{getenv('DB_USER')}:{getenv('DB_PASSWORD')}@{getenv('DB_HOST')}:{getenv('DB_PORT')}/{getenv('DB_NAME')}"
engine = create_engine(DATABASE_URL, echo=True)

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
