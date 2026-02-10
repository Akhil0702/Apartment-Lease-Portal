from app import apartment
from app.routes import  admin_routes, application_routes, reporting_routes
from app.routes import payment_routes, auth_routes, apartment_routes, manager_routes, tenant_routes, admin_routes
from app.routes import community_routes
if __name__ == "__main__":
     apartment.run(host='0.0.0.0', port=5001, debug=True)

