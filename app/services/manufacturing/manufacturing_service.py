from app.extensions import db
from app.models.manufacturing_order import ManufacturingOrder
from app.models.product import Product
from app.models.bom import Bom
from app.models.work_order import WorkOrder
from app.services.inventory.stock_service import StockService
from datetime import datetime


class ManufacturingService:
    def create_mo(self, product_id, quantity, bom_id=None, notes=""):
        product = Product.query.get(product_id)
        if not bom_id:
            bom = Bom.query.filter_by(product_id=product_id, is_active=True).first()
            bom_id = bom.id if bom else None
        mo = ManufacturingOrder(
            mo_number=f"MO-{ManufacturingOrder.query.count() + 1:05d}",
            product_id=product_id,
            bom_id=bom_id,
            quantity=quantity,
            notes=notes,
            status="draft",
        )
        db.session.add(mo)
        db.session.commit()
        return mo

    def confirm_mo(self, mo_id):
        mo = ManufacturingOrder.query.get(mo_id)
        if not mo or mo.status != "draft":
            return mo, "Manufacturing order not found or already confirmed"

        messages = []

        # Check component availability and create MOs for shortages
        if mo.bom:
            for component in mo.bom.components.all():
                component_product = component.component_product
                required_qty = component.quantity * mo.quantity
                inventory = component_product.inventory
                available_qty = inventory.free_to_use_qty if inventory else 0.0
                shortage_qty = max(0, required_qty - available_qty)

                # Reserve available stock for this component
                if available_qty > 0:
                    StockService.reserve_stock(component_product.id, min(available_qty, required_qty))

                # Create manufacturing order for component shortage
                if shortage_qty > 0:
                    component_bom = Bom.query.filter_by(product_id=component_product.id, is_active=True).first()
                    component_mo = ManufacturingOrder(
                        mo_number=f"MO-{ManufacturingOrder.query.count() + 1:05d}",
                        product_id=component_product.id,
                        bom_id=component_bom.id if component_bom else None,
                        quantity=shortage_qty,
                        notes=f"Auto-created for component shortage in MO {mo.mo_number}",
                        status="draft",
                    )
                    db.session.add(component_mo)
                    db.session.flush()
                    messages.append(f"Manufacturing order created for {shortage_qty} units of {component_product.name}")

        mo.status = "confirmed"
        db.session.commit()
        return mo, "; ".join(messages) if messages else None

    def start_mo(self, mo_id):
        mo = ManufacturingOrder.query.get(mo_id)
        if mo and mo.status == "confirmed":
            mo.status = "in_progress"
            mo.start_date = datetime.utcnow()
            if mo.bom:
                for i, operation in enumerate(mo.bom.operations.all()):
                    wo = WorkOrder(
                        mo_id=mo.id,
                        work_center_id=operation.work_center_id,
                        operation_name=operation.name,
                        sequence=operation.sequence,
                        duration_minutes=operation.duration_minutes,
                        status="pending",
                    )
                    db.session.add(wo)
            db.session.commit()
        return mo
