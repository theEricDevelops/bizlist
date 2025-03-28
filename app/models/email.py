from models import Base, generate_uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
import datetime

class EmailMessage(Base):
    __tablename__ = "emails"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    recipient = Column(String(255), unique=False, nullable=False)
    sender = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(String, nullable=False)
    created = Column(DateTime, default=datetime.datetime.now)
    sent = Column(DateTime)
    status = Column(String(50), nullable=False)
    events = Column(String, nullable=True)