def test_stock_view(client, db):
    from app.models.user import User
    from app.models.role import Role
    role = Role.query.filter_by(name="Inventory Manager").first()
    user = User(username="test", email="test@test.com", role_id=role.id)
    user.set_password("test")
    db.session.add(user)
    db.session.commit()
    client.post("/auth/login", data={"username": "test", "password": "test"})
    response = client.get("/inventory/")
    assert response.status_code == 200


def test_product_creation_and_details(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.category import Category
    from app.models.product import Product
    from app.models.inventory import Inventory
    
    # Setup inventory manager user
    role = Role.query.filter_by(name="Inventory Manager").first()
    user = User(username="inv_mgr", email="inv_mgr@test.com", role_id=role.id)
    user.set_password("mgrpass")
    db.session.add(user)
    
    # Create category for form choices
    cat = Category(name="Test Materials")
    db.session.add(cat)
    db.session.commit()
    
    client.post("/auth/login", data={"username": "inv_mgr", "password": "mgrpass"})
    
    # Create product via form POST
    response = client.post("/products/create", data={
        "name": "New Brass Bolt",
        "sku": "RAW-BRS-001",
        "barcode": "987654321",
        "category_id": cat.id,
        "product_type": "raw_material",
        "unit_of_measure": "pcs",
        "description": "Premium brass bolt",
        "cost_price": 50.0,
        "sales_price": 85.0,
        "tax_percent": 18.0,
        "reorder_level": 100,
        "safety_stock": 25,
        "procurement_type": "mts",
        "lead_time_days": 3,
        "is_active": True
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify product was created and associated inventory record was initialized
    prod = Product.query.filter_by(name="New Brass Bolt").first()
    assert prod is not None
    assert prod.inventory is not None
    assert prod.inventory.on_hand_qty == 0.0
    assert prod.inventory.reserved_qty == 0.0
    
    # Verify details page loads successfully
    response = client.get(f"/products/{prod.id}")
    assert response.status_code == 200
    assert b"New Brass Bolt" in response.data
    assert prod.sku.encode() in response.data
    assert b"Free To Use" in response.data


def test_stock_adjustments_and_transfers(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.product import Product
    from app.models.inventory import Inventory
    from app.models.stock_ledger import StockLedger
    
    # Setup user
    role = Role.query.filter_by(name="Inventory Manager").first()
    user = User(username="inv_test", email="inv_test@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)
    
    # Create product & initial inventory
    prod = Product(name="Test Gear", sku="RAW-GER-001", is_active=True)
    db.session.add(prod)
    db.session.flush()
    
    inv = Inventory(product_id=prod.id, on_hand_qty=20.0, reserved_qty=5.0)
    db.session.add(inv)
    db.session.commit()
    
    client.post("/auth/login", data={"username": "inv_test", "password": "pass123"})
    
    # Test Stock Adjustment Route
    response = client.post("/inventory/adjust", data={
        "product_id": prod.id,
        "quantity": 15.0,
        "reason": "Adjustment Test Notes"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert inv.on_hand_qty == 35.0
    
    # Verify Stock Ledger Entry
    ledger = StockLedger.query.filter_by(product_id=prod.id, movement_type="adjustment").first()
    assert ledger is not None
    assert ledger.quantity == 15.0
    assert ledger.notes == "Adjustment Test Notes"
    
    # Test Stock Transfer Route
    response = client.post("/inventory/transfer", data={
        "product_id": prod.id,
        "quantity": 10.0,
        "to_warehouse": "POS Warehouse",
        "to_location": "Register Drawer 1"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert inv.warehouse == "POS Warehouse"
    assert inv.location == "Register Drawer 1"
    
    # Verify Stock Ledger Movement for Transfer
    transfer_ledger = StockLedger.query.filter_by(product_id=prod.id, movement_type="transfer").first()
    assert transfer_ledger is not None
    assert "Transferred" in transfer_ledger.notes
    assert "POS Warehouse" in transfer_ledger.notes
