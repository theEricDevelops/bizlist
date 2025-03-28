from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base, generate_uuid
import datetime

class WebSearchCache(Base):
    __tablename__ = "web_search_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    query = Column(String, nullable=False)
    results = Column(String, nullable=False)
    datetime = Column(DateTime, default=datetime.datetime.now)