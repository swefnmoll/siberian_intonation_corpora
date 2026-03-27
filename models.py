from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from datetime import datetime

engine = create_engine('sqlite:///intonation.db', echo=True)

Base = declarative_base()

class Dictors(Base):
    __tablename__ = 'dictors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(3))
    lang = Column(Integer, ForeignKey('languages.id'))
    gender = Column(String(1))
    dob = Column(Integer)
    settlement = Column(Integer, ForeignKey('settlements.id'))
    education = Column(Integer, ForeignKey('education.id'))

class Education(Base):
    __tablename__ = 'education'
    
    id = Column(Integer, primary_key=True)
    name = Column(Text)

class Files(Base):
    __tablename__ = 'files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file = Column(Text)
    dictor = Column(Integer, ForeignKey('dictors.id'))
    type = Column(Integer, ForeignKey('types.id'))
    subtype = Column(Integer, ForeignKey('types.id'))
    text = Column(Text)
    translation = Column(Text)

class FullDialogs(Base):
    __tablename__ = 'full_dialogs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lang = Column(Integer, ForeignKey('languages.id'))
    theme = Column(Integer, ForeignKey('themes.id'))
    dictor1 = Column(Integer, ForeignKey('dictors.id'))
    dictor2 = Column(Integer, ForeignKey('dictors.id'))

class Languages(Base):
    __tablename__ = 'languages'
    
    id = Column(Integer, primary_key=True)
    lang = Column(Text)

class Settlements(Base):
    __tablename__ = 'settlements'
    
    id = Column(Integer, primary_key=True)
    settlement = Column(Text)

class Themes(Base):
    __tablename__ = 'themes'
    
    id = Column(Integer, primary_key=True)
    theme = Column(Text)

class Types(Base):
    __tablename__ = 'types'
    
    id = Column(Integer, primary_key=True)
    type = Column(Text)

class Subtypes(Base):
    __tablename__ = 'subtypes'
    
    id = Column(Integer, primary_key=True)
    subtype = Column(Text)

class GraphicsData(Base):
    __tablename__ = 'graphics_data'

    id = Column(Integer, primary_key=True)
    file = Column(Text, ForeignKey('files.file'))
    pitch = Column(Text)
    intensity = Column(Text)

Base.metadata.create_all(engine)