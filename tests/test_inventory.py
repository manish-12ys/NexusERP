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
        "source_inventory_id": inv.id,
        "quantity": 10.0,
        "to_warehouse": "POS Warehouse",
        "to_location": "Register Drawer 1"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert inv.on_hand_qty == 25.0
    
    new_inv = Inventory.query.filter_by(
        product_id=prod.id,
        warehouse="POS Warehouse",
        location="Register Drawer 1"
    ).first()
    assert new_inv is not None
    assert new_inv.on_hand_qty == 10.0
    
    # Verify Stock Ledger Movement for Transfer
    transfer_ledger = StockLedger.query.filter_by(product_id=prod.id, movement_type="transfer_out").first()
    assert transfer_ledger is not None
    assert "transfer to pos warehouse" in transfer_ledger.notes.lower()


def test_warehouse_replenishment_logic_and_routes(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.product import Product
    from app.models.inventory import Inventory
    from app.services.inventory.inventory_service import InventoryService

    # Setup user
    role = Role.query.filter_by(name="Inventory Manager").first()
    user = User(username="wh_test", email="wh_test@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    # Create product with safety stock = 10
    prod = Product(name="Warehouse Bolt", sku="RAW-WHB-001", safety_stock=10.0, is_active=True)
    db.session.add(prod)
    db.session.flush()

    # Create low stock inventory in Main:Phase 1 (on hand = 2)
    inv_low = Inventory(product_id=prod.id, warehouse="Main", location="Phase 1", on_hand_qty=2.0)
    # Create surplus inventory in Main:Phase 2 (on hand = 25, free to use = 25)
    inv_surplus = Inventory(product_id=prod.id, warehouse="Main", location="Phase 2", on_hand_qty=25.0)
    # Create inventory in another warehouse to test cross-warehouse boundary
    inv_other_wh = Inventory(product_id=prod.id, warehouse="OtherWh", location="Phase 1", on_hand_qty=50.0)

    db.session.add_all([inv_low, inv_surplus, inv_other_wh])
    db.session.commit()

    # Test static recommendation method
    recs = InventoryService.get_inter_location_replenishment_recommendations()
    assert len(recs) == 1
    rec = recs[0]
    assert rec["product_id"] == prod.id
    assert rec["warehouse"] == "Main"
    assert rec["from_location"] == "Phase 2"
    assert rec["to_location"] == "Phase 1"
    # Deficit is 10 - 2 = 8. Surplus is 25 - 10 = 15. Suggested qty should be min(8, 15) = 8.
    assert rec["quantity"] == 8.0

    client.post("/auth/login", data={"username": "wh_test", "password": "pass123"})

    # Test Warehouse View Endpoint
    response = client.get("/inventory/warehouses")
    assert response.status_code == 200
    assert b"Warehouse Management" in response.data
    assert b"Main" in response.data
    assert b"OtherWh" in response.data
    assert b"Phase 1" in response.data
    assert b"Phase 2" in response.data

    # Test Replenishment POST Endpoint
    response = client.post("/inventory/warehouses/replenish", data={
        "product_id": prod.id,
        "warehouse": "Main",
        "from_location": "Phase 2",
        "to_location": "Phase 1",
        "quantity": 8.0
    }, follow_redirects=True)

    assert response.status_code == 200
    # Verify stock was successfully transferred
    assert inv_low.on_hand_qty == 10.0
    assert inv_surplus.on_hand_qty == 17.0


