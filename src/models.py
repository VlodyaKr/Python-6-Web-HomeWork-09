from sqlalchemy import Column, Integer, String, ForeignKey, Date, Boolean, FetchedValue
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import relationship, column_property
from datetime import date, datetime

from src.db import Base


class Contact(Base):
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True, nullable=False)
    address = Column(String(100), nullable=True)
    birthday = Column(Date, nullable=True)
    phones = relationship('Phone', back_populates='contact')
    emails = relationship('Email', back_populates='contact')

    @hybrid_property
    def days_to_birthday(self) -> int:
        # print(self.birthday, type(self.birthday))
        if self.birthday is None:
            return -1
        this_day = date.today()
        birthday_day = date(this_day.year, self.birthday.month, self.birthday.day)
        if birthday_day < this_day:
            birthday_day = date(this_day.year + 1, self.birthday.month, self.birthday.day)
        return int((birthday_day - this_day).days)


class Phone(Base):
    __tablename__ = 'phones'
    id = Column(Integer, primary_key=True)
    phone_number = Column(String(15), unique=True, nullable=False)
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False)
    contact = relationship('Contact', back_populates='phones')


class Email(Base):
    __tablename__ = 'emails'
    id = Column(Integer, primary_key=True)
    mail = Column(String(254), unique=True, nullable=False)
    contact_id = Column(Integer, ForeignKey('contacts.id', ondelete='CASCADE'), nullable=False)
    contact = relationship('Contact', back_populates='emails')


class Note(Base):
    __tablename__ = 'notes'
    id = Column(Integer, primary_key=True)
    tags = relationship('Tag')
    text = Column(String(255), nullable=False)
    execution_date = Column(Date)
    is_done = Column(Boolean, default=False)


class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    tag = Column(String(15), nullable=False)
    note_id = Column(Integer, ForeignKey('notes.id', ondelete='CASCADE'), nullable=False)
