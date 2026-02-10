from app import mongo
from bson import ObjectId
from datetime import datetime

class Apartment:
    collection = mongo.db.apartments

    @classmethod
    def get_all(cls):
        return list(cls.collection.find({}))
    
    @classmethod
    def update_availability(cls, id, apartment_data):
        id = ObjectId(id)
        result = cls.collection.update_one({"_id": id}, {"$set": apartment_data})
        return result

    @classmethod
    def create(cls, data):
        result = cls.collection.insert_one(data)
        apartment_id = str(result.inserted_id)
        return apartment_id

    @classmethod
    def get_by_id(cls, id):
        product_id = ObjectId(id)
        apartment = cls.collection.find_one({"_id": product_id})
        return apartment

    @classmethod
    def update(cls, id, data):
        id = ObjectId(id)
        result = cls.collection.update_one({"_id": id}, {"$set": data})
        return result

    @classmethod
    def delete(cls, id):
        product_id = ObjectId(id)
        return cls.collection.delete_one({"_id": product_id})

    @classmethod
    def update_status(cls, apartment_id, new_status):
        """Update the status of an apartment"""
        if not isinstance(apartment_id, ObjectId):
            apartment_id = ObjectId(apartment_id)
            
        cls.collection.update_one(
            {'_id': apartment_id},
            {'$set': {'status': new_status}}
        )

    @classmethod
    def find_one(cls, query):
        """Find a single apartment matching the query"""
        return cls.collection.find_one(query)

    @classmethod
    def count(cls):
        return cls.collection.count_documents({})
