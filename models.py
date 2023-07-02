from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Bot(Base):
    __tablename__ = 'bots'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    channel_id = Column(Integer, nullable=False)
    tones = Column(Text, nullable=False)
    keywords = Column(Text, nullable=False)
    template_id = Column(Integer, ForeignKey('templates.id'), nullable=False)
    frequency = Column(String(255), nullable=False)
    start_from = Column(Date, nullable=False)
    owner_slack_id = Column(String(255), nullable=False)


class Template(Base):
    __tablename__ = 'templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    owner_slack_id = Column(String(255), nullable=False)
