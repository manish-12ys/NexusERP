# NexusERP - Project Architecture & Usage Flow

> Comprehensive guide to understanding NexusERP system architecture, module interactions, and complete user workflows.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Module Breakdown](#module-breakdown)
3. [Data Models & Relationships](#data-models--relationships)
4. [User Roles & Permissions](#user-roles--permissions)
5. [Complete Usage Flows](#complete-usage-flows)
6. [Data Flow Between Modules](#data-flow-between-modules)
7. [Integration Points](#integration-points)

---

## System Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│              Presentation Layer                     │
│  (Jinja Templates, Bootstrap UI, Bootstrap Icons)  │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              API Layer (Routes)                      │
│  (15+ Blueprint modules handling HTTP requests)    │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│         Business Logic Layer (Services)             │
│  (50+ service classes handling core logic)         │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│         Data Access Layer (Models)                  │
│  (30+ SQLAlchemy models with relationships)        │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│            Database Layer (SQLite)                  │
│  (Persistent data storage + audit trails)          │
└─────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend Framework** | Flask 3.1 | HTTP request handling, routing |
| **Language** | Python 3.14 | Business logic implementation |
| **ORM** | SQLAlchemy | Database abstraction & relationships |
| **Database** | SQLite | Persistent data storage |
| **Authentication** | Flask-Login + Bcrypt | User auth & password security |
| **Form Handling** | Flask-WTF + WTForms | Data validation & rendering |
| **Frontend** | Bootstrap 5.3 + Jinja | Responsive UI templates |
| **Charts** | Chart.js | Real-time analytics visualization |
| **Real-time** | Flask-SocketIO | Live data updates (when configured) |
| **AI** | Google Gemini | AI Copilot assistance |

---

## Module Breakdown

### 1. **Product Management** (`app/routes/products.py`)

**Purpose:** Manage product catalog, categories, and master data.

**Key Features:**
- Create/Edit/Delete products with SKU tracking
- Product categorization (raw materials, semi-finished, finished goods)
- Barcode generation for product tracking
- Product specifications (sales price, cost price, tax %)
- Unit of measure management

**Database Models:**
- `Product` - Core product data
- `Category` - Product classification
- `Inventory` - Live stock levels
- `StockLedger` - Transaction history

**Core Services:**
- `ProductService` - CRUD operations
- `InventoryService` - Stock management
- `BarcodeGenerator` - SKU/barcode generation

**User Workflow:**
```
Product Admin creates product
    ↓
Enter: Name, SKU, Category, Pricing
    ↓
System generates barcode
    ↓
Product available for sales/procurement
```

---

### 2. **Inventory Management** (`app/routes/inventory.py`)

**Purpose:** Track stock levels across warehouses and manage physical inventory.

**Key Features:**
- Real-time stock tracking (on-hand, reserved, free-to-use)
- Multi-warehouse support
- Stock transfers between locations
- Physical inventory adjustments
- Low-stock alerts
- Stock ledger audit trail
- Automatic stock reservations

**Database Models:**
- `Inventory` - Stock levels by location
- `StockLedger` - Transaction audit trail
- `InventoryAdjustment` - Manual adjustments

**Core Services:**
- `InventoryService` - Stock calculations
- `LedgerService` - Transaction recording
- `ReservationService` - Order reservation logic

**Stock Formula:**
```
On-Hand = Opening + Purchases + Productions - Sales - Adjustments
Reserved = Allocated to sales orders (not yet delivered)
Free-to-Use = On-Hand - Reserved
```

**User Workflow:**
```
Warehouse Manager opens Inventory module
    ↓
Views real-time stock levels per location
    ↓
Identifies low-stock items
    ↓
Initiates stock transfer/adjustment
    ↓
System updates ledger with full audit trail
```

---

### 3. **Sales Module** (`app/routes/sales.py`, `app/routes/customers.py`)

**Purpose:** Manage customer orders from creation to delivery.

**Key Features:**
- Sales order creation with line items
- Automatic inventory reservation
- Order confirmation & delivery tracking
- Payment status management
- Order history & amendments
- Customer credit limit enforcement
- Delivery proof tracking

**Database Models:**
- `Customer` - Customer master data
- `SalesOrder` - Order header
- `SalesOrderLine` - Order line items
- `SalesDelivery` - Delivery tracking

**Core Services:**
- `SalesService` - Order CRUD operations
- `ReservationService` - Stock reservation logic
- `DeliveryService` - Delivery tracking

**Sales Order Lifecycle:**
```
CREATE
  ↓ (Check inventory)
CONFIRM
  ↓ (Reserve stock)
PICK
  ↓ (Physical fulfillment)
DELIVER
  ↓ (Update stock)
COMPLETE
  ↓ (Revenue recognition in Analytics)
```

**User Workflow:**
```
Sales Manager creates new sales order
    ↓
Enters: Customer, Product, Quantity, Price
    ↓
System validates inventory availability
    ↓
Order confirmed → Stock automatically reserved
    ↓
Warehouse picks & ships items
    ↓
Customer receives → Order complete
    ↓
Analytics records revenue
```

---

### 4. **Purchase Module** (`app/routes/purchase.py`, `app/routes/vendors.py`)

**Purpose:** Manage supplier relationships and purchase orders.

**Key Features:**
- Supplier (vendor) master management
- Purchase order creation & tracking
- Goods receipt & quality checks
- Invoice matching (3-way matching)
- Supplier performance metrics
- Lead time tracking

**Database Models:**
- `Vendor` (displayed as "Supplier") - Supplier data
- `PurchaseOrder` - PO header
- `PurchaseOrderLine` - PO line items
- `GoodsReceipt` - Receiving records

**Core Services:**
- `PurchaseService` - PO management
- `ReceivingService` - Goods receipt processing
- `InvoiceMatchingService` - Document reconciliation

**Purchase Order Lifecycle:**
```
CREATE
  ↓ (Send to supplier)
CONFIRM
  ↓ (Track shipment)
RECEIVE
  ↓ (Update inventory)
INVOICE
  ↓ (Payment processing)
CLOSE
```

**User Workflow:**
```
Procurement Manager creates purchase order
    ↓
Selects: Supplier, Product, Quantity, Rate
    ↓
Order sent to supplier (status: pending)
    ↓
Goods received at warehouse
    ↓
Warehouse Manager receives and verifies items
    ↓
System updates inventory & stock ledger
    ↓
Invoice matched with PO and receipt
    ↓
Payment processed
```

---

### 5. **Manufacturing Module** (`app/routes/manufacturing.py`, `app/routes/workorders.py`)

**Purpose:** Execute production from planning to completion.

**Key Features:**
- Production Order (MO) creation from sales demand
- Product Recipe (BOM) management
- Work order creation from recipes
- Production progress tracking
- Material consumption tracking
- Work center capacity management
- Kanban board visualization

**Database Models:**
- `Bom` (Recipe) - Product composition
- `BomComponent` - Raw materials in recipe
- `BomOperation` - Production steps
- `ManufacturingOrder` (MO) - Production order
- `WorkOrder` - Individual production task
- `WorkCenter` - Production facility
- `ProductionOrder` - Linked to MO

**Core Services:**
- `ManufacturingService` - MO CRUD
- `WorkOrderService` - Task assignment & tracking
- `ProductionService` - Execution & completion
- `BomService` - Recipe explosion & costing

**Production Recipe Explosion:**
```
Recipe: "Dining Table"
├── Raw Materials (components):
│   ├── Wood (4 units @ ₹500)
│   ├── Legs (4 units @ ₹100)
│   └── Fasteners (16 units @ ₹5)
└── Operations:
    ├── Op1: Cutting (2 hours @ WC-01)
    ├── Op2: Assembly (3 hours @ WC-02)
    └── Op3: Finishing (1 hour @ WC-03)
```

**Manufacturing Order Lifecycle:**
```
CREATE (from sales demand)
  ↓
CONFIRM
  ↓ (Reserve raw materials)
START
  ↓ (Create work orders)
IN_PROGRESS
  ↓ (Track production)
COMPLETE
  ↓ (Consume materials, produce finished goods)
CLOSE
```

**User Workflow:**
```
Manufacturing Manager views low finished goods
    ↓
Creates Production Order (MO)
    ↓
Selects: Product, Recipe, Quantity
    ↓
System checks raw material availability
    ↓
MO confirmed → Work orders generated
    ↓
Factory team picks materials & starts production
    ↓
Kanban board shows real-time progress
    ↓
Each operation completes with time & quantity tracking
    ↓
Final goods produced → Added to inventory
    ↓
Raw materials automatically consumed from stock
```

---

### 6. **Procurement (Smart Purchasing)** (`app/routes/procurement.py`)

**Purpose:** Automate replenishment decisions using intelligent rules.

**Key Features:**
- Procurement rules engine (Make-to-Stock, Make-to-Order)
- Automatic reorder point calculation
- Supplier recommendation
- Purchase request generation
- Demand forecasting integration
- Procurement analytics

**Database Models:**
- `ProcurementRule` - Reorder rules per product
- `ProcurementRequest` - Generated requests

**Core Services:**
- `ProcurementEngine` - Rule execution
- `MtsEngine` - Make-to-Stock logic
- `MtoEngine` - Make-to-Order logic
- `ReorderEngine` - Reorder point calculation

**Procurement Rules Logic:**
```
Rule: "Table - Make-to-Stock"
├── Trigger: When stock < 50 units
├── Source: Purchase from Supplier A or Manufacture in-house
├── Order Qty: 200 units
└── Lead Time: 5 days

Execution:
When stock drops below 50
    ↓
System checks: Can we manufacture? → If yes, create MO
    ↓
If manufacturing not feasible → Create PO to Supplier A
    ↓
Order for 200 units placed
    ↓
Expected arrival in 5 days
```

**User Workflow:**
```
Procurement Manager sets up rules
    ↓
Rule: "Order Table when stock < 50 units"
    ↓
System monitors inventory in real-time
    ↓
Stock drops below threshold
    ↓
System auto-triggers Purchase Order/Manufacturing Order
    ↓
No manual intervention needed
    ↓
Manager views suggested actions in Procurement dashboard
    ↓
Can approve, modify, or skip suggestions
```

---

### 7. **POS Terminal** (`app/routes/pos.py`)

**Purpose:** Point-of-sale interface for retail transactions.

**Key Features:**
- Cash register interface
- Product scanning & quick add
- Real-time stock availability
- Payment processing (cash, UPI, cards)
- Session management (open/close)
- Receipt generation
- End-of-day reconciliation

**Database Models:**
- `PosSession` - Cashier session tracking
- `PosOrder` - Transaction data
- `PosOrderLine` - Line items

**Core Services:**
- `PosService` - Transaction management
- `PaymentService` - Payment processing
- `ReceiptService` - Receipt generation

**POS Workflow:**
```
Cashier opens POS session
    ↓
Session: Amount ₹5000 (float)
    ↓
Customer adds items (scan or manual)
    ↓
Real-time availability check
    ↓
Customer makes payment
    ↓
Receipt generated
    ↓
Stock updated immediately
    ↓
At end of shift: Close session
    ↓
System reconciles transactions with opening balance
```

---

### 8. **Analytics & Reporting** (`app/routes/analytics.py`, `app/routes/reports.py`)

**Purpose:** Business intelligence and KPI tracking.

**Key Features:**
- Real-time KPI dashboard
- Sales analytics (revenue, growth, top products)
- Inventory analytics (turnover, value)
- Production metrics (efficiency, delays)
- Supplier performance (on-time delivery, quality)
- Financial reports (profit margin, COGS)
- Stock valuation report
- Custom report builder

**Core Services:**
- `KpiService` - KPI calculations
- `ReportService` - Report generation
- `BusinessHealthService` - Health metrics
- `DemandForecastService` - Predictive analytics

**Key Metrics Tracked:**
```
Sales:
├── Total Revenue (₹)
├── Sales Growth (%)
├── Average Order Value
└── Top 10 Products

Inventory:
├── Total Stock Value
├── Inventory Turnover
├── Slow-moving items
└── Low-stock alerts

Production:
├── Manufacturing orders completed
├── Average production time
├── On-time completion %
└── Material waste %

Procurement:
├── Supplier on-time delivery %
├── Order-to-receipt time
└── Supplier quality rating
```

---

### 9. **Audit & Compliance** (`app/routes/audit.py`)

**Purpose:** Complete transaction history and compliance tracking.

**Key Features:**
- Automatic audit trail logging
- User action tracking (who, what, when, before/after)
- Change tracking for all transactions
- Compliance reporting
- Data integrity verification
- Permission audit

**Database Models:**
- `AuditLog` - Complete transaction history

**Audit Capture Points:**
```
Every system change records:
├── User (who)
├── Timestamp (when)
├── Action (what - create/update/delete)
├── Module (which area)
├── Before-After values (what changed)
└── Reason (optional)

Example Log Entry:
User: sales@nexuserp.com
Time: 2026-06-13 14:30:45
Action: Order Confirmed
Module: Sales Order #SO-001
Before: Status = DRAFT
After: Status = CONFIRMED
```

---

### 10. **AI Copilot** (`app/routes/copilot.py`)

**Purpose:** AI-powered business intelligence assistant.

**Key Features:**
- Natural language queries
- Business health summary
- Alert recommendations
- Decision support
- Performance insights
- Anomaly detection

**Uses Google Gemini API** (when configured).

---

## Data Models & Relationships

### Core Entity Relationships

```
┌─────────────────────────────────────────────────────┐
│                   PRODUCT                           │
│  (id, sku, name, type, sales_price, cost_price)   │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌────────┐  ┌────────┐  ┌──────────┐
   │ SALES  │  │PURCHASE│  │INVENTORY │
   │ ORDER  │  │ ORDER  │  │(quantity)│
   │ LINE   │  │ LINE   │  └──────────┘
   └────────┘  └────────┘

┌─────────────────────────────────────────────────────┐
│                    BOM (Recipe)                     │
│            Product Composition & Operations         │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌────────────┐ ┌────────────┐ ┌──────────────┐
   │COMPONENT   │ │OPERATION   │ │MANUFACTURING│
   │(raw mat'l) │ │(production)│ │WORK CENTER  │
   └────────────┘ └────────────┘ └──────────────┘

┌─────────────────────────────────────────────────────┐
│             MANUFACTURING ORDER (MO)                │
│       Links Recipe to Production Execution         │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌──────────┐ ┌────────┐ ┌──────────┐
   │WORK      │ │MATERIAL│ │FINISHED  │
   │ORDER     │ │CONSUMP.│ │GOODS OUT │
   └──────────┘ └────────┘ └──────────┘
```

### Transaction Flow Through Ledger

```
STOCK LEDGER Tracks:
├── Opening Balance (start of period)
├── Additions:
│   ├── Purchase Receipts
│   ├── Production Output
│   └── Stock Adjustments (positive)
├── Deductions:
│   ├── Sales Deliveries
│   ├── Material Consumption
│   └── Stock Adjustments (negative)
└── Closing Balance (end of period)

Example Ledger Entry:
Date: 2026-06-13
Product: Table
Transaction: Sale Delivery (SO-001)
Quantity: -5 units
Running Balance: 95 → 90 units
```

---

## User Roles & Permissions

### Role Hierarchy & Access

```
┌──────────────────────────────────────────────┐
│            SYSTEM ADMINISTRATOR              │
│  • Full system access                        │
│  • User & role management                    │
│  • System configuration                      │
│  • Audit log access                          │
└──────────────────────────────────────────────┘
            │
    ┌───────┼───────┬──────────┬──────────┐
    │       │       │          │          │
┌───▼──┐ ┌──▼──┐ ┌─▼───┐ ┌───▼─┐ ┌────▼─┐
│Sales │ │Inv. │ │Mfg. │ │Proc.│ │POS   │
│Mgr.  │ │Mgr. │ │Mgr. │ │Mgr. │ │Cashier
└──────┘ └─────┘ └─────┘ └─────┘ └──────┘
```

### Permission Model

```
User
  ├── Assigned Roles (can have multiple)
  │   └── Each Role has Permissions
  │       ├── view_* (read access)
  │       ├── create_* (create new records)
  │       ├── edit_* (modify records)
  │       ├── delete_* (remove records)
  │       └── execute_* (special actions)
  │
  ├── Direct Permissions (override)
  │
  └── Effective Permissions = Role + Direct

Typical Sales Role Permissions:
├── view_sales (read sales orders)
├── create_sales (create new orders)
├── edit_sales (modify orders)
├── view_products (see product catalog)
├── view_customers (customer lookup)
├── view_inventory (stock availability)
└── execute_delivery (confirm delivery)
```

---

## Complete Usage Flows

### Flow 1: Sales Order → Delivery → Revenue

```
START
  │
  ├─→ Sales Manager creates Sales Order
  │   Input: Customer, Products, Quantities, Prices
  │
  ├─→ System validates:
  │   ├─ Customer credit limit OK? ✓
  │   └─ Stock available? ✓
  │
  ├─→ Order CONFIRMED
  │   Action: Reserve stock
  │           Record in AuditLog
  │           Email confirmation sent
  │
  ├─→ Warehouse team picks items
  │   Status: IN_PICKING
  │
  ├─→ Items shipped to customer
  │   Status: SHIPPED
  │   Stock ledger updated: -5 units
  │
  ├─→ Customer receives items
  │   Status: DELIVERED
  │
  ├─→ Analytics processes:
  │   ├─ Revenue recognized
  │   ├─ COGS calculated
  │   ├─ Profit margin computed
  │   └─ KPIs updated
  │
  └─→ END (Order Complete)

Audit Trail Created:
├── [14:00] Order created by sales@nexuserp.com
├── [14:05] Stock reserved (5 units)
├── [14:10] Order confirmed
├── [14:30] Picked by warehouse@nexuserp.com
├── [15:00] Shipped
├── [15:45] Delivered
└── [16:00] Revenue recognized
```

---

### Flow 2: Low Stock → Procurement → Production

```
START (Inventory Monitoring)
  │
  ├─→ Scheduled job runs (every hour)
  │   Checks: Table stock = 45 units
  │   Minimum: 50 units
  │   ALERT: Stock below minimum!
  │
  ├─→ Smart Purchasing engine triggers
  │   Rule: "Table - Make-to-Stock"
  │   Decision: Manufacture in-house
  │
  ├─→ Manufacturing Order (MO) auto-created
  │   Product: Table
  │   Quantity: 200 units
  │   Status: DRAFT
  │
  ├─→ Production Manager reviews MO
  │   Checks raw material availability
  │   ├─ Wood: 800 units available ✓
  │   ├─ Legs: 800 units available ✓
  │   └─ Fasteners: 3200 units available ✓
  │
  ├─→ MO CONFIRMED
  │   ├─ Raw materials RESERVED
  │   ├─ Recipe exploded (BOM)
  │   └─ Work orders generated (3 operations)
  │
  ├─→ Factory executes production
  │   Op1: Cutting (2 hrs) → Material consumption recorded
  │   Op2: Assembly (3 hrs) → Progress tracked
  │   Op3: Finishing (1 hr) → Quality verified
  │
  ├─→ Production COMPLETE
  │   Actions:
  │   ├─ Raw materials fully consumed
  │   ├─ 200 finished Tables produced
  │   ├─ Added to inventory: 45 + 200 = 245 units
  │   └─ Stock ledger updated
  │
  ├─→ Analytics updated
  │   ├─ Inventory value recalculated
  │   ├─ COGS recorded
  │   └─ Production efficiency metrics tracked
  │
  └─→ END (Stock replenished, MO closed)

Procurement Timeline:
├── 09:00 - Stock alert triggered
├── 09:05 - Auto-created MO#2045
├── 09:30 - Production Manager confirms
├── 10:00 - Factory starts Cutting
├── 12:00 - Cutting complete → Assembly starts
├── 15:00 - Assembly complete → Finishing starts
├── 16:00 - Finishing complete → QC pass
├── 16:15 - Stock updated: 245 units
└── 16:30 - MO closed
```

---

### Flow 3: Purchase Order → Goods Receipt

```
START (Procurement Decision)
  │
  ├─→ Procurement Manager needs raw materials
  │   Analysis: Wood inventory = 50 units
  │   Reorder point: 100 units
  │   Decision: Purchase 500 units from Supplier A
  │
  ├─→ Creates Purchase Order
  │   Supplier: Supplier A
  │   Product: Wood (raw material)
  │   Quantity: 500 units @ ₹400/unit
  │   Total: ₹200,000
  │   Lead time: 5 days
  │
  ├─→ PO sent to Supplier
  │   Status: PENDING
  │   Supplier notified (email/SMS)
  │
  ├─→ Supplier ships goods
  │   5 days pass...
  │   Tracking: Shipment in transit
  │
  ├─→ Warehouse receives shipment
  │   Goods inspection begins
  │   ├─ Physical count: 500 units ✓
  │   ├─ Quality check: All good ✓
  │   └─ Condition: No damage ✓
  │
  ├─→ Goods Receipt created
  │   Maps 500 units to PO
  │   Status: RECEIVED
  │   Receiving timestamp: 2026-06-20 10:00
  │
  ├─→ System updates
  │   ├─ PO status: CONFIRMED
  │   ├─ Inventory: 50 + 500 = 550 units
  │   ├─ Stock ledger: Entry recorded
  │   └─ Location: Warehouse A, Rack B3
  │
  ├─→ Invoice received from supplier
  │   Amount: ₹200,000
  │   Matches PO: ✓ (3-way match complete)
  │   Status: READY_FOR_PAYMENT
  │
  ├─→ Finance approves payment
  │   Method: Bank transfer
  │   Payment processed
  │   Status: CLOSED
  │
  └─→ END (PO completed, stock replenished)

Audit Trail:
├── [Jun-13 14:00] PO created by procurement@nexuserp.com
├── [Jun-13 14:15] PO sent to supplier (status: pending)
├── [Jun-18 09:00] Receipt notification from shipping
├── [Jun-20 10:00] Physical receipt by warehouse@nexuserp.com
├── [Jun-20 10:30] Stock updated: +500 units
├── [Jun-22 11:00] Invoice received and matched
├── [Jun-23 16:00] Payment processed
├── [Jun-23 16:15] PO closed
```

---

### Flow 4: Daily POS Operations

```
MORNING (7:00 AM)
  │
  ├─→ POS Cashier logs in
  │   Username: cashier1@nexuserp.com
  │   Password: ****
  │
  ├─→ Opens POS Session
  │   Float amount: ₹5,000 (starting cash)
  │   Session ID: POS-20260613-001
  │   Status: OPEN
  │
  THROUGHOUT DAY
  │
  ├─→ Customer 1 arrives
  │   Scans: Product SKU "CHAIR-001"
  │   Quantity: 2 units
  │   Price: ₹2,000 each = ₹4,000 total
  │   Payment: Cash ₹4,000
  │   Receipt generated & printed
  │   Inventory: -2 units (real-time)
  │
  ├─→ Customer 2 arrives
  │   Products: Table (₹8,000) + Cushion (₹500)
  │   Total: ₹8,500
  │   Payment: UPI (scanned QR)
  │   Receipt: Digital + printed
  │   Inventory: -1 table, -2 cushions
  │
  ├─→ [Repeat for 50-100 transactions throughout day]
  │   Total cash collected: ₹185,000
  │   Total UPI collected: ₹45,000
  │   Total credit card: ₹25,000
  │   Total sales: ₹255,000
  │
  EVENING (10:00 PM)
  │
  ├─→ Cashier closes POS Session
  │   Status: CLOSING
  │   Physical cash count: ₹190,000
  │   (Opening ₹5,000 + Sales ₹185,000)
  │
  ├─→ System reconciliation
  │   Expected: ₹5,000 + ₹185,000 = ₹190,000
  │   Actual: ₹190,000
  │   Variance: ₹0 ✓ (Perfect match)
  │
  ├─→ Session Summary generated
  │   Total transactions: 75
  │   Total revenue: ₹255,000
  │   Items sold: 125 units
  │   Inventory adjustment: Processed
  │
  ├─→ Analytics updated
  │   Daily sales: ₹255,000 recorded
  │   Top products: Chair (42 units), Table (15 units)
  │   Payment breakdown: Cash 73%, UPI 18%, Cards 9%
  │
  └─→ END (Session closed, next day ready)

Real-time Inventory Impact:
├── 07:00: Starting inventory snapshot taken
├── 07:05→22:00: Each sale instantly reduces stock
├── 22:00: Final inventory reconciliation
└── 22:30: Discrepancy report (if any)
```

---

## Data Flow Between Modules

### Cross-Module Communication

```
                        ┌─────────────┐
                        │  ANALYTICS  │
                        │(Aggregates) │
                        └──────┬──────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
    ┌────────┐           ┌─────────┐          ┌──────────┐
    │  SALES │           │ PURCHASE│          │   MFG    │
    │ Revenue├──────────▶│ COGS    │          │ Efficiency
    └────────┘           └─────────┘          └──────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                        ┌──────▼──────┐
                        │ INVENTORY   │
                        │(Center hub) │
                        └──────┬──────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
   ┌──────────┐         ┌──────────┐        ┌────────────┐
   │SALES     │         │PURCHASE  │        │PROCUREMENT │
   │Reserv.  │         │Receipts  │        │Triggers    │
   └──────────┘         └──────────┘        └────────────┘
```

### Module Interaction Pattern

```
Example: Customer orders Table (not in stock)

1. SALES MODULE creates order
   Input: SO-001, Customer ABC, 5 Tables
   Output: Order CONFIRMED, Stock RESERVED

2. INVENTORY MODULE processes reservation
   Input: 5 tables to reserve
   Action: Free-to-use: 0 → -5 (negative stock alert)
   Output: Low stock alert to Procurement

3. PROCUREMENT MODULE responds
   Input: Alert - Table stock negative
   Rule: "Make-to-Stock" for Table
   Output: Auto-create MO

4. MANUFACTURING MODULE executes
   Input: MO-2045, 200 Tables
   BOM: Explodes to materials needed
   Output: Work orders generated

5. INVENTORY MODULE updates again
   Input: MO confirmed
   Action: Reserve 800 wood, 800 legs, etc.
   Output: Raw materials allocated

6. MANUFACTURING completes production
   Input: MO-2045 complete
   Action: Consume raw materials, produce finished goods
   Output: Stock ledger entries recorded

7. INVENTORY balance updated
   On-hand: 0 → 200 tables
   Reserved: -5 (for SO-001)
   Free-to-use: 195

8. SALES delivery processed
   Input: SO-001 delivery confirmation
   Action: Reduce on-hand by 5
   Output: Stock: 200 → 195

9. ANALYTICS computes
   Revenue: ₹X recognized
   COGS: ₹Y calculated
   Profit: ₹(X-Y)
   KPIs updated

Timeline: 0-30 hours from order to revenue
```

---

## Integration Points

### API Endpoints Hierarchy

```
├── / (Landing page)
├── /auth
│   ├── /login
│   ├── /logout
│   ├── /register
│   └── /profile
├── /dashboard
│   ├── /dashboard (KPI overview)
│   └── /alerts
├── /products
│   ├── /products (list)
│   ├── /products/<id>/view
│   ├── /products/<id>/edit
│   └── /products/<id>/delete
├── /inventory
│   ├── /inventory/stock (list all)
│   ├── /inventory/transfer (move between locations)
│   ├── /inventory/adjust (manual adjustment)
│   ├── /inventory/ledger (transaction history)
│   └── /inventory/low-stock (alerts)
├── /sales
│   ├── /sales (order list)
│   ├── /sales/create
│   ├── /sales/<id>/edit
│   ├── /sales/<id>/confirm
│   ├── /sales/<id>/deliver
│   └── /sales/<id>/close
├── /customers
│   ├── /customers (directory)
│   ├── /customers/<id>/view (including order history)
│   └── /customers/<id>/edit
├── /purchase
│   ├── /purchase (PO list)
│   ├── /purchase/create
│   ├── /purchase/<id>/confirm
│   ├── /purchase/<id>/receive
│   └── /purchase/<id>/close
├── /vendors (display as "Suppliers")
│   ├── /vendors (directory)
│   ├── /vendors/<id>/view
│   └── /vendors/<id>/edit
├── /bom (display as "Product Recipes")
│   ├── /bom (recipe list)
│   ├── /bom/create
│   ├── /bom/<id>/view
│   └── /bom/<id>/edit
├── /manufacturing (display as "Production Orders")
│   ├── /manufacturing (MO list)
│   ├── /manufacturing/create
│   ├── /manufacturing/<id>/confirm
│   ├── /manufacturing/<id>/start
│   └── /manufacturing/<id>/complete
├── /workorders (display as "Production Tasks")
│   ├── /workorders (task list)
│   ├── /workorders/<id>/start
│   ├── /workorders/<id>/update
│   └── /workorders/<id>/complete
├── /procurement (display as "Smart Purchasing")
│   ├── /procurement/dashboard
│   ├── /procurement/create-rule
│   └── /procurement/run
├── /pos
│   ├── /pos/terminal (POS interface)
│   ├── /pos/session/open
│   └── /pos/session/close
├── /reports
│   ├── /reports (list)
│   ├── /reports/valuation
│   ├── /reports/sales
│   └── /reports/inventory
├── /analytics
│   ├── /analytics/dashboard
│   ├── /analytics/sales
│   └── /analytics/production
└── /audit
    ├── /audit/logs (activity history)
    └── /audit/compliance
```

---

### Database Transaction Sequence

```
Example: Complete sales order

Database Transaction Sequence:
┌────────────────────────────────────────┐
│ BEGIN TRANSACTION                      │
├────────────────────────────────────────┤
│ 1. Insert SalesOrder row               │ → SALES TABLE
│ 2. Insert SalesOrderLine row(s)        │ → SALES_ORDER_LINES TABLE
│ 3. Update Inventory (reservation)      │ → INVENTORY TABLE
│ 4. Insert StockLedger entry            │ → STOCK_LEDGER TABLE
│ 5. Create AuditLog entry               │ → AUDIT_LOG TABLE
│ 6. Insert Notification (optional)      │ → NOTIFICATION TABLE
├────────────────────────────────────────┤
│ COMMIT TRANSACTION                     │
│ (All or nothing - atomic operation)    │
└────────────────────────────────────────┘

Guarantee:
✓ Either all 6 steps succeed
✗ Or ALL are rolled back (no partial updates)
```

---

## Performance & Scalability Considerations

### Caching Strategy

```
Frequently Accessed Data (Cached):
├── Product catalog (TTL: 1 hour)
├── Supplier list (TTL: 2 hours)
├── User permissions (TTL: 30 min)
├── Exchange rates (TTL: 24 hours)
└── System configuration (TTL: 1 day)

Real-time Data (Not cached):
├── Inventory levels (always live)
├── Stock ledger (always live)
├── Order status (always live)
├── Payment status (always live)
└── Production progress (always live)
```

### Batch Operations

```
Batch Processing:
├── Stock reconciliation (daily @ 2:00 AM)
├── Revenue recognition (daily @ 3:00 AM)
├── KPI calculation (hourly)
├── Procurement engine (hourly)
└── Report generation (on-demand)
```

---

## Summary

**NexusERP Architecture:**
- Modular, scalable design with 10+ independent modules
- Centralized inventory as the hub for all transactions
- Complete audit trail for compliance
- Real-time analytics and KPI tracking
- AI-powered assistance for decision-making

**Key Flows:**
1. **Sales → Delivery** (Customer orders fulfilled)
2. **Procurement → Production** (Intelligent replenishment)
3. **Purchase → Receipt** (Supplier management)
4. **POS Transactions** (Retail sales)

**Data Integrity:**
- Atomic transactions (all-or-nothing updates)
- Stock ledger audit trail
- Complete user action history
- Permission-based access control

---

**For questions or clarifications, refer to the codebase:**
- Models: `app/models/`
- Services: `app/services/`
- Routes: `app/routes/`
- Tests: `tests/`
