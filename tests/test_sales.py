def test_sales_lifecycle(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.category import Category
    from app.models.inventory import Inventory
    from app.models.sales_order import SalesOrder
    from app.services.inventory.inventory_service import InventoryService

    # 1. Setup roles and user
    role = Role.query.filter_by(name="Sales User").first()
    user = User(username="sales_rep", email="sales_rep@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    # 2. Create customer and product category
    customer = Customer(name="Acme Corp", email="acme@test.com")
    category = Category(name="Finished Goods")
    db.session.add(customer)
    db.session.add(category)
    db.session.commit()

    # 3. Create product with initial inventory
    product = Product(
        name="Premium Table",
        sku="FG-TBL-001",
        category_id=category.id,
        sales_price=2000.0,
        cost_price=1200.0,
        product_type="finished_product",
        is_active=True
    )
    db.session.add(product)
    db.session.commit()

    inv = InventoryService.get_or_create_inventory(product.id)
    inv.on_hand_qty = 10.0
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "sales_rep", "password": "pass123"})

    # 4. Create Sales Order (draft)
    response = client.post("/sales/create", data={
        "customer_id": customer.id,
        "notes": "Test sales order"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Sales Order" in response.data

    # Retrieve created order
    order = SalesOrder.query.filter_by(customer_id=customer.id).first()
    assert order is not None
    assert order.status == "draft"

    # 5. Add Order Line
    response = client.post(f"/sales/{order.id}/add-line", data={
        "product_id": product.id,
        "quantity": 4.0
    }, follow_redirects=True)
    assert response.status_code == 200
    assert order.subtotal == 8000.0

    # 6. Confirm Order (reserves stock)
    response = client.post(f"/sales/{order.id}/confirm", follow_redirects=True)
    assert response.status_code == 200
    assert b"confirmed" in response.data

    order = SalesOrder.query.get(order.id)
    assert order.status == "confirmed"

    inv = Inventory.query.filter_by(product_id=product.id).first()
    assert inv.on_hand_qty == 10.0
    assert inv.reserved_qty == 4.0
    assert inv.free_to_use_qty == 6.0

    # 7. Deliver Order (consumes stock and ledger updates)
    response = client.post(f"/sales/{order.id}/deliver", follow_redirects=True)
    assert response.status_code == 200
    assert b"delivered" in response.data

    order = SalesOrder.query.get(order.id)
    assert order.status == "delivered"

    inv = Inventory.query.filter_by(product_id=product.id).first()
    assert inv.on_hand_qty == 6.0
    assert inv.reserved_qty == 0.0
    assert inv.free_to_use_qty == 6.0


def test_sales_insufficient_stock(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.category import Category
    from app.models.sales_order import SalesOrder
    from app.services.inventory.inventory_service import InventoryService

    role = Role.query.filter_by(name="Sales User").first()
    user = User(username="sales_rep2", email="sales_rep2@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    customer = Customer(name="Beta Corp", email="beta@test.com")
    category = Category(name="Finished Goods Beta")
    db.session.add(customer)
    db.session.add(category)
    db.session.commit()

    product = Product(
        name="Chair",
        sku="FG-CHR-001",
        category_id=category.id,
        sales_price=500.0,
        cost_price=300.0,
        product_type="finished_product",
        is_active=True
    )
    db.session.add(product)
    db.session.commit()

    inv = InventoryService.get_or_create_inventory(product.id)
    inv.on_hand_qty = 2.0
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "sales_rep2", "password": "pass123"})

    # Create Order
    order = SalesOrder(order_number="SO-TEST-FLOW-999", customer_id=customer.id, status="draft")
    db.session.add(order)
    db.session.commit()

    # Add line for 5 items (stock is only 2)
    response = client.post(f"/sales/{order.id}/add-line", data={
        "product_id": product.id,
        "quantity": 5.0
    }, follow_redirects=True)
    assert response.status_code == 200

    # Confirm Order (should fail due to insufficient stock and cancel order)
    response = client.post(f"/sales/{order.id}/confirm", follow_redirects=True)
    assert response.status_code == 200
    assert b"Insufficient stock" in response.data

    order = SalesOrder.query.get(order.id)
    assert order.status == "cancelled"
