from flask import current_app
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from app import mongo
import calendar

class Payment:
    collection = mongo.db.payments

    @classmethod
    def create(cls, data):
        """Create a new payment record"""
        result = cls.collection.insert_one(data)
        return str(result.inserted_id)

    @classmethod
    def update_status(cls, tenant_id, application_id, status):
  
        return cls.collection.update_one(
            {"tenant_id": tenant_id, "application_id": application_id},
            {"$set": {"status": status}}
        ).acknowledged

    @classmethod
    def update_status_by_id(cls, payment_id, status):
        """Update payment status by payment ID"""
        return cls.collection.update_one(
            {"_id": ObjectId(payment_id)},
            {"$set": {"status": status}}
        ).acknowledged

    @classmethod
    def get_all(cls):
        """Get all payment records"""
        return list(cls.collection.find())

    @classmethod
    def get_by_id(cls, id):
        """Get a payment by ID"""
        if not id:
            return None
        try:
            return cls.collection.find_one({"_id": ObjectId(id)})
        except:
            return None

    @classmethod
    def get_by_tenant(cls, tenant_id):
        """Get all payments for a specific tenant"""
        return list(cls.collection.find({"tenant_id": tenant_id}))

    @classmethod
    def get_by_community(cls, community_id):
        """Get all payments for a specific community"""
        return list(cls.collection.find({"community_id": community_id}))

    @classmethod
    def get_by_apartment(cls, apartment_id):
        """Get all payments for a specific apartment"""
        return list(cls.collection.find({"apartment_id": apartment_id}))

    @classmethod
    def update(cls, id, data):
        """Update a payment record"""
        return cls.collection.update_one({"_id": ObjectId(id)}, {"$set": data})

    @classmethod
    def delete(cls, id):
        """Delete a payment record"""
        return cls.collection.delete_one({"_id": ObjectId(id)})

    @classmethod
    def count(cls):
        """Count all payment records"""
        return cls.collection.count_documents({})

    @classmethod
    def get_revenue_summary(cls, community_id=None, period="monthly"):
        """
        Generate a revenue summary based on the specified filters.
        
        Args:
            community_id (str): Filter by community ID (optional)
            period (str): Time period for grouping (daily, weekly, monthly, yearly)
            
        Returns:
            dict: Summary data including total revenue, payment count, and distributions
        """
        # Base query
        match_query = {}
        if community_id:
            match_query["community_id"] = community_id
        
        # Only include paid payments in revenue calculations
        match_query["status"] = "paid"
        
        # Get all payments for status distribution
        status_query = {"community_id": community_id} if community_id else {}
        all_payments = list(cls.collection.find(status_query))
        
        # Calculate status distribution
        status_distribution = {}
        for payment in all_payments:
            status = payment.get("status", "unknown")
            if status in status_distribution:
                status_distribution[status] += 1
            else:
                status_distribution[status] = 1
        
        # Get paid payments for revenue calculations
        paid_payments = list(cls.collection.find(match_query))
        
        # Calculate total revenue
        total_revenue = sum(payment.get("amount", 0) for payment in paid_payments)
        
        # Calculate average payment
        payment_count = len(paid_payments)
        average_payment = total_revenue / payment_count if payment_count > 0 else 0
        
        # Generate time series data based on period
        time_series = {}
        community_distribution = {}
        
        for payment in paid_payments:
            # Get payment date
            payment_date = payment.get("payment_date")
            if not payment_date:
                continue
                
            # Format period key based on selected period
            if period == "daily":
                period_key = payment_date.strftime("%Y-%m-%d")
            elif period == "weekly":
                # Get the week number and year
                week_num = payment_date.isocalendar()[1]
                year = payment_date.year
                period_key = f"{year}-W{week_num:02d}"
            elif period == "monthly":
                period_key = payment_date.strftime("%Y-%m")
            elif period == "yearly":
                period_key = payment_date.strftime("%Y")
            else:
                # Default to monthly
                period_key = payment_date.strftime("%Y-%m")
            
            # Add to time series
            amount = payment.get("amount", 0)
            if period_key in time_series:
                time_series[period_key]["revenue"] += amount
                time_series[period_key]["count"] += 1
            else:
                time_series[period_key] = {"revenue": amount, "count": 1}
            
            # Add to community distribution if not filtered by community
            if not community_id:
                comm_id = payment.get("community_id", "unknown")
                if comm_id in community_distribution:
                    community_distribution[comm_id]["revenue"] += amount
                    community_distribution[comm_id]["count"] += 1
                else:
                    community_distribution[comm_id] = {"revenue": amount, "count": 1}
        
        # Sort time series by period key
        sorted_time_series = {k: time_series[k] for k in sorted(time_series.keys())}
        
        # Return summary data
        return {
            "total_revenue": round(total_revenue, 2),
            "payment_count": payment_count,
            "average_payment": round(average_payment, 2),
            "status_distribution": status_distribution,
            "time_series": sorted_time_series,
            "community_distribution": community_distribution
        }

    @classmethod
    def create_lease_payment(cls, lease_id, tenant_id, apartment_id, amount, payment_method, transaction_id):
        """Create a payment record for lease initiation"""
        payment_data = {
            'lease_id': lease_id,
            'tenant_id': tenant_id,
            'apartment_id': apartment_id,
            'total_amount': amount,
            'payment_method': payment_method,
            'transaction_id': transaction_id,
            'payment_status': 'completed',
            'due_date': datetime.now().strftime("%Y-%m-%d"),
            'timestamp': datetime.now(),
            'payment_type': 'lease_initiation'
        }
        return cls.create(payment_data)

    @classmethod
    def create_rent_payment(cls, lease_id, tenant_id, apartment_id, amount, payment_method, transaction_id, due_date):
        """Create a rent payment record"""
        payment_data = {
            'lease_id': lease_id,
            'tenant_id': tenant_id,
            'apartment_id': apartment_id,
            'total_amount': amount,
            'payment_method': payment_method,
            'transaction_id': transaction_id,
            'payment_status': 'pending',
            'due_date': due_date,
            'timestamp': datetime.now(),
            'payment_type': 'rent'
        }
        return cls.create(payment_data)

    @classmethod
    def get_upcoming_rent_payments(cls, tenant_id):
        """Get upcoming rent payments for a tenant"""
        return list(cls.collection.find({
            'tenant_id': tenant_id,
            'payment_type': 'rent',
            'payment_status': 'pending',
            'due_date': {'$gte': datetime.now().strftime("%Y-%m-%d")}
        }))

    @classmethod
    def get_payment_history(cls, tenant_id):
        """Get complete payment history for a tenant"""
        return list(cls.collection.find({
            'tenant_id': tenant_id
        }).sort('timestamp', -1))

    @classmethod
    def find_one(cls, query):
        """Find a single payment record matching the query"""
        return cls.collection.find_one(query)

    @classmethod
    def update_status(cls, payment_id, new_status):
        """Update the status of a payment"""
        if not isinstance(payment_id, ObjectId):
            payment_id = ObjectId(payment_id)
            
        cls.collection.update_one(
            {'_id': payment_id},
            {'$set': {'status': new_status}}
        )