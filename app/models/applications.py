from app import mongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson import ObjectId

class Application:
    collection = mongo.db.applications

    @classmethod
    def get_by_tenant_id(cls, tenant_id):
        return list(cls.collection.find({"tenant_id": tenant_id}))


    @classmethod
    def get_tenant_applications(cls, tenant_id):
        return list(cls.collection.find({"tenant_id": tenant_id}))


    @classmethod
    def find_one(cls, query):
        return cls.collection.find_one(query)


    @classmethod
    def get_by_id(cls, application_id):
        return cls.collection.find_one({"_id": ObjectId(application_id)})
    

    @classmethod
    def get_by_apartment_id(cls, apartment_id):
        return list(cls.collection.find({"apartment_id": apartment_id}))


    @classmethod
    def get_all(cls):
        return list(cls.collection.find({}))
    

    @classmethod
    def update(cls, application_id, data):
        return cls.collection.update_one({"_id": ObjectId(application_id)}, {"$set": data})
    
    @classmethod
    def create(cls, data):
        return cls.collection.insert_one(data)
    
    # get all pending stockout out for delivery applications
    @classmethod
    def get_all_pending_applications(cls):
        return list(cls.collection.find({"status": {"$in": ["pending", "stockout", "out_for_delivery"]}}))
    

    @classmethod
    def get_all_pending_by_tenant(cls, tenant_id):
        return list(cls.collection.find({"tenant_id": tenant_id, "status": "pending"}))
    
    @classmethod
    def get_pending_products_count_for_tenant(cls, tenant_id):
        return cls.collection.count_documents({"tenant_id": tenant_id, "status": "pending"})
    

    @classmethod
    def update_status(cls, tenant_id, application_id, status):
        return cls.collection.update_one({"_id": ObjectId(application_id), "tenant_id": tenant_id}, {"$set": {"status": status}})
    

    @classmethod
    def get_applications_for_tenant(cls, tenant_id):
        return list(cls.collection.find({"tenant_id": tenant_id}))
    

    @classmethod
    def update_status_emp(cls, application_id, status):
        return cls.collection.update_one({"application_id": application_id}, {"$set": {"status": status}})
    

    @classmethod
    def count(cls):
        return cls.collection.count_documents({})

    @classmethod
    def get_application_by_id(cls, application_id):
        # Ensure you're querying by the MongoDB ObjectId
        print("application_id", application_id)
        return cls.collection.find_one({"_id": ObjectId(application_id)})
        
    @classmethod
    def get_by_status(cls, status):
        """Get all applications with a specific status"""
        return list(cls.collection.find({"status": status}))
        
    @classmethod
    def get_filtered(cls, filters=None):
        """Get applications with applied filters
        
        Args:
            filters (dict): Dictionary of filters to apply
                - status: Filter by status (pending/approved/rejected/etc)
                - tenant_id: Filter by tenant
                - community_id: Filter by community
                - date_from: Filter by date range (start)
                - date_to: Filter by date range (end)
        """
        query = {}
        if filters:
            if 'status' in filters and filters['status']:
                query['status'] = filters['status']
            if 'tenant_id' in filters and filters['tenant_id']:
                query['tenant_id'] = filters['tenant_id']
            if 'community_id' in filters and filters['community_id']:
                query['community_id'] = filters['community_id']
            
            # Date range filtering
            date_query = {}
            if 'date_from' in filters and filters['date_from']:
                date_query['$gte'] = filters['date_from']
            if 'date_to' in filters and filters['date_to']:
                date_query['$lte'] = filters['date_to']
            
            if date_query:
                query['created_at'] = date_query
                
        return list(cls.collection.find(query))
        
    @classmethod
    def get_stats_by_timeframe(cls, timeframe='week'):
        """Get application statistics by timeframe
        
        Args:
            timeframe (str): 'day', 'week', 'month', or 'year'
        
        Returns:
            dict: Statistics about applications in the given timeframe
        """
        now = datetime.now()
        
        if timeframe == 'day':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'week':
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now - timedelta(days=30)  # Default to last 30 days
            
        # Query for applications created in the timeframe
        applications = list(cls.collection.find({
            "created_at": {"$gte": start_date}
        }))
        
        # Count by status
        status_counts = {}
        for app in applications:
            status = app.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts[status] = 1
                
        return {
            'total': len(applications),
            'by_status': status_counts,
            'timeframe': timeframe,
            'start_date': start_date,
            'end_date': now
        }
        
    @classmethod
    def get_summary_by_community(cls, community_id=None):
        """Get summary of applications by community
        
        Args:
            community_id (str, optional): Filter by community ID
        
        Returns:
            dict: Summary statistics by community
        """
        query = {}
        if community_id:
            query['community_id'] = community_id
            
        applications = list(cls.collection.find(query))
        
        # Group by community
        community_stats = {}
        for app in applications:
            comm_id = app.get('community_id', 'unknown')
            status = app.get('status', 'unknown')
            
            if comm_id not in community_stats:
                community_stats[comm_id] = {
                    'total': 0,
                    'by_status': {}
                }
                
            community_stats[comm_id]['total'] += 1
            
            if status in community_stats[comm_id]['by_status']:
                community_stats[comm_id]['by_status'][status] += 1
            else:
                community_stats[comm_id]['by_status'][status] = 1
                
        return community_stats

    @classmethod
    def update_status(cls, application_id, new_status):
        """Update the status of an application"""
        if not isinstance(application_id, ObjectId):
            application_id = ObjectId(application_id)
            
        cls.collection.update_one(
            {'_id': application_id},
            {'$set': {
                'status': new_status,
                'payment_status': 'paid' if new_status == 'completed' else 'pending'
            }}
        )
