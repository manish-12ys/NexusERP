def test_customers_crud_and_rbac(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.customer import Customer
    from app.models.sales_order import SalesOrder

    # 1. Create a user with 'Sales User' role
    role = Role.query.filter_by(name="Sales User").first()
    user = User(username="sales_user_test", email="sales_user_test@test.com", role_id=role.id)
    user.set_password("testpass")
    db.session.add(user)
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "sales_user_test", "password": "testpass"})

    # 2. Get customer listing
    response = client.get("/customers/")
    assert response.status_code == 200
    assert b"Customers" in response.data

    # 3. Create a customer
    create_data = {
        "name": "Customer X",
        "contact_person": "Contact X",
        "email": "x@customer.com",
        "phone": "12345",
        "address": "Address X",
        "city": "City X",
        "state": "State X",
        "pincode": "123",
        "gst_number": "GST123",
        "credit_limit": 10000.0,
    }
    response = client.post("/customers/create", data=create_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Customer &#39;Customer X&#39; created." in response.data

    # Verify customer is in DB
    customer = Customer.query.filter_by(email="x@customer.com").first()
    assert customer is not None
    assert customer.name == "Customer X"
    assert customer.credit_limit == 10000.0

    # 4. Search customer
    response = client.get("/customers/?search=Customer X")
    assert response.status_code == 200
    assert b"Customer X" in response.data

    # 5. View customer details
    response = client.get(f"/customers/{customer.id}")
    assert response.status_code == 200
    assert b"Customer Details" in response.data
    assert b"Customer X" in response.data
    assert b"x@customer.com" in response.data

    # 6. Edit customer details
    edit_data = {
        "name": "Customer X Updated",
        "contact_person": "Contact X",
        "email": "x@customer.com",
        "phone": "54321",
        "address": "Address X",
        "city": "City X",
        "state": "State X",
        "pincode": "321",
        "gst_number": "GST123",
        "credit_limit": 15000.0,
    }
    response = client.post(f"/customers/{customer.id}/edit", data=edit_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Customer &#39;Customer X Updated&#39; updated." in response.data

    customer = Customer.query.get(customer.id)
    assert customer.name == "Customer X Updated"
    assert customer.credit_limit == 15000.0

    # 7. Safe deletion test
    # A) Attempt to delete a customer who has orders
    order = SalesOrder(order_number="SO-TEST-001", customer_id=customer.id, status="draft", total_amount=500.0)
    db.session.add(order)
    db.session.commit()

    response = client.post(f"/customers/{customer.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Cannot delete customer" in response.data
    assert Customer.query.get(customer.id) is not None

    # B) Delete customer after removing their order
    db.session.delete(order)
    db.session.commit()

    response = client.post(f"/customers/{customer.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"deleted successfully" in response.data
    assert Customer.query.get(customer.id) is None
