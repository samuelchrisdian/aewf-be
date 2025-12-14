
import os
import jwt
import sys
from src.app import create_app
from src.app.extensions import db
from src.domain.models import User
import datetime

def generate_token(username='admin'):
    app = create_app('default')
    
    with app.app_context():
        # Ensure database exists
        db.create_all()
        
        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User '{username}' not found. Creating a new user...")
            user = User(
                username=username,
                password_hash='pbkdf2:sha256:...' # Dummy hash, not used for token generation
            )
            db.session.add(user)
            db.session.commit()
            print(f"Created user: {user.username} with ID: {user.id}")
        else:
            print(f"Found existing user: {user.username} (ID: {user.id})")
            
        # Generate Token
        try:
            payload = {
                'user_id': user.id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
            }
            token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], algorithm="HS256")
            
            # If jwt.encode returns bytes (older versions), decode to string
            if isinstance(token, bytes):
                token = token.decode('utf-8')
                
            print("\n" + "="*50)
            print("GENERATED AUTH TOKEN (Valid for 24 hours):")
            print("="*50)
            print(f"Bearer {token}")
            print("="*50 + "\n")
            print("Use this token in the 'Authorization' header for your API requests.")
            
        except Exception as e:
            print(f"Error generating token: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_token(sys.argv[1])
    else:
        generate_token()
