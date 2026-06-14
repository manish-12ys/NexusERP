def test_procurement_page(client, db):
    from app.models.user import User
    from app.models.role import Role
    role = Role.query.filter_by(name="Inventory Manager").first()
    user = User(username="proc_test", email="proc@test.com", role_id=role.id)
    user.set_password("test")
    db.session.add(user)
    db.session.commit()
    client.post("/auth/login", data={"username": "proc_test", "password": "test"}, follow_redirects=True)
    response = client.get("/procurement/")
    assert response.status_code == 200


def test_smart_purchasing_engine(client, db):
    from app.models.category import Category
    from app.models.product import Product
    from app.models.inventory import Inventory
    from app.models.bom import Bom
    from app.models.vendor import Vendor
    from app.models.manufacturing_order import ManufacturingOrder
    from app.models.purchase_order import PurchaseOrder
    from app.models.procurement_request import ProcurementRequest
    from app.services.procurement.procurement_engine import ProcurementEngine

    # 1. Setup vendor
    vendor = Vendor(name="Supplier Alpha", email="alpha@supplier.com")
    db.session.add(vendor)
    
    # 2. Setup categories
    cat = Category(name="Test Sourcing")
    db.session.add(cat)
    db.session.flush()

    # 3. Setup product made in-house (has BOM)
    p_made = Product(
        name="Made Sofa",
        sku="FG-SOF-001",
        product_type="finished_goods",
        category_id=cat.id,
        cost_price=1000.0,
        reorder_level=5.0,
        is_active=True
    )
    db.session.add(p_made)
    db.session.flush()
    bom = Bom(product_id=p_made.id, name="BOM for Sofa", quantity=1, is_active=True)
    db.session.add(bom)
    
    # Inventory showing shortage (available 2, reorder level 5)
    inv_made = Inventory(product_id=p_made.id, on_hand_qty=2.0)
    db.session.add(inv_made)

    # 4. Setup product bought from outside (no BOM)
    p_bought = Product(
        name="Bought Leather",
        sku="RAW-LTH-001",
        product_type="raw_material",
        category_id=cat.id,
        cost_price=200.0,
        reorder_level=20.0,
        is_active=True
    )
    db.session.add(p_bought)
    db.session.flush()
    
    # Inventory showing shortage (available 5, reorder level 20)
    inv_bought = Inventory(product_id=p_bought.id, on_hand_qty=5.0)
    db.session.add(inv_bought)
    db.session.commit()

    # 5. Run the procurement engine
    engine = ProcurementEngine()
    result = engine.run()
    requests_created = result["requests_created"] if isinstance(result, dict) else result
    
    # We expect 2 requests to be created
    assert requests_created == 2

    # 6. Verify made in-house product got a Manufacturing Order (MO)
    pr_made = ProcurementRequest.query.filter_by(product_id=p_made.id).first()
    assert pr_made is not None
    assert pr_made.source_type == "manufacture"
    assert pr_made.mo_id is not None
    mo = ManufacturingOrder.query.get(pr_made.mo_id)
    assert mo is not None
    assert mo.product_id == p_made.id
    assert mo.quantity == 3.0  # (reorder 5.0 - on_hand 2.0)
    assert mo.status == "draft"

    # 7. Verify bought from outside product got a Purchase Order (PO)
    pr_bought = ProcurementRequest.query.filter_by(product_id=p_bought.id).first()
    assert pr_bought is not None
    assert pr_bought.source_type == "purchase"
    assert pr_bought.po_id is not None
    po = PurchaseOrder.query.get(pr_bought.po_id)
    assert po is not None
    assert po.vendor_id == vendor.id
    assert po.lines.count() == 1
    assert po.lines.first().product_id == p_bought.id
    assert po.lines.first().quantity == 15.0  # (reorder 20.0 - on_hand 5.0)
    assert po.status == "draft"
