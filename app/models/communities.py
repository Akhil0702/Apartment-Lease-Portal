from app import mongo
from bson import ObjectId
from datetime import datetime

class Community:
    collection = mongo.db.communities

    @classmethod
    def get_all(cls):
        return list(cls.collection.find({}))

    @classmethod
    def create(cls, data):
        result = cls.collection.insert_one(data)
        community_id = str(result.inserted_id)
        return community_id

    @classmethod
    def get_by_id(cls, id):
        product_id = ObjectId(id)
        community = cls.collection.find_one({"_id": product_id})
        return community

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
    def count(cls):
        return cls.collection.count_documents({})
