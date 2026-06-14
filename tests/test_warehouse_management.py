import pytest
from app.models.user import User
from app.models.role import Role
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.stock_transfer import StockTransfer
from app.models.procurement_request import ProcurementRequest
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.purchase_order import PurchaseOrder
from app.models.manufacturing_order import ManufacturingOrder
from app.models.warehouse import Warehouse, Location
from app.services.inventory.inventory_service import InventoryService


def setup_manager_user(db):
    role = Role.query.filter_by(name="Inventory Manager").first()
    if not role:
        role = Role(name="Inventory Manager", permissions=["view_inventory", "adjust_inventory"])
        db.session.add(role)
        db.session.commit()
    user = User(username="manager", email="manager@test.com", role_id=role.id)
    user.set_password("managerpass")
    db.session.add(user)
    db.session.commit()
    return user


def test_sync_warehouses_and_locations(db):
    # Setup test product
    prod = Product(name="Sync Test Product", sku="SYNC-TEST-001", is_active=True)
    db.session.add(prod)
    db.session.flush()

    # Create Inventory with custom string warehouse/location
    inv = Inventory(
        product_id=prod.id,
        warehouse="Sync Warehouse",
        location="Sync Location",
        on_hand_qty=10.0
    )
    db.session.add(inv)
    db.session.commit()

    # Verify tables are empty initially
    assert Warehouse.query.filter_by(name="Sync Warehouse").first() is None

    # Call syncer
    InventoryService.sync_warehouses_and_locations()

    # Verify Warehouse and Location are created
    wh = Warehouse.query.filter_by(name="Sync Warehouse").first()
    assert wh is not None
    assert wh.code == "WH-SYNCWAREHOUSE"

    loc = Location.query.filter_by(warehouse_id=wh.id, name="Sync Location").first()
    assert loc is not None


def test_warehouse_creation_via_route(client, db):
    setup_manager_user(db)
    client.post("/auth/login", data={"username": "manager", "password": "managerpass"})

    # Create warehouse
    response = client.post("/inventory/warehouses/create", data={
        "name": "Custom North",
        "code": "WH-NORTH",
        "address": "123 North St"
    }, follow_redirects=True)

    assert response.status_code == 200
    wh = Warehouse.query.filter_by(name="Custom North").first()
    assert wh is not None
    assert wh.code == "WH-NORTH"
    assert wh.address == "123 North St"

    # Default location should be created automatically
    default_loc = Location.query.filter_by(warehouse_id=wh.id, name="Default").first()
    assert default_loc is not None


def test_location_creation_via_route(client, db):
    setup_manager_user(db)
    client.post("/auth/login", data={"username": "manager", "password": "managerpass"})

    # Pre-create a warehouse
    wh = Warehouse(name="Custom South", code="WH-SOUTH")
    db.session.add(wh)
    db.session.commit()

    # Create location
    response = client.post("/inventory/warehouses/location/create", data={
        "warehouse_id": wh.id,
        "name": "Aisle 4"
    }, follow_redirects=True)

    assert response.status_code == 200
    loc = Location.query.filter_by(warehouse_id=wh.id, name="Aisle 4").first()
    assert loc is not None


def test_warehouse_rename_cascade(client, db):
    setup_manager_user(db)
    client.post("/auth/login", data={"username": "manager", "password": "managerpass"})

    wh = Warehouse(name="Old Warehouse", code="WH-OLD")
    db.session.add(wh)
    db.session.flush()
    loc = Location(warehouse_id=wh.id, name="Default")
    db.session.add(loc)

    prod = Product(name="Cascade Product", sku="CSD-001", is_active=True)
    db.session.add(prod)
    db.session.flush()

    # Create matching models using string warehouse name
    inv = Inventory(product_id=prod.id, warehouse="Old Warehouse", location="Default", on_hand_qty=5.0)
    db.session.add(inv)

    transfer = StockTransfer(
        transfer_number="ST-999",
        product_id=prod.id,
        quantity=2.0,
        from_warehouse="Old Warehouse",
        from_location="Default",
        to_warehouse="Other WH",
        to_location="Default"
    )
    db.session.add(transfer)

    req = ProcurementRequest(request_number="PR-999", product_id=prod.id, quantity=10.0, warehouse="Old Warehouse", location="Default")
    db.session.add(req)

    po = PurchaseOrder(order_number="PO-999", vendor_id=1)
    db.session.add(po)
    db.session.flush()
    po_line = PurchaseOrderLine(purchase_order_id=po.id, product_id=prod.id, quantity=15.0, warehouse="Old Warehouse", location="Default")
    db.session.add(po_line)

    mo = ManufacturingOrder(mo_number="MO-999", product_id=prod.id, quantity=8.0, warehouse="Old Warehouse", location="Default")
    db.session.add(mo)

    db.session.commit()

    # Perform warehouse update via route
    response = client.post("/inventory/warehouses/update", data={
        "warehouse_id": wh.id,
        "name": "New Warehouse",
        "code": "WH-NEW",
        "address": "456 New St"
    }, follow_redirects=True)

    assert response.status_code == 200

    # Verify Warehouse model updated
    updated_wh = Warehouse.query.get(wh.id)
    assert updated_wh.name == "New Warehouse"
    assert updated_wh.code == "WH-NEW"

    # Verify cascading updates in other tables
    assert Inventory.query.filter_by(warehouse="Old Warehouse").first() is None
    assert Inventory.query.filter_by(warehouse="New Warehouse").first() is not None

    assert StockTransfer.query.filter_by(from_warehouse="New Warehouse").first() is not None
    assert ProcurementRequest.query.filter_by(warehouse="New Warehouse").first() is not None
    assert PurchaseOrderLine.query.filter_by(warehouse="New Warehouse").first() is not None
    assert ManufacturingOrder.query.filter_by(warehouse="New Warehouse").first() is not None


def test_location_rename_cascade(client, db):
    setup_manager_user(db)
    client.post("/auth/login", data={"username": "manager", "password": "managerpass"})

    wh = Warehouse(name="Cascade WH", code="WH-CSD")
    db.session.add(wh)
    db.session.flush()
    loc = Location(warehouse_id=wh.id, name="Old Location")
    db.session.add(loc)

    prod = Product(name="Cascade Location Product", sku="CSD-LOC-001", is_active=True)
    db.session.add(prod)
    db.session.flush()

    inv = Inventory(product_id=prod.id, warehouse="Cascade WH", location="Old Location", on_hand_qty=5.0)
    db.session.add(inv)

    transfer = StockTransfer(
        transfer_number="ST-888",
        product_id=prod.id,
        quantity=2.0,
        from_warehouse="Cascade WH",
        from_location="Old Location",
        to_warehouse="Other WH",
        to_location="Default"
    )
    db.session.add(transfer)

    req = ProcurementRequest(request_number="PR-888", product_id=prod.id, quantity=10.0, warehouse="Cascade WH", location="Old Location")
    db.session.add(req)

    po = PurchaseOrder(order_number="PO-888", vendor_id=1)
    db.session.add(po)
    db.session.flush()
    po_line = PurchaseOrderLine(purchase_order_id=po.id, product_id=prod.id, quantity=15.0, warehouse="Cascade WH", location="Old Location")
    db.session.add(po_line)

    mo = ManufacturingOrder(mo_number="MO-888", product_id=prod.id, quantity=8.0, warehouse="Cascade WH", location="Old Location")
    db.session.add(mo)

    db.session.commit()

    # Perform location update via route
    response = client.post("/inventory/warehouses/location/update", data={
        "warehouse_id": wh.id,
        "old_name": "Old Location",
        "new_name": "New Location"
    }, follow_redirects=True)

    assert response.status_code == 200

    # Verify Location model updated
    updated_loc = Location.query.filter_by(warehouse_id=wh.id, name="New Location").first()
    assert updated_loc is not None

    # Verify cascading updates
    assert Inventory.query.filter_by(warehouse="Cascade WH", location="Old Location").first() is None
    assert Inventory.query.filter_by(warehouse="Cascade WH", location="New Location").first() is not None

    assert StockTransfer.query.filter_by(from_warehouse="Cascade WH", from_location="New Location").first() is not None
    assert ProcurementRequest.query.filter_by(warehouse="Cascade WH", location="New Location").first() is not None
    assert PurchaseOrderLine.query.filter_by(warehouse="Cascade WH", location="New Location").first() is not None
    assert ManufacturingOrder.query.filter_by(warehouse="Cascade WH", location="New Location").first() is not None


def test_stock_adjustment_to_new_warehouse(client, db):
    setup_manager_user(db)
    client.post("/auth/login", data={"username": "manager", "password": "managerpass"})

    wh = Warehouse(name="North Warehouse", code="WH-NTH")
    db.session.add(wh)
    db.session.flush()
    loc = Location(warehouse_id=wh.id, name="Bin A")
    db.session.add(loc)

    prod = Product(name="Adjustment Target Product", sku="ADJ-TGT-001", is_active=True)
    db.session.add(prod)
    db.session.commit()

    response = client.post("/inventory/adjust", data={
        "product_id": prod.id,
        "warehouse": "North Warehouse",
        "location": "Bin A",
        "quantity": 25.0,
        "reason": "Initial stock seeding"
    }, follow_redirects=True)

    assert response.status_code == 200

    inv = Inventory.query.filter_by(product_id=prod.id, warehouse="North Warehouse", location="Bin A").first()
    assert inv is not None
    assert inv.on_hand_qty == 25.0
