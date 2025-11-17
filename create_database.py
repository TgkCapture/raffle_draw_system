# create_database.py
from app import create_app, db
from app.models import User
from app.utils.security import hash_password
import os

def init_database():
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
            # Create admin user if doesn't exist
            if not User.query.filter_by(role='admin').first():
                admin = User(
                    username=os.environ.get('ADMIN_USERNAME', 'admin'),
                    password_hash=hash_password(os.environ.get('ADMIN_PASSWORD', 'admin123')),
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
            
            print("PostgreSQL database initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()

if __name__ == '__main__':
    init_database()