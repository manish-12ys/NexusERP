def test_location_specific_replenishment(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.product import Product
    from app.models.inventory import Inventory
    from app.models.vendor import Vendor
    from app.models.purchase_order import PurchaseOrder
    from app.models.purchase_order_line import PurchaseOrderLine
    from app.models.procurement_request import ProcurementRequest
    from app.services.procurement.procurement_engine import ProcurementEngine
    from app.services.purchase.receiving_service import ReceivingService

    # 1. Setup user
    role = Role.query.filter_by(name="Inventory Manager").first()
    user = User(username="loc_mgr", email="loc_mgr@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    # 2. Setup vendor
    vendor = Vendor(name="Supplier Beta", email="beta@supplier.com", is_active=True)
    db.session.add(vendor)
    db.session.flush()

    # 3. Create product with shortage in Phase 1
    prod = Product(
        name="Phase Sofa",
        sku="FG-SOF-P1",
        product_type="finished_goods",
        cost_price=500.0,
        reorder_level=10.0,
        safety_stock=5.0,
        is_active=True
    )
    db.session.add(prod)
    db.session.flush()

    # Inventory at Phase 1 is 2.0 (below reorder level of 10.0)
    inv_p1 = Inventory(
        product_id=prod.id,
        warehouse="Main",
        location="Phase 1",
        on_hand_qty=2.0
    )
    db.session.add(inv_p1)
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "loc_mgr", "password": "pass123"})

    # 4. Run Autopilot
    engine = ProcurementEngine()
    counts = engine.run(mode="semi")

    # We expect 1 request created (since no surplus at other locations exists)
    assert counts["requests_created"] == 1

    # Verify ProcurementRequest has target location
    req = ProcurementRequest.query.filter_by(product_id=prod.id, status="open").first()
    assert req is not None
    assert req.warehouse == "Main"
    assert req.location == "Phase 1"
    assert req.source_type == "purchase"
    assert req.po_id is not None

    # Verify PurchaseOrderLine has target location
    po = PurchaseOrder.query.get(req.po_id)
    assert po is not None
    assert po.lines.count() == 1
    line = po.lines.first()
    assert line.warehouse == "Main"
    assert line.location == "Phase 1"
    assert line.quantity == 13.0  # (reorder 10 + safety 5 - on_hand 2)

    # 5. Approve and confirm PO
    client.post(f"/procurement/approve/{req.id}", follow_redirects=True)
    assert po.status == "confirmed"

    # 6. Receive PO
    ReceivingService.receive_order(po.id, user.id)

    # 7. Verify stock is received specifically into Phase 1, NOT Main:Default!
    # Refetch inv_p1 from DB
    inv_p1_after = Inventory.query.filter_by(product_id=prod.id, warehouse="Main", location="Phase 1").first()
    assert inv_p1_after.on_hand_qty == 15.0  # (2.0 initial + 13.0 received)

    # Verify no inventory record was created at Main:Default
    inv_def = Inventory.query.filter_by(product_id=prod.id, warehouse="Main", location="Default").first()
    assert inv_def is None


def test_manufacturing_location_specific(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.product import Product
    from app.models.inventory import Inventory
    from app.models.bom import Bom
    from app.models.manufacturing_order import ManufacturingOrder
    from app.models.procurement_request import ProcurementRequest
    from app.services.procurement.procurement_engine import ProcurementEngine
    from app.services.manufacturing.production_service import ProductionService

    # 1. Setup user
    role = Role.query.filter_by(name="Inventory Manager").first()
    user = User(username="mo_mgr", email="mo_mgr@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    # 2. Setup finished goods with BOM
    prod = Product(
        name="Phase Table",
        sku="FG-TBL-P1",
        product_type="finished_goods",
        cost_price=300.0,
        reorder_level=5.0,
        is_active=True
    )
    db.session.add(prod)
    db.session.flush()

    bom = Bom(product_id=prod.id, name="BOM for Table", quantity=1, is_active=True)
    db.session.add(bom)

    # Shortage at Phase 2
    inv_p2 = Inventory(
        product_id=prod.id,
        warehouse="Main",
        location="Phase 2",
        on_hand_qty=1.0
    )
    db.session.add(inv_p2)
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "mo_mgr", "password": "pass123"})

    # 3. Run Autopilot
    engine = ProcurementEngine()
    counts = engine.run(mode="semi")

    assert counts["requests_created"] == 1

    # Verify ProcurementRequest and MO target location
    req = ProcurementRequest.query.filter_by(product_id=prod.id, status="open").first()
    assert req is not None
    assert req.warehouse == "Main"
    assert req.location == "Phase 2"
    assert req.source_type == "manufacture"
    assert req.mo_id is not None

    mo = ManufacturingOrder.query.get(req.mo_id)
    assert mo is not None
    assert mo.warehouse == "Main"
    assert mo.location == "Phase 2"
    assert mo.quantity == 4.0  # (reorder 5 - on_hand 1)

    # 4. Finish production
    prod_svc = ProductionService()
    prod_svc.finish_production(mo.id, user.id)

    # 5. Verify stock output went to Phase 2
    inv_p2_after = Inventory.query.filter_by(product_id=prod.id, warehouse="Main", location="Phase 2").first()
    assert inv_p2_after.on_hand_qty == 5.0  # (1.0 initial + 4.0 completed)
