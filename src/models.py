from sqlalchemy import Column, Integer, String, ARRAY, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Creator(Base):
    """Creator _summary_

    Args:
        Base (_type_): _description_
    """    
    __tablename__ = "creators"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    model_count = Column(Integer)
    link = Column(String)

class Model(Base):
    """Model _summary_

    Args:
        Base (_type_): _description_
    """    
    __tablename__ = "models"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    type = Column(String)#	enum (Checkpoint, TextualInversion, Hypernetwork, AestheticGradient)
    nsfw = Column(Boolean)
    tags = Column(String) # JSON array
    triggerWords = Column(String) # JSON array
    creator_username = Column(String)
    creator_image = Column(String) #TODO: figure out key to creator table
    versions = relationship("ModelVersion", backref="model")

class ModelVersion(Base):
    """ModelVersion _summary_

    Args:
        Base (_type_): _description_
    """    
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    base_model = Column(String)
    created_at = Column(DateTime)
    download_url = Column(String)
    trained_words = Column(String) # JSON array
    parent_id = Column(Integer, ForeignKey("models.id"))
    files = relationship("ModelVersionFile", backref="model_version")
    images = relationship("ModelVersionImage", backref="model_version")

class ModelVersionFile(Base):
    """ModelVersion _summary_

    Args:
        Base (_type_): _description_
    """
    __tablename__ = "model_version_files"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    size_kb = Column(Integer)
    type = Column(String)
    format = Column(String)
    pickle_scan_result = Column(String)
    virus_scan_result = Column(String)
    scanned_at = Column(DateTime)
    parent_id = Column(Integer, ForeignKey("model_versions.id"))

class ModelVersionImage(Base):
    """ModelVersion _summary_

    Args:
        Base (_type_): _description_
    """
    __tablename__ = "model_version_images"
    id = Column(Integer, primary_key=True)
    url = Column(String)
    nsfw = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    hash = Column(String)
    meta = Column(String)
    parent_id = Column(Integer, ForeignKey("model_versions.id"))

class Tag(Base):
    """Tag _summary_

    Args:
        Base (_type_): _description_
    """    
    __tablename__ = "tags"
    name = Column(String, primary_key=True)
    model_count = Column(Integer)
    link = Column(String)
    metadata_total_items = Column(String)
    metadata_current_page = Column(String)
    metadata_page_size = Column(String)
    metadata_total_pages = Column(String)
    metadata_next_page = Column(String)
    metadata_prev_page = Column(String)
