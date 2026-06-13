def test_vendors_crud_and_rbac(client, db):
    from app.models.user import User
    from app.models.role import Role
    from app.models.vendor import Vendor
    from app.models.purchase_order import PurchaseOrder

    # 1. Create a user with 'Purchase User' role
    role = Role.query.filter_by(name="Purchase User").first()
    user = User(username="purchase_user_test", email="purchase_user_test@test.com", role_id=role.id)
    user.set_password("testpass")
    db.session.add(user)
    db.session.commit()

    # Log in
    client.post("/auth/login", data={"username": "purchase_user_test", "password": "testpass"})

    # 2. Get vendor listing
    response = client.get("/vendors/")
    assert response.status_code == 200
    assert b"Vendors Directory" in response.data

    # 3. Create a vendor
    create_data = {
        "name": "Vendor Y",
        "contact_person": "Contact Y",
        "email": "y@vendor.com",
        "phone": "12345",
        "address": "Address Y",
        "city": "City Y",
        "state": "State Y",
        "pincode": "123",
        "gst_number": "GST123",
        "payment_terms": "Net 30",
        "lead_time_days": 5.0,
    }
    response = client.post("/vendors/create", data=create_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Vendor &#39;Vendor Y&#39; created." in response.data

    # Verify vendor is in DB
    vendor = Vendor.query.filter_by(email="y@vendor.com").first()
    assert vendor is not None
    assert vendor.name == "Vendor Y"
    assert vendor.lead_time_days == 5

    # 4. Search vendor
    response = client.get("/vendors/?search=Vendor Y")
    assert response.status_code == 200
    assert b"Vendor Y" in response.data

    # 5. View vendor details
    response = client.get(f"/vendors/{vendor.id}")
    assert response.status_code == 200
    assert b"Vendor Details" in response.data
    assert b"Vendor Y" in response.data
    assert b"y@vendor.com" in response.data

    # 6. Edit vendor details
    edit_data = {
        "name": "Vendor Y Updated",
        "contact_person": "Contact Y",
        "email": "y@vendor.com",
        "phone": "54321",
        "address": "Address Y",
        "city": "City Y",
        "state": "State Y",
        "pincode": "321",
        "gst_number": "GST123",
        "payment_terms": "Net 60",
        "lead_time_days": 10.0,
    }
    response = client.post(f"/vendors/{vendor.id}/edit", data=edit_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Vendor &#39;Vendor Y Updated&#39; updated." in response.data

    vendor = Vendor.query.get(vendor.id)
    assert vendor.name == "Vendor Y Updated"
    assert vendor.payment_terms == "Net 60"
    assert vendor.lead_time_days == 10

    # 7. Safe deletion test
    # A) Attempt to delete a vendor who has purchase orders
    order = PurchaseOrder(order_number="PO-TEST-001", vendor_id=vendor.id, status="draft", total_amount=1000.0)
    db.session.add(order)
    db.session.commit()

    response = client.post(f"/vendors/{vendor.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Cannot delete vendor" in response.data
    assert Vendor.query.get(vendor.id) is not None

    # B) Delete vendor after removing their order
    db.session.delete(order)
    db.session.commit()

    response = client.post(f"/vendors/{vendor.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"deleted successfully" in response.data
    assert Vendor.query.get(vendor.id) is None
