from app import create_app, db
from app.models import User
from app.utils.security import hash_password

def init_database():
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create admin user if doesn't exist
        if not User.query.filter_by(role='admin').first():
            admin = User(
                username='admin', 
                password_hash=hash_password('admin123'), 
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: username='admin', password='admin123'")
        
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()