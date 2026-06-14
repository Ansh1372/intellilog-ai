from backend.database.db import engine
from backend.models.models import Base

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")