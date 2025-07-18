from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class KnowledgeDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'file' or 'url'
    path = db.Column(db.String(500), nullable=False)  # 文件路径或URL
    tags = db.Column(db.String(255), nullable=False)  # 逗号分隔的标签
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'path': self.path,
            'tags': self.tags.split(','),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }