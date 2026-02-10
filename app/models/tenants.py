from app import mongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId, errors

class Tenant:
    collection = mongo.db.tenants

    @classmethod
    def create(cls, data):
        # Set default status to active if not provided
        if 'status' not in data:
            data['status'] = 'active'
        return cls.collection.insert_one(data)


    @classmethod
    def get_by_id(cls, tenant_id):
        return cls.collection.find_one({"_id": ObjectId(tenant_id)})

    @classmethod
    def get_by_email(cls, email):
        return cls.collection.find_one({"email": email})

    @classmethod
    def check_password(cls, tenant, password):
        return check_password_hash(tenant["password"], password)

    @classmethod
    def exists_by_email(cls, email):
        return cls.collection.find_one({"email": email}) is not None

    @classmethod
    def get_tenant_name_by_id(cls, tenant_id):
        try:
            tenant = cls.collection.find_one({"_id": ObjectId(tenant_id)})  
            return tenant['name'] if tenant else None
        except errors.PyMongoError as e: 
            return None

    @classmethod
    def get_tenant_by_id(cls, tenant_id):
        try:
            tenant = cls.collection.find_one({"_id": ObjectId(tenant_id)})  
            return tenant
        except errors.PyMongoError as e: 
            return None
    @classmethod
    def get_all(cls):
        return cls.collection.find({})
    
    @classmethod
    def find_all(cls):
        return cls.collection.find({})
    
    
    @classmethod
    def count(cls):
        return cls.collection.count_documents({})
        
    @classmethod
    def update_status(cls, tenant_id, status):
        """Update the status of a tenant (active/inactive)"""
        return cls.collection.update_one(
            {"_id": ObjectId(tenant_id)},
            {"$set": {"status": status}}
        )
        
    @classmethod
    def get_by_community(cls, community_id):
        """Get all tenants in a specific community"""
        return list(cls.collection.find({"community_id": community_id}))
        
    @classmethod
    def get_by_status(cls, status):
        """Get all tenants with a specific status"""
        return list(cls.collection.find({"status": status}))
        
    @classmethod
    def get_by_role(cls, role):
        """Get all tenants with a specific role"""
        return list(cls.collection.find({"role": role}))
        
    @classmethod
    def get_filtered(cls, filters=None):
        """Get tenants with applied filters
        
        Args:
            filters (dict): Dictionary of filters to apply
                - community_id: Filter by community
                - status: Filter by status (active/inactive)
                - role: Filter by role
        """
        query = {}
        if filters:
            if 'community_id' in filters and filters['community_id']:
                query['community_id'] = filters['community_id']
            if 'status' in filters and filters['status']:
                query['status'] = filters['status']
            if 'role' in filters and filters['role']:
                query['role'] = filters['role']
                
        return list(cls.collection.find(query))