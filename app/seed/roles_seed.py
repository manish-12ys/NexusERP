from app.extensions import db
from app.models.role import Role
from app.models.permission import Permission


def seed_roles_and_permissions():
    permissions_data = [
        ("Manage Users", "manage_users", "auth"),
        ("View Products", "view_products", "products"),
        ("Create Products", "create_products", "products"),
        ("Edit Products", "edit_products", "products"),
        ("Delete Products", "delete_products", "products"),
        ("View Inventory", "view_inventory", "inventory"),
        ("Adjust Inventory", "adjust_inventory", "inventory"),
        ("View Sales", "view_sales", "sales"),
        ("Create Sales", "create_sales", "sales"),
        ("Confirm Sales", "confirm_sales", "sales"),
        ("Deliver Sales", "deliver_sales", "sales"),
        ("View Purchases", "view_purchases", "purchase"),
        ("Create Purchases", "create_purchases", "purchase"),
        ("Confirm Purchases", "confirm_purchases", "purchase"),
        ("Receive Purchases", "receive_purchases", "purchase"),
        ("View BOM", "view_bom", "bom"),
        ("Create BOM", "create_bom", "bom"),
        ("View Manufacturing", "view_manufacturing", "manufacturing"),
        ("Create Manufacturing", "create_manufacturing", "manufacturing"),
        ("View Reports", "view_reports", "reports"),
        ("View Audit Logs", "view_audit", "audit"),
        ("Run Procurement", "run_procurement", "procurement"),
        ("View POS", "view_pos", "pos"),
        ("Create POS", "create_pos", "pos"),
    ]
    for name, codename, module in permissions_data:
        if not Permission.query.filter_by(codename=codename).first():
            db.session.add(Permission(name=name, codename=codename, module=module))
    db.session.flush()

    roles_permissions_map = {
        "Admin": [
            "manage_users", "view_reports", "view_audit"
        ],
        "Sales User": [
            "view_sales", "create_sales", "confirm_sales", "deliver_sales",
            "view_products", "view_inventory"
        ],
        "Purchase User": [
            "view_purchases", "create_purchases", "confirm_purchases", "receive_purchases",
            "view_products", "view_inventory"
        ],
        "Manufacturing User": [
            "view_bom", "create_bom", "view_manufacturing", "create_manufacturing",
            "view_products", "view_inventory"
        ],
        "Inventory Manager": [
            "view_products", "create_products", "edit_products", "delete_products",
            "view_inventory", "adjust_inventory", "view_audit", "run_procurement"
        ],
        "Business Owner": [
            "view_reports", "view_sales", "view_purchases", "view_inventory",
            "view_products", "view_audit"
        ],
        "POS Cashier": [
            "view_pos", "create_pos", "view_products"
        ]
    }

    for role_name, allowed_codenames in roles_permissions_map.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f"{role_name} Access Role")
            db.session.add(role)
            db.session.flush()
        
        if allowed_codenames == "*":
            role.permissions = Permission.query.all()
        else:
            role.permissions = Permission.query.filter(
                Permission.codename.in_(allowed_codenames)
            ).all()

    db.session.commit()
