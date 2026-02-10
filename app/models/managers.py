from app import mongo
from werkzeug.security import check_password_hash
from bson import ObjectId, errors

class Manager:
    collection = mongo.db.managers

    @classmethod
    def create(cls, data):
        required_fields = ['user_name', 'email', 'phone', 'password', 'first_name', 'last_name', 'dob', 'ssn', 'address', 'city', 'state', 'zipcode']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Check if username or email already exists
        if cls.exists_by_email(data['email']) or cls.exists_by_username(data['user_name']):
            raise ValueError("Username or email already exists")
        
        # Password should already be hashed by the route
        return cls.collection.insert_one(data)

    @classmethod
    def get_by_id(cls, manager_id):
        try:
            return cls.collection.find_one({"_id": ObjectId(manager_id)})
        except errors.InvalidId:
            return None

    @classmethod
    def get_by_email(cls, email):
        return cls.collection.find_one({"email": email})

    @classmethod
    def get_by_username(cls, username):
        return cls.collection.find_one({"user_name": username})

    @classmethod
    def exists_by_email(cls, email):
        return cls.collection.find_one({"email": email}) is not None

    @classmethod
    def exists_by_username(cls, username):
        return cls.collection.find_one({"user_name": username}) is not None

    @classmethod
    def verify_password(cls, manager, password):
        return check_password_hash(manager["password"], password)

    @classmethod
    def get_all(cls):
        return list(cls.collection.find({}))

    @classmethod
    def count(cls):
        return cls.collection.count_documents({})
        
    @classmethod
    def update_profile(cls, manager_id, data):
        """Update manager's profile information"""
        allowed_fields = ['user_name', 'email', 'phone']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return None

        return cls.collection.update_one(
            {"_id": ObjectId(manager_id)},
            {"$set": update_data}
        )
    
    @classmethod
    def assign_to_community(cls, manager_id, community_id):
        """Assign a manager to a specific community"""
        return cls.collection.update_one(
            {"_id": ObjectId(manager_id)},
            {"$set": {"community_id": community_id}}
        )
    
    @classmethod
    def unassign_from_community(cls, manager_id):
        """Unassign a manager from their community"""
        return cls.collection.update_one(
            {"_id": ObjectId(manager_id)},
            {"$unset": {"community_id": ""}}
        )
    
    @classmethod
    def reset_password(cls, manager_id, new_password):
        """Reset a manager's password"""
        hashed_password = generate_password_hash(new_password)
        return cls.collection.update_one(
            {"_id": ObjectId(manager_id)},
            {"$set": {"password": hashed_password}}
        )
        
    @classmethod
    def get_by_community(cls, community_id):
        """Get all managers assigned to a specific community"""
        return list(cls.collection.find({"community_id": community_id}))

    @classmethod
    def delete(cls, manager_id):
        """Delete a manager"""
        return cls.collection.delete_one({"_id": ObjectId(manager_id)})
        
    @classmethod
    def update_status(cls, manager_id, status):
        """Update a manager's status"""
        return cls.collection.update_one(
            {"_id": ObjectId(manager_id)},
            {"$set": {"status": status}}
        )