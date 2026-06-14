from datetime import datetime
from app.extensions import db
from app.models.stock_transfer import StockTransfer
from app.models.inventory import Inventory
from app.models.stock_ledger import StockLedger
from app.services.inventory.ledger_service import LedgerService


class TransferService:
    @staticmethod
    def create_transfer(product_id, quantity, from_wh, from_loc, to_wh, to_loc, notes=None, user_id=None):
        if quantity <= 0:
            return None, "Quantity must be positive"

        # Generate ST-YYYYMM-XXXX
        last = StockTransfer.query.order_by(StockTransfer.id.desc()).first()
        seq = (last.id + 1) if last else 1
        transfer_number = f"ST-{datetime.utcnow().strftime('%Y%m')}-{seq:04d}"

        transfer = StockTransfer(
            transfer_number=transfer_number,
            product_id=product_id,
            quantity=quantity,
            from_warehouse=from_wh,
            from_location=from_loc,
            to_warehouse=to_wh,
            to_location=to_loc,
            status="pending",
            notes=notes
        )
        db.session.add(transfer)
        db.session.commit()
        return transfer, None

    @staticmethod
    def execute_transfer(transfer_id, user_id=None):
        transfer = StockTransfer.query.get(transfer_id)
        if not transfer:
            return False, "Transfer not found"
        if transfer.status != "pending":
            return False, f"Transfer is already in '{transfer.status}' status"

        # Find source inventory
        source_inv = Inventory.query.filter_by(
            product_id=transfer.product_id,
            warehouse=transfer.from_warehouse,
            location=transfer.from_location
        ).first()

        if not source_inv or source_inv.free_to_use_qty < transfer.quantity:
            avail = source_inv.free_to_use_qty if source_inv else 0.0
            return False, f"Insufficient stock at source: {avail} available, {transfer.quantity} requested"

        # Find or create destination inventory
        dest_inv = Inventory.query.filter_by(
            product_id=transfer.product_id,
            warehouse=transfer.to_warehouse,
            location=transfer.to_location
        ).first()

        if not dest_inv:
            dest_inv = Inventory(
                product_id=transfer.product_id,
                warehouse=transfer.to_warehouse,
                location=transfer.to_location,
                on_hand_qty=0.0
            )
            db.session.add(dest_inv)
            db.session.flush()

        # Deduct from source
        source_before = source_inv.on_hand_qty
        source_inv.on_hand_qty -= transfer.quantity
        source_after = source_inv.on_hand_qty

        # Add to destination
        dest_before = dest_inv.on_hand_qty
        dest_inv.on_hand_qty += transfer.quantity
        dest_after = dest_inv.on_hand_qty

        # Record Ledger entry for source (transfer out)
        LedgerService.record_movement(
            product_id=transfer.product_id,
            movement_type="transfer_out",
            quantity=-transfer.quantity,
            before_qty=source_before,
            after_qty=source_after,
            reference_type="transfer",
            reference_id=transfer.id,
            reference_number=transfer.transfer_number,
            notes=f"Internal transfer to {transfer.to_warehouse}:{transfer.to_location}. {transfer.notes or ''}",
            user_id=user_id
        )

        # Record Ledger entry for destination (transfer in)
        LedgerService.record_movement(
            product_id=transfer.product_id,
            movement_type="transfer_in",
            quantity=transfer.quantity,
            before_qty=dest_before,
            after_qty=dest_after,
            reference_type="transfer",
            reference_id=transfer.id,
            reference_number=transfer.transfer_number,
            notes=f"Internal transfer from {transfer.from_warehouse}:{transfer.from_location}. {transfer.notes or ''}",
            user_id=user_id
        )

        transfer.status = "completed"
        db.session.commit()
        return True, None

    @staticmethod
    def cancel_transfer(transfer_id, user_id=None):
        transfer = StockTransfer.query.get(transfer_id)
        if not transfer:
            return False, "Transfer not found"
        if transfer.status != "pending":
            return False, f"Only pending transfers can be cancelled"

        transfer.status = "cancelled"
        db.session.commit()
        return True, None
