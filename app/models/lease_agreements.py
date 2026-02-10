from app import mongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta

class LeaseAgreement:
    collection = mongo.db.LeaseAgreement


    @classmethod
    def calculate_end_date(cls, start_date, lease_term):
        end_date = start_date + timedelta(days=lease_term)
        return end_date


    @classmethod
    def get_by_application_id(cls, application_id):
        """
        Get lease agreement by application ID
        
        Args:
            application_id (str): Application ID
            
        Returns:
            dict: Lease agreement document or None if not found
        """
        if not application_id:
            return None
        
        if not isinstance(application_id, ObjectId):
            try:
                application_id = ObjectId(application_id)
            except:
                return None
        
        lease = cls.collection.find_one({"application_id": str(application_id)})
        return lease
    
    @classmethod
    def calculate_security_deposit(cls, monthly_rent):
        return monthly_rent * 2
    
    @classmethod
    def create(cls, data):
        """
        Create a new lease agreement
        
        Args:
            data (dict): Lease agreement data including tenant_id, apartment_id, start_date, end_date, etc.
            
        Returns:
            str: ID of the newly created lease agreement
        """
        result = cls.collection.insert_one(data)
        print(result)
        lease_id = str(result.inserted_id)
        print("Lease ID:", lease_id)
        return lease_id
    
    @classmethod
    def get_by_id(cls, lease_id):
        """
        Get a lease agreement by ID
        
        Args:
            lease_id (str): Lease agreement ID
            
        Returns:
            dict: Lease agreement document or None if not found
        """
        if not lease_id:
            return None
        
        if not isinstance(lease_id, ObjectId):
            try:
                lease_id = ObjectId(lease_id)
            except:
                return None
        
        lease = cls.collection.find_one({"_id": lease_id})
        return lease
    
    @classmethod
    def get_by_tenant_id(cls, tenant_id):
        """
        Get all lease agreements for a tenant
        
        Args:
            tenant_id (str): Tenant ID
            
        Returns:
            list: List of lease agreement documents
        """
        if not tenant_id:
            return []
        
        leases = list(cls.collection.find({"tenant_id": tenant_id}))
        return leases
    
    @classmethod
    def get_by_apartment_id(cls, apartment_id):
        """
        Get all lease agreements for an apartment
        
        Args:
            apartment_id (str): Apartment ID
            
        Returns:
            list: List of lease agreement documents
        """
        if not apartment_id:
            return []
        
        leases = list(cls.collection.find({"apartment_id": apartment_id}))
        return leases
    
    @classmethod
    def get_active_by_apartment_id(cls, apartment_id):
        """
        Get active lease agreement for an apartment
        
        Args:
            apartment_id (str): Apartment ID
            
        Returns:
            dict: Active lease agreement document or None if not found
        """
        if not apartment_id:
            return None
        
        lease = cls.collection.find_one({
            "apartment_id": apartment_id,
            "lease_status": "active"
        })
        return lease
    
    @classmethod
    def update(cls, lease_id, data):
        """
        Update a lease agreement
        
        Args:
            lease_id (str): Lease agreement ID
            data (dict): Updated lease agreement data
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if not lease_id:
            return False
        
        if not isinstance(lease_id, ObjectId):
            try:
                lease_id = ObjectId(lease_id)
            except:
                return False
        
        result = cls.collection.update_one(
            {"_id": lease_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    @classmethod
    def delete(cls, lease_id):
        """
        Delete a lease agreement
        
        Args:
            lease_id (str): Lease agreement ID
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not lease_id:
            return False
        
        if not isinstance(lease_id, ObjectId):
            try:
                lease_id = ObjectId(lease_id)
            except:
                return False
        
        result = cls.collection.delete_one({"_id": lease_id})
        return result.deleted_count > 0
    
    @classmethod
    def get_expiring_leases(cls, days=30):
        """
        Get leases that are expiring within the specified number of days
        
        Args:
            days (int): Number of days from now
            
        Returns:
            list: List of expiring lease agreement documents
        """
        from datetime import datetime, timedelta
        
        # Calculate the date range for expiring leases
        today = datetime.now()
        expiry_date = today + timedelta(days=days)
        
        # Find leases expiring within the date range and with active status
        expiring_leases = list(cls.collection.find({
            "end_date": {
                "$gte": today,
                "$lte": expiry_date
            },
            "lease_status": "active"
        }))
        
        return expiring_leases

    @classmethod
    def find_one(cls, query):
        """Find a single lease agreement matching the query"""
        return cls.collection.find_one(query)

    @classmethod
    def update_status(cls, lease_id, status):
        """
        Update the status of a lease agreement
        
        Args:
            lease_id (str): Lease agreement ID
            status (str): New status value
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if not lease_id:
            return False
        
        try:
            if not isinstance(lease_id, ObjectId):
                lease_id = ObjectId(lease_id)
                
            result = cls.collection.update_one(
                {"_id": lease_id},
                {"$set": {"status": status}}
            )
            return result.acknowledged
        except Exception as e:
            print(f"Error updating lease status: {e}")
            return False
