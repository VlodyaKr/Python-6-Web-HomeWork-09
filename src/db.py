from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import configparser
import pathlib

# f'postgresql://username:password@domain_name:port/database_name'

file_config = pathlib.Path(__file__).parent.parent.joinpath('config.ini')
config = configparser.ConfigParser()
config.read(file_config)

username = config.get('DB', 'user')
password = config.get('DB', 'password')
domain_name = config.get('DB', 'domain')
database_name = config.get('DB', 'db_name')

url = f'postgresql://{username}:{password}@{domain_name}:5432/{database_name}'

Base = declarative_base()
engine = create_engine(url, echo=False, pool_size=5)

DBSession = sessionmaker(bind=engine)
session = DBSession()
