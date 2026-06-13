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
from app.models.work_center import WorkCenter
from app.models.audit_log import AuditLog
from app.models.notification import Notification


class AdminDataService:
    @staticmethod
    def delete_all_data_except_users():
        """Delete all business data while preserving users, roles, and permissions"""
        
        # Delete in order of dependencies (foreign keys)
        # Start with leaf tables that have no dependents
        
        # Delete POS data
        PosOrderLine.query.delete()
        PosOrder.query.delete()
        PosSession.query.delete()
        
        # Delete Sales Order data
        SalesOrderLine.query.delete()
        SalesOrder.query.delete()
        
        # Delete Purchase Order data
        PurchaseOrderLine.query.delete()
        PurchaseOrder.query.delete()
        
        # Delete Manufacturing data
        WorkOrder.query.delete()
        ManufacturingOrder.query.delete()
        
        # Delete BOM data
        BomComponent.query.delete()
        BomOperation.query.delete()
        Bom.query.delete()
        
        # Delete Procurement data
        ProcurementRequest.query.delete()
        ProcurementRule.query.delete()
        
        # Delete Inventory data
        StockLedger.query.delete()
        Inventory.query.delete()
        
        # Delete Product data (which cascades to related inventory)
        Product.query.delete()
        
        # Delete Category data
        Category.query.delete()
        
        # Delete Customer and Vendor data
        Customer.query.delete()
        Vendor.query.delete()
        
        # Delete Work Center data
        WorkCenter.query.delete()
        
        # Delete audit logs
        AuditLog.query.delete()
        
        # Delete notifications
        Notification.query.delete()
        
        # Commit all deletions
        db.session.commit()
