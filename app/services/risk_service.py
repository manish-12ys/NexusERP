from app.models.sales_order import SalesOrder
from app.models.sales_order_line import SalesOrderLine
from app.models.inventory import Inventory
from app.models.bom import Bom

class RiskService:
    def evaluate_order_risk(self, order_id):
        order = SalesOrder.query.get(order_id)
        if not order:
            return {"level": "Unknown", "reasons": ["Order not found."]}

        if order.status in ("delivered", "cancelled"):
            return {"level": "None", "reasons": ["Order is already completed or cancelled."]}

        reasons = []
        high_risk = False
        medium_risk = False

        for line in order.lines:
            product = line.product
            # Check stock
            inv = Inventory.query.filter_by(product_id=product.id).first()
            qty_on_hand = inv.quantity_on_hand if inv else 0
            
            if qty_on_hand < line.quantity:
                if product.procurement_type == "mto":
                    medium_risk = True
                    reasons.append(f"Shortage of MTO product '{product.name}'. Needs manufacturing.")
                    # Check BOM
                    bom = Bom.query.filter_by(product_id=product.id, is_active=True).first()
                    if not bom:
                        high_risk = True
                        reasons.append(f"No active BOM found for '{product.name}'.")
                    else:
                        for comp in bom.components:
                            comp_inv = Inventory.query.filter_by(product_id=comp.product_id).first()
                            comp_qty = comp_inv.quantity_on_hand if comp_inv else 0
                            required_comp_qty = comp.quantity * line.quantity
                            if comp_qty < required_comp_qty:
                                high_risk = True
                                reasons.append(f"Component shortage: '{comp.product.name}' (Need {required_comp_qty}, have {comp_qty}).")
                else:
                    high_risk = True
                    reasons.append(f"Stock shortage for MTS product '{product.name}'. (Need {line.quantity}, have {qty_on_hand}).")

        if high_risk:
            return {"level": "High", "reasons": reasons, "color": "danger"}
        elif medium_risk:
            return {"level": "Medium", "reasons": reasons, "color": "warning"}
        else:
            return {"level": "Low", "reasons": ["All items are in stock or have sufficient components."], "color": "success"}
