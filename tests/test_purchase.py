def test_purchase_lifecycle(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.vendor import Vendor
    from app.models.product import Product
    from app.models.category import Category
    from app.models.inventory import Inventory
    from app.models.purchase_order import PurchaseOrder
    from app.models.stock_ledger import StockLedger
    from app.services.inventory.inventory_service import InventoryService

    # 1. Setup role and user
    role = Role.query.filter_by(name="Purchase User").first()
    user = User(username="purchaser", email="purchaser@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    # 2. Create vendor and category
    vendor = Vendor(name="Steel Supplier", email="steel@test.com")
    category = Category(name="Raw Materials")
    db.session.add(vendor)
    db.session.add(category)
    db.session.commit()

    # 3. Create product (starts with 0 stock)
    product = Product(
        name="Steel Bar",
        sku="RAW-STL-001",
        category_id=category.id,
        sales_price=150.0,
        cost_price=100.0,
        product_type="raw_material",
        is_active=True
    )
    db.session.add(product)
    db.session.commit()

    inv = InventoryService.get_or_create_inventory(product.id)
    assert inv.on_hand_qty == 0.0

    # Log in
    client.post("/auth/login", data={"username": "purchaser", "password": "pass123"})

    # 4. Create Purchase Order (draft)
    response = client.post("/purchase/create", data={
        "vendor_id": vendor.id,
        "notes": "Test PO"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Purchase Order" in response.data

    order = PurchaseOrder.query.filter_by(vendor_id=vendor.id).first()
    assert order is not None
    assert order.status == "draft"

    # 5. Add Line
    response = client.post(f"/purchase/{order.id}/add-line", data={
        "product_id": product.id,
        "quantity": 50.0,
        "unit_cost": 95.0
    }, follow_redirects=True)
    assert response.status_code == 200
    assert order.subtotal == 4750.0

    # 6. Confirm Purchase Order
    response = client.post(f"/purchase/{order.id}/confirm", follow_redirects=True)
    assert response.status_code == 200
    assert b"confirmed" in response.data

    order = PurchaseOrder.query.get(order.id)
    assert order.status == "confirmed"
    assert inv.on_hand_qty == 0.0

    # 7. Receive Purchase Order
    response = client.post(f"/purchase/{order.id}/receive", follow_redirects=True)
    assert response.status_code == 200
    assert b"received" in response.data

    order = PurchaseOrder.query.get(order.id)
    assert order.status == "received"

    # Verify inventory is increased
    inv = Inventory.query.filter_by(product_id=product.id).first()
    assert inv.on_hand_qty == 50.0

    # Verify Stock Ledger
    ledger = StockLedger.query.filter_by(product_id=product.id).first()
    assert ledger is not None
    assert ledger.movement_type == "purchase_receipt"
    assert ledger.quantity == 50.0
