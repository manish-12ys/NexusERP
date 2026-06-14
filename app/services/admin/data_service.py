from sqlalchemy import inspect
from app.extensions import db
from app.models.product import Product
from app.models.category import Category
from app.models.customer import Customer
from app.models.vendor import Vendor
from app.models.sales_order import SalesOrder
from app.models.sales_order_line import SalesOrderLine
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_order_line import PurchaseOrderLine
from app.models.inventory import Inventory
from app.models.stock_ledger import StockLedger
from app.models.manufacturing_order import ManufacturingOrder
from app.models.work_order import WorkOrder
from app.models.bom import Bom
from app.models.bom_component import BomComponent
from app.models.bom_operation import BomOperation
from app.models.pos_order import PosOrder
from app.models.pos_order_line import PosOrderLine
from app.models.pos_session import PosSession
from app.models.procurement_request import ProcurementRequest
from app.models.procurement_rule import ProcurementRule
from app.models.stock_transfer import StockTransfer
from app.models.work_center import WorkCenter
from app.models.audit_log import AuditLog
from app.models.notification import Notification


class AdminDataService:
    @staticmethod
    def _table_exists(model):
        inspector = inspect(db.engine)
        return inspector.has_table(model.__tablename__)

    @staticmethod
    def _delete_if_exists(model):
        if AdminDataService._table_exists(model):
            model.query.delete()

    @staticmethod
    def delete_all_data_except_users():
        """Delete all business data while preserving users, roles, and permissions"""
        
        # Delete in order of dependencies (foreign keys) to prevent constraint violations
        
        # 1. Delete notifications and logs
        AdminDataService._delete_if_exists(Notification)
        AdminDataService._delete_if_exists(AuditLog)
        
        # 2. Delete POS data
        AdminDataService._delete_if_exists(PosOrderLine)
        AdminDataService._delete_if_exists(PosOrder)
        AdminDataService._delete_if_exists(PosSession)
        
        # 3. Delete Sales Order data
        AdminDataService._delete_if_exists(SalesOrderLine)
        AdminDataService._delete_if_exists(SalesOrder)
        
        # 4. Delete Procurement data (must be deleted before MO and PO due to foreign keys)
        AdminDataService._delete_if_exists(ProcurementRequest)
        AdminDataService._delete_if_exists(ProcurementRule)
        AdminDataService._delete_if_exists(StockTransfer)
        
        # 5. Delete Purchase Order data
        AdminDataService._delete_if_exists(PurchaseOrderLine)
        AdminDataService._delete_if_exists(PurchaseOrder)
        
        # 6. Delete Manufacturing data
        AdminDataService._delete_if_exists(WorkOrder)
        AdminDataService._delete_if_exists(ManufacturingOrder)
        
        # 7. Delete BOM data (must be deleted after MO due to foreign keys)
        AdminDataService._delete_if_exists(BomComponent)
        AdminDataService._delete_if_exists(BomOperation)
        AdminDataService._delete_if_exists(Bom)
        
        # 8. Delete Inventory and Stock Ledger data
        AdminDataService._delete_if_exists(StockLedger)
        AdminDataService._delete_if_exists(Inventory)
        
        # 9. Delete Product data (which cascades to related inventory)
        AdminDataService._delete_if_exists(Product)
        
        # 10. Delete Category data
        AdminDataService._delete_if_exists(Category)
        
        # 11. Delete Customer and Vendor data
        AdminDataService._delete_if_exists(Customer)
        AdminDataService._delete_if_exists(Vendor)
        
        # 12. Delete Work Center data
        AdminDataService._delete_if_exists(WorkCenter)
        
        # Commit all deletions
        db.session.commit()
