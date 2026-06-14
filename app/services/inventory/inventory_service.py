from app.extensions import db
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.stock_ledger import StockLedger


class InventoryService:
    @staticmethod
    def get_or_create_inventory(product_id, warehouse="Main", location="Default"):
        inv = Inventory.query.filter_by(product_id=product_id, warehouse=warehouse, location=location).first()
        if not inv:
            inv = Inventory(product_id=product_id, warehouse=warehouse, location=location)
            db.session.add(inv)
            db.session.commit()
        return inv

    @staticmethod
    def adjust_stock(product_id, quantity, reason, user_id=None, warehouse="Main", location="Default"):
        inv = InventoryService.get_or_create_inventory(product_id, warehouse=warehouse, location=location)
        before = inv.on_hand_qty
        inv.on_hand_qty += quantity
        if inv.on_hand_qty < 0:
            return False, "Stock cannot be negative"
        db.session.flush()

        entry = StockLedger(
            product_id=product_id,
            movement_type="adjustment",
            reference_type="adjustment",
            quantity=quantity,
            before_qty=before,
            after_qty=inv.on_hand_qty,
            notes=reason,
            user_id=user_id,
        )
        db.session.add(entry)
        db.session.commit()
        return True, inv

    @staticmethod
    def get_low_stock_products():
        return Inventory.query.filter(
            Inventory.on_hand_qty <= Inventory.product.has(Product.is_active.is_(True))
        ).all()

    @staticmethod
    def get_stock_value():
        inventories = Inventory.query.all()
        return sum(inv.on_hand_qty * inv.product.cost_price for inv in inventories if inv.product)

    @staticmethod
    def find_surplus_locations(product_id, exclude_warehouse=None, exclude_location=None):
        """
        Scan all inventory rows for product_id.
        Find locations that have free stock > reorder_level (or > safety_stock).
        Return list of dicts: [{'warehouse': ..., 'location': ..., 'surplus_qty': ...}] sorted by surplus_qty desc.
        """
        invs = Inventory.query.filter_by(product_id=product_id).all()
        candidates = []
        for inv in invs:
            if exclude_warehouse and inv.warehouse == exclude_warehouse:
                if not exclude_location or inv.location == exclude_location:
                    continue
            
            product = inv.product
            limit = max(product.reorder_level or 0.0, product.safety_stock or 0.0)
            
            surplus = inv.free_to_use_qty - limit
            if surplus > 0:
                candidates.append({
                    "warehouse": inv.warehouse,
                    "location": inv.location,
                    "surplus_qty": surplus,
                    "free_to_use": inv.free_to_use_qty
                })
        candidates.sort(key=lambda x: x["surplus_qty"], reverse=True)
        return candidates

    @staticmethod
    def get_inter_location_replenishment_recommendations():
        """
        Scan all active products and their inventories to find:
        - Deficits in specific warehouse locations (on_hand_qty <= safety_stock).
        - Corresponding surpluses in other locations within the SAME warehouse (free_to_use_qty > safety_stock).
        Suggest transfers to resolve deficits without dipping source locations below safety_stock.
        """
        active_products = Product.query.filter_by(is_active=True).all()
        recommendations = []

        for prod in active_products:
            # Query all inventories for this product
            invs = Inventory.query.filter_by(product_id=prod.id).all()
            if len(invs) < 2:
                continue

            # Group by warehouse
            wh_groups = {}
            for inv in invs:
                wh_groups.setdefault(inv.warehouse, []).append(inv)

            for wh_name, items in wh_groups.items():
                if len(items) < 2:
                    continue

                # Separate into low stock and surplus locations
                threshold = prod.safety_stock or 0.0

                low_locations = []
                surplus_locations = []

                for item in items:
                    if item.on_hand_qty <= threshold:
                        low_locations.append(item)
                    elif item.free_to_use_qty > threshold:
                        surplus_locations.append(item)

                for low_item in low_locations:
                    deficit = threshold - low_item.on_hand_qty
                    if deficit <= 0.001:
                        continue

                    # Find candidate surplus locations in the same warehouse
                    candidates = []
                    for s_item in surplus_locations:
                        surplus = s_item.free_to_use_qty - threshold
                        if surplus > 0.001:
                            candidates.append((s_item, surplus))

                    if not candidates:
                        continue

                    # Sort candidates by surplus descending
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    best_source, best_surplus = candidates[0]

                    transfer_qty = min(deficit, best_surplus)
                    if transfer_qty > 0.001:
                        recommendations.append({
                            "product_id": prod.id,
                            "product_name": prod.name,
                            "product_sku": prod.sku,
                            "warehouse": wh_name,
                            "from_location": best_source.location,
                            "to_location": low_item.location,
                            "quantity": round(transfer_qty, 2),
                            "source_qty": best_source.free_to_use_qty,
                            "dest_qty": low_item.on_hand_qty,
                            "safety_stock": threshold
                        })
        return recommendations

    @staticmethod
    def sync_warehouses_and_locations():
        from app.models.warehouse import Warehouse, Location
        distinct_pairs = db.session.query(Inventory.warehouse, Inventory.location).distinct().all()
        for wh_name, loc_name in distinct_pairs:
            if not wh_name:
                continue
            
            wh = Warehouse.query.filter_by(name=wh_name).first()
            if not wh:
                code = f"WH-{wh_name.upper().replace(' ', '')}"
                base_code = code
                counter = 1
                while Warehouse.query.filter_by(code=code).first():
                    code = f"{base_code}-{counter}"
                    counter += 1
                wh = Warehouse(name=wh_name, code=code)
                db.session.add(wh)
                db.session.commit()
            
            if loc_name:
                loc = Location.query.filter_by(warehouse_id=wh.id, name=loc_name).first()
                if not loc:
                    loc = Location(warehouse_id=wh.id, name=loc_name)
                    db.session.add(loc)
                    db.session.commit()

    @staticmethod
    def cascade_warehouse_rename(old_name, new_name):
        from app.models.inventory import Inventory
        from app.models.stock_transfer import StockTransfer
        from app.models.procurement_request import ProcurementRequest
        from app.models.purchase_order_line import PurchaseOrderLine
        from app.models.manufacturing_order import ManufacturingOrder
        
        Inventory.query.filter_by(warehouse=old_name).update({Inventory.warehouse: new_name})
        StockTransfer.query.filter_by(from_warehouse=old_name).update({StockTransfer.from_warehouse: new_name})
        StockTransfer.query.filter_by(to_warehouse=old_name).update({StockTransfer.to_warehouse: new_name})
        ProcurementRequest.query.filter_by(warehouse=old_name).update({ProcurementRequest.warehouse: new_name})
        PurchaseOrderLine.query.filter_by(warehouse=old_name).update({PurchaseOrderLine.warehouse: new_name})
        ManufacturingOrder.query.filter_by(warehouse=old_name).update({ManufacturingOrder.warehouse: new_name})
        db.session.commit()

    @staticmethod
    def cascade_location_rename(warehouse_name, old_loc, new_loc):
        from app.models.inventory import Inventory
        from app.models.stock_transfer import StockTransfer
        from app.models.procurement_request import ProcurementRequest
        from app.models.purchase_order_line import PurchaseOrderLine
        from app.models.manufacturing_order import ManufacturingOrder
        
        Inventory.query.filter_by(warehouse=warehouse_name, location=old_loc).update({Inventory.location: new_loc})
        StockTransfer.query.filter_by(from_warehouse=warehouse_name, from_location=old_loc).update({StockTransfer.from_location: new_loc})
        StockTransfer.query.filter_by(to_warehouse=warehouse_name, to_location=old_loc).update({StockTransfer.to_location: new_loc})
        ProcurementRequest.query.filter_by(warehouse=warehouse_name, location=old_loc).update({ProcurementRequest.location: new_loc})
        PurchaseOrderLine.query.filter_by(warehouse=warehouse_name, location=old_loc).update({PurchaseOrderLine.location: new_loc})
        ManufacturingOrder.query.filter_by(warehouse=warehouse_name, location=old_loc).update({ManufacturingOrder.location: new_loc})
        db.session.commit()

