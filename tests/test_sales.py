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


def test_sales_view_confirmed_order_risk_widget(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.category import Category
    from app.models.sales_order import SalesOrder
    from app.models.sales_order_line import SalesOrderLine
    from app.services.inventory.inventory_service import InventoryService

    role = Role.query.filter_by(name="Sales User").first()
    user = User(username="sales_view_test", email="sales_view_test@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    customer = Customer(name="Gamma Corp", email="gamma@test.com")
    category = Category(name="Risk Test Goods")
    db.session.add(customer)
    db.session.add(category)
    db.session.commit()

    product = Product(
        name="Risky Desk",
        sku="FG-RSK-001",
        category_id=category.id,
        sales_price=999.0,
        cost_price=600.0,
        product_type="finished_goods",
        procurement_type="mts",
        is_active=True,
    )
    db.session.add(product)
    db.session.commit()

    inv = InventoryService.get_or_create_inventory(product.id)
    inv.on_hand_qty = 1.0
    inv.reserved_qty = 0.0
    db.session.commit()

    order = SalesOrder(order_number="SO-RISK-0001", customer_id=customer.id, status="confirmed")
    db.session.add(order)
    db.session.flush()

    line = SalesOrderLine(
        sales_order_id=order.id,
        product_id=product.id,
        quantity=3.0,
        unit_price=product.sales_price,
        tax_percent=0.0,
        line_total=2997.0,
    )
    db.session.add(line)
    db.session.commit()

    client.post("/auth/login", data={"username": "sales_view_test", "password": "pass123"})
    response = client.get(f"/sales/{order.id}")

    assert response.status_code == 200
    assert b"Delivery Risk Predictor" in response.data
    assert b"Risk Level" in response.data


def test_sales_mto_shortage_triggers_mo(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.category import Category
    from app.models.sales_order import SalesOrder
    from app.models.bom import Bom
    from app.models.manufacturing_order import ManufacturingOrder
    from app.services.inventory.inventory_service import InventoryService

    # Setup User
    role = Role.query.filter_by(name="Sales User").first()
    user = User(username="sales_mto_rep", email="sales_mto@test.com", role_id=role.id)
    user.set_password("pass123")
    db.session.add(user)

    # Setup customer and category
    customer = Customer(name="Delta Corp", email="delta@test.com")
    category = Category(name="MTO Goods")
    db.session.add(customer)
    db.session.add(category)
    db.session.commit()

    # Create MTO product
    product = Product(
        name="Custom Sofa",
        sku="FG-SOF-001",
        category_id=category.id,
        sales_price=5000.0,
        cost_price=3000.0,
        product_type="finished_goods",
        procurement_type="mto",
        is_active=True
    )
    db.session.add(product)
    db.session.commit()

    # Add BOM for product (so it qualifies for is_manufacture)
    bom = Bom(
        product_id=product.id,
        name="BOM for Custom Sofa",
        quantity=1.0,
        is_active=True
    )
    db.session.add(bom)

    # Initialize empty inventory
    inv = InventoryService.get_or_create_inventory(product.id)
    inv.on_hand_qty = 0.0
    inv.reserved_qty = 0.0
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "sales_mto_rep", "password": "pass123"})

    # Create Sales Order
    order = SalesOrder(order_number="SO-MTO-0001", customer_id=customer.id, status="draft")
    db.session.add(order)
    db.session.commit()

    # Add line (requesting 2 Custom Sofas)
    response = client.post(f"/sales/{order.id}/add-line", data={
        "product_id": product.id,
        "quantity": 2.0
    }, follow_redirects=True)
    assert response.status_code == 200

    # Confirm order (should trigger MO creation due to shortage of 2 units on MTO product)
    response = client.post(f"/sales/{order.id}/confirm", follow_redirects=True)
    assert response.status_code == 200
    assert b"Manufacturing order" in response.data or b"confirmed" in response.data

    order = SalesOrder.query.get(order.id)
    assert order.status == "confirmed"

    # Verify Manufacturing Order is created for quantity 2
    mo = ManufacturingOrder.query.filter_by(product_id=product.id).first()
    assert mo is not None
    assert mo.quantity == 2.0
    assert "SO-MTO" in mo.notes

