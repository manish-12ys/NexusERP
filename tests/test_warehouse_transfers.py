def test_autopilot_transfer_recommendation(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.product import Product
    from app.models.inventory import Inventory
    from app.models.stock_transfer import StockTransfer
    from app.models.procurement_request import ProcurementRequest
    from app.services.procurement.procurement_engine import ProcurementEngine

    # 1. Setup user with run_procurement permissions
    role = Role.query.filter_by(name="Inventory Manager").first()
    user = User(username="proc_mgr", email="proc_mgr@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    # 2. Create product & locations (shortage at Phase 1, surplus at Phase 2)
    prod = Product(
        name="Phase Wood",
        sku="RAW-PWD-001",
        product_type="raw_material",
        reorder_level=20.0,
        safety_stock=10.0,
        is_active=True
    )
    db.session.add(prod)
    db.session.flush()

    dest_inv = Inventory(
        product_id=prod.id,
        warehouse="Main",
        location="Phase 1",
        on_hand_qty=0.0
    )
    source_inv = Inventory(
        product_id=prod.id,
        warehouse="Main",
        location="Phase 2",
        on_hand_qty=100.0
    )
    db.session.add(dest_inv)
    db.session.add(source_inv)
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "proc_mgr", "password": "pass123"})

    # 3. Run Autopilot Replenishment Engine in semi-auto mode
    engine = ProcurementEngine()
    counts = engine.run(mode="semi")

    # 4. Verify recommendation was generated as a Stock Transfer
    assert counts["requests_created"] == 1
    req = ProcurementRequest.query.filter_by(product_id=prod.id, status="open").first()
    assert req is not None
    assert req.source_type == "transfer"
    assert req.stock_transfer_id is not None
    
    st = StockTransfer.query.get(req.stock_transfer_id)
    assert st is not None
    assert st.status == "pending"
    assert st.quantity == 30.0  # (reorder 20 + safety 10 - free 0)
    assert st.from_location == "Phase 2"
    assert st.to_location == "Phase 1"

    # 5. Approve the suggested transfer via route
    response = client.post(f"/procurement/approve/{req.id}", follow_redirects=True)
    assert response.status_code == 200

    # 6. Verify transfer execution
    assert dest_inv.on_hand_qty == 30.0
    assert source_inv.on_hand_qty == 70.0
    assert st.status == "completed"
    assert req.status == "closed"


def test_bidirectional_warehouse_transfers(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.product import Product
    from app.models.inventory import Inventory
    from app.models.stock_transfer import StockTransfer

    # 1. Setup user with adjust_inventory permissions
    role = Role.query.filter_by(name="Inventory Manager").first()
    if not role:
        role = Role(name="Inventory Manager", permissions=["view_inventory", "adjust_inventory"])
        db.session.add(role)
        db.session.commit()
    user = User(username="inv_user", email="inv_user@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)
    db.session.commit()

    # 2. Create product & inventory records
    prod = Product(
        name="Transfer Plank",
        sku="RAW-TPL-001",
        product_type="raw_material",
        is_active=True
    )
    db.session.add(prod)
    db.session.flush()

    main_inv = Inventory(
        product_id=prod.id,
        warehouse="Main",
        location="Default",
        on_hand_qty=50.0
    )
    db.session.add(main_inv)
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "inv_user", "password": "pass123"})

    # 3. Test Transfer: Main (Default) -> Custom WH (Aisle 1)
    response = client.post("/inventory/transfer", data={
        "product_id": prod.id,
        "from_warehouse": "Main",
        "from_location": "Default",
        "to_warehouse": "Custom WH",
        "to_location": "Aisle 1",
        "quantity": 20.0
    }, follow_redirects=True)

    assert response.status_code == 200
    
    # Verify stock deducted from Main
    assert main_inv.on_hand_qty == 30.0
    
    # Verify stock added to Custom WH
    custom_inv = Inventory.query.filter_by(
        product_id=prod.id,
        warehouse="Custom WH",
        location="Aisle 1"
    ).first()
    assert custom_inv is not None
    assert custom_inv.on_hand_qty == 20.0

    # 4. Test Transfer: Custom WH (Aisle 1) -> Main (Default) [Bidirectional/Opposite Way]
    response = client.post("/inventory/transfer", data={
        "product_id": prod.id,
        "from_warehouse": "Custom WH",
        "from_location": "Aisle 1",
        "to_warehouse": "Main",
        "to_location": "Default",
        "quantity": 5.0
    }, follow_redirects=True)

    assert response.status_code == 200

    # Verify stock updated
    assert main_inv.on_hand_qty == 35.0
    assert custom_inv.on_hand_qty == 15.0

    # 5. Test validation: Insufficient stock
    response = client.post("/inventory/transfer", data={
        "product_id": prod.id,
        "from_warehouse": "Custom WH",
        "from_location": "Aisle 1",
        "to_warehouse": "Main",
        "to_location": "Default",
        "quantity": 100.0
    }, follow_redirects=True)
    
    # Verify transaction failed and no stock changed
    assert custom_inv.on_hand_qty == 15.0
    assert main_inv.on_hand_qty == 35.0

