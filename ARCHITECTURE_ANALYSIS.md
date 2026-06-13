# NexusERP Architecture & Data Flow Analysis

## Executive Summary

**NexusERP** is a Flask-based manufacturing ERP system designed for furniture manufacturing and similar discrete manufacturing operations. It provides end-to-end visibility from customer demand through production execution, inventory management, and business intelligence.

**Core Problem Solved:** Creates a single source of truth for the factory by eliminating visibility gaps between:
- Sales (doesn't know stock)
- Purchasing (doesn't know shortages)
- Manufacturing (doesn't know priorities)
- Inventory (often inaccurate)
- Management (cannot see status)

---

## 1. MAIN MODULES & THEIR PURPOSES

### 1.1 Products Module
**Purpose:** Master data for all items (raw materials, semi-finished goods, finished goods)

**Key Features:**
- SKU & barcode management
- Product categorization (finished_goods, raw_material, semi_finished)
- Procurement type specification (MTS = Make-to-Stock, MTO = Make-to-Order)
- Pricing: Cost price + Sales price with tax
- Supply chain parameters: Lead time, reorder level, safety stock
- Product lifecycle: Active/Inactive status

**Database Model:** `Product`
- `name`, `sku`, `barcode`, `category_id`
- `cost_price`, `sales_price`, `tax_percent`
- `product_type`, `unit_of_measure`
- `procurement_type`, `lead_time_days`
- `reorder_level`, `safety_stock`

---

### 1.2 Inventory Module
**Purpose:** Real-time stock visibility and inventory management

**Key Features:**
- Multi-location warehouse support (warehouse + location tracking)
- Four-part inventory accounting:
  - `on_hand_qty`: Physical stock
  - `reserved_qty`: Allocated to orders
  - `incoming_qty`: Expected from POs
  - `outgoing_qty`: Committed to sales
- Free-to-use quantity calculation: `on_hand - reserved`
- Low stock alerts when on_hand ≤ safety_stock
- Stock ledger tracking (history of all movements)

**Key Methods:**
- `reserve_stock()`: Reserve qty for sales order confirmation
- `unreserve_stock()`: Release reservations if order cancelled
- `consume_stock()`: Deduct from on_hand when goods used/delivered
- `receive_stock()`: Add incoming qty when PO received
- `transfer()`: Move stock between locations

**Database Models:**
- `Inventory`: Current stock state per product
- `StockLedger`: Historical record of every movement (type, qty, before/after)

---

### 1.3 Sales Order Module
**Purpose:** Manage customer demand from order creation to delivery

**Order Lifecycle:**
```
DRAFT → CONFIRMED → DELIVERED → CLOSED
         ↓
      CANCELLED
```

**Key Features:**
- Customer management with credit limits
- Order line items with quantity + unit pricing + tax
- Automatic stock reservation on confirmation
- Order-to-delivery tracking with expected/actual dates
- Order totals: subtotal, tax, discount, total amount
- User audit trail (created_by, timestamps)

**Database Models:**
- `SalesOrder`: Header (order_number, customer, status, dates, amounts)
- `SalesOrderLine`: Line items (product, qty, unit_price, tax, line_total)
- `Customer`: Name, contact, address, GST, credit_limit, is_active

**Service Methods:**
- `create_order()`: Create draft order with optional line items
- `confirm_order()`: Validate stock → Reserve → Change to CONFIRMED
- `deliver_order()`: Consume reserved stock → Change to DELIVERED
- `generate_order_number()`: SO-YYYYMM-NNNN format

---

### 1.4 Purchase Order Module
**Purpose:** Manage procurement from vendors to goods receipt

**Order Lifecycle:**
```
DRAFT → CONFIRMED → RECEIVED → CLOSED
                       ↓
                  PARTIALLY_RECEIVED
```

**Key Features:**
- Vendor master with payment terms, lead times, ratings
- Purchase line items with quantity + unit cost
- Expected receipt date tracking
- Partial receipt capability (multiple GRNs per PO)
- Order totals: subtotal, tax, total amount
- Integration with procurement requests

**Database Models:**
- `PurchaseOrder`: Header (order_number, vendor, status, dates, amounts)
- `PurchaseOrderLine`: Line items (product, qty, unit_cost, line_total)
- `Vendor`: Name, contact, address, GST, lead_time_days, payment_terms, rating

**Service Methods:**
- `create_order()`: Create draft order with optional line items
- `confirm_order()`: Change to CONFIRMED (commitment to vendor)
- `receive_goods()`: Update inventory from GRN → Change to RECEIVED

---

### 1.5 Manufacturing Module
**Purpose:** Execute production planning and order fulfillment

**Key Entities:**

#### Bill of Materials (BOM)
- Product recipe: What materials needed + How much
- Manufacturing operations: Steps required + Resource costs
- Cost calculation: Material cost + Operation cost
- Version tracking for recipe evolution
- Associated with finished goods products

#### Manufacturing Order (MO)
**Lifecycle:**
```
DRAFT → CONFIRMED → IN_PROGRESS → COMPLETED → CLOSED
                        ↓
                     CANCELLED
```
- Links finished goods → BOM → Raw materials
- Planned quantity vs. produced quantity tracking
- Start/end date scheduling
- Assignee tracking
- Work orders generated from operations

#### Work Order (WO)
- Individual production task within MO
- Assigned to work centers (machines/departments)
- Sequencing within MO (operation_name, sequence)
- Status tracking: PENDING → IN_PROGRESS → COMPLETED
- Duration & actual time tracking
- Completion percentage

**Database Models:**
- `Bom`: Version, components list, operations list, total_cost
- `BomComponent`: Product link, qty per unit, total cost
- `BomOperation`: Work center link, sequence, duration, cost
- `ManufacturingOrder`: mo_number, product, bom, quantity, produced_qty, status
- `WorkOrder`: mo_id, work_center_id, operation, sequence, status, times
- `WorkCenter`: Name, location, capacity info

**Data Flow in Manufacturing:**
1. Sales order → Demand detected
2. Shortage analysis via procurement engine
3. Manufacturing order created for finished goods
4. BOM exploded (raw materials → Work orders)
5. Work orders assigned to work centers
6. Procurement requests generated for component shortage
7. Stock consumed as manufacturing progresses
8. Finished goods added to inventory on completion

---

### 1.6 Procurement Module
**Purpose:** Intelligent procurement planning (automated supply chain decisions)

**Procurement Strategies:**

#### MTS (Make-to-Stock)
- Triggered by inventory levels vs. reorder point
- Automatic replenishment to safety stock level
- Applies to: Finished goods, common components
- Uses: `ReorderEngine`, `MtsEngine`

#### MTO (Make-to-Order)
- No pre-procurement; triggered by sales demand
- Creates procurement request when sales order confirmed
- Applies to: Custom products, specialty items

#### Reorder Policy
- Monitors product `reorder_level`
- When `on_hand_qty ≤ reorder_level`: Trigger reorder
- Creates procurement request: Qty = `reorder_level * 2`

**Key Models:**
- `ProcurementRequest`: request_number, product, quantity, status
  - `source_type`: "vendor" | "manufacturing"
  - `source_id`: Links to vendor or manufacturing order
  - Lifecycle: OPEN → IN_PROGRESS → CLOSED
- `ProcurementRule`: Product, min_order_qty, source_type, vendor, procurement_type

**Service Engines:**
- `ProcurementEngine`: Rule-based automatic request generation
- `ReorderEngine`: Monitors low stock, recommends quantities
- `MtsEngine`: Evaluates MTS rules, returns demand list
- `MtoEngine`: Generates requests from sales demand

**Data Flow:**
```
Inventory Threshold Check
    ↓
Procurement Rule Evaluation
    ↓
Request Generated (Purchase or Manufacturing)
    ↓
Converted to PO or MO
    ↓
Status Tracked
    ↓
Request Closed
```

---

### 1.7 Point of Sale (POS) Module
**Purpose:** Retail cashier interface for walk-in customers

**Key Features:**
- Session management (open/close per cashier)
- Real-time cart with product add/remove
- Payment method tracking (cash, card, etc.)
- Customer optional (cash customers vs. registered)
- Tax calculation per item
- Receipt generation

**Database Models:**
- `PosSession`: session_number, user, status, opening_balance, closing_balance, dates
- `PosOrder`: order_number, session, customer, total, payment_method, payment_status
- `PosOrderLine`: Product, quantity, unit_price, tax, line_total

**Workflow:**
1. Cashier opens session with starting balance
2. Create orders (one or more per session)
3. Add items to each order
4. Collect payment
5. Generate receipt
6. Close session with ending balance

**Connection to Inventory:**
- Real-time deduction from on_hand_qty on sale
- Stock ledger entry created for audit trail

---

### 1.8 Analytics & Reporting Module
**Purpose:** Business intelligence, KPIs, and decision support

**Key Metrics:**

#### Revenue & Sales Analytics
- Monthly revenue (DELIVERED/CLOSED orders only)
- Total sales value over period
- Open order count & value
- Completed order count

#### Inventory Analytics
- Total stock value (on_hand_qty * cost_price)
- Inventory turnover ratio: COGS / Average Inventory
- Stock movement trends
- Aging analysis (slow-moving items)
- Warehouse utilization

#### Manufacturing Analytics
- Manufacturing order completion rate
- Production queue depth
- Average lead time
- Work center utilization
- Material shortage impact

#### Purchase Analytics
- Total purchase value
- Vendor performance (on-time, quality)
- Average lead time by vendor
- Cost trends

**Database Service:** `KpiService`
- `get_revenue_growth()`: This month's delivered orders
- `inventory_turnover_ratio()`: COGS / Average inventory value
- `purchase_order_metrics()`: Total PO value by status

**Dashboard Displays:**
- Factory Control Center: Pending queue, delays, shortages
- Key metrics: Stock value, low items, free qty
- Delayed orders timeline
- Manufacturing queue
- Purchase queue
- Real-time alerts

---

### 1.9 Audit & Compliance Module
**Purpose:** Complete operational traceability and regulatory compliance

**Capabilities:**
- User-level tracking (who, when, what action)
- Reference tracking (links to order/product changed)
- Value tracking (old vs. new values for changes)
- Module-level filtering
- Time-based audit trails
- IP address logging (for security)

**Database Model:** `AuditLog`
- `user_id`: Which user
- `action`: CREATE, UPDATE, DELETE, CONFIRM, etc.
- `module`: sales, purchase, manufacturing, inventory, etc.
- `reference_type`: SalesOrder, PurchaseOrder, Product, etc.
- `reference_id`: ID of affected entity
- `reference_number`: Order number (SO-..., PO-..., etc.)
- `description`: Human-readable change
- `old_values`, `new_values`: JSON change tracking
- `ip_address`: Request source
- `created_at`: Timestamp

**Audit Trail Query:**
- By module (Sales, Purchase, Manufacturing, etc.)
- By action (Create, Confirm, Receive, etc.)
- By user
- By date range
- By reference (find all changes to SO-202406-0001)

---

### 1.10 AI Operations Copilot
**Purpose:** Natural language assistant for operational insights

**Capabilities:**
- Real-time ERP snapshot (live data)
- Intent detection from user questions
- Context-aware responses

**Intent Recognition:**
- "Low stock" → Returns products below safety stock
- "Manufacture today" → Shows manufacturing priorities
- "Shortages" → Identifies inventory gaps
- "Delayed orders" → Lists overdue orders
- General queries → Summarizes factory state

**Data Accessed:**
- Low stock items: Products with on_hand < safety_stock
- Manufacturing priorities: Demand aggregation (sales → shortage → production need)
- Delayed orders: Sales/Purchase orders with expected_date < now
- Open queue counts

**Service:** `CopilotService`
- `get_snapshot()`: Current factory state (open orders, delays, low stock)
- `_extract_intent()`: Parse user message
- `respond()`: Generate response with Gemini API (if configured)

---

## 2. DATA FLOW BETWEEN MODULES

### 2.1 Customer Demand to Delivery (Sales Path)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CUSTOMER DEMAND ENTRY POINT                      │
│                                                                       │
│  Sales User creates Sales Order with Customer + Items               │
│  Input: Customer ID, Products, Quantities, Pricing                  │
│  Status: DRAFT                                                       │
│  Location: Sales Routes → sales_bp.create_order()                  │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      SALES ORDER CONFIRMATION                       │
│                                                                       │
│  Sales confirms order → Triggers:                                   │
│  1. Stock reservation check (Free stock available?)                 │
│  2. If insufficient: Order cancelled                                │
│  3. If sufficient: Reserve qty marked in inventory                  │
│  Status: CONFIRMED                                                  │
│  Service: SalesService.confirm_order()                              │
│  Inventory Update: reserved_qty += order_line_qty                   │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
         ┌───────────────────────────────────────────┐
         │   SHORTAGE DETECTION & MANUFACTURING      │
         │   (If stock insufficient, shortage occurs)│
         │                                           │
         │  IF on_hand - reserved < 0:               │
         │  → Manufacturing request created          │
         │  → BOM exploded for components            │
         │  → Procurement requests for shortages     │
         └───────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        STOCK FULFILLMENT                            │
│                                                                       │
│  Route: From inventory, one of two paths:                           │
│                                                                       │
│  PATH A - Stock Available:                                          │
│    Status: IN_PICKING                                               │
│    Action: Staging for shipment                                     │
│                                                                       │
│  PATH B - Stock Short (requires manufacturing):                     │
│    Manufacturing Order created for finished goods                   │
│    BOM components → Procurement requests for raw materials          │
│    Manufacturing progresses in parallel                             │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         GOODS DELIVERY                              │
│                                                                       │
│  Delivery approved → Consume stock                                  │
│  Service: StockService.consume_stock()                              │
│  Actions:                                                            │
│    - on_hand_qty -= order_line_qty                                  │
│    - reserved_qty -= order_line_qty                                 │
│    - StockLedger entry created (MOVEMENT_TYPE: delivery)           │
│  Status: DELIVERED                                                  │
│  Audit: Sales module, DELIVER action logged                        │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       ORDER COMPLETION                              │
│                                                                       │
│  Final status: CLOSED                                               │
│  Revenue recognized (in KPI calculations)                           │
│  Customer notified                                                  │
│  Data available for analytics                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Entities Involved:**
- Customer → SalesOrder → SalesOrderLine → Product
- SalesOrder → Inventory (reserve/consume)
- SalesOrder → ManufacturingOrder (if shortage)
- SalesOrder → StockLedger (audit trail)
- SalesOrder → AuditLog (who, when, action)

---

### 2.2 Supplier to Inventory (Purchase Path)

```
┌─────────────────────────────────────────────────────────────────────┐
│              PROCUREMENT REQUEST CREATION (Multiple Sources)         │
│                                                                       │
│  SOURCE 1 - Low Stock Reorder:                                      │
│    Inventory threshold check: on_hand < reorder_level               │
│    Service: ReorderEngine.check_reorder()                           │
│    Action: Create ProcurementRequest(source=vendor)                 │
│                                                                       │
│  SOURCE 2 - Manufacturing Shortage:                                 │
│    BOM explosion on MO creation                                     │
│    Raw material check: Do we have component?                        │
│    Action: Create ProcurementRequest(source=vendor)                 │
│                                                                       │
│  SOURCE 3 - Make-to-Stock Rule:                                     │
│    Service: MtsEngine.evaluate()                                    │
│    Action: Create ProcurementRequest for vendor                     │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PURCHASE ORDER CREATION                          │
│                                                                       │
│  Procurement request → Purchase Order decision:                     │
│  - Purchase staff reviews open requests                             │
│  - Groups requests by vendor (consolidation)                        │
│  - Creates Purchase Order                                           │
│  Input: Vendor, Product, Quantity, Unit Cost, Expected Date         │
│  Status: DRAFT                                                      │
│  Service: PurchaseService.create_order()                            │
│  Location: Purchase Routes → purchase_bp.create_order()            │
│  ProcurementRequest.status: OPEN → IN_PROGRESS (linked to PO)     │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PURCHASE ORDER CONFIRMATION                      │
│                                                                       │
│  Purchase staff confirms order → Send to vendor                     │
│  Status: CONFIRMED                                                  │
│  Trigger: Email/EDI to vendor (optional integration)                │
│  Inventory Updated:                                                 │
│    - incoming_qty += order_line_qty                                 │
│    (now tracked as "goods on order")                                │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
         ┌────────────────────────────────────────────┐
         │  GOODS IN TRANSIT (from vendor)            │
         │  Monitored: Expected date vs. current      │
         │  Alert if delayed                          │
         └────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      GOODS RECEIPT (GRN)                            │
│                                                                       │
│  Receiving team:                                                    │
│  1. Checks goods against PO                                         │
│  2. Accepts full or partial receipt                                 │
│  3. Updates inventory:                                              │
│      - on_hand_qty += received_qty                                  │
│      - incoming_qty -= received_qty                                 │
│      - outgoing_qty (if return/defect)                              │
│  Status: RECEIVED (or PARTIALLY_RECEIVED if multi-GRN)             │
│  Service: Implied in purchase routes                                │
│  StockLedger: Entry created (MOVEMENT_TYPE: receipt)               │
│  Audit: Purchase module, RECEIVE action logged                     │
│                                                                       │
│  If shortage exists:                                                │
│    → Manufacturing order waits for component                        │
│    → Work order blocked until incoming qty available                │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PROCUREMENT REQUEST CLOSURE                      │
│                                                                       │
│  When PO fully received: ProcurementRequest.status = CLOSED        │
│  Stock now available for manufacturing or sales                     │
│  KPI update: Purchase order count metrics                           │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Entities Involved:**
- Vendor → PurchaseOrder → PurchaseOrderLine → Product
- PurchaseOrder → Inventory (incoming/received)
- PurchaseOrder → ProcurementRequest (source linking)
- PurchaseOrder → StockLedger (audit trail)
- PurchaseOrder → AuditLog (who, when, action)

---

### 2.3 Manufacturing Execution (Production Path)

```
┌─────────────────────────────────────────────────────────────────────┐
│               MANUFACTURING ORDER CREATION                          │
│                                                                       │
│  Trigger: Sales demand + Shortage OR Planned replenishment          │
│  Input: Product (finished good), Quantity, Expected date            │
│  Status: DRAFT                                                      │
│  Service: ManufacturingService (routes only)                        │
│                                                                       │
│  During creation:                                                   │
│  1. Product linked to BOM (auto-lookup)                             │
│  2. BOM exploded (list all components needed)                       │
│  3. Shortage calculation for each component                         │
│  4. Procurement requests generated for shortages                    │
│  5. Work orders created from BOM operations                         │
│                                                                       │
│  Example: MO for 10 units of Chair                                  │
│    BOM: 4 legs (shortage: 0), 1 seat (shortage: 5), 1 back (ok)    │
│    → Procurement request: 5 seat components                         │
│    → Work orders: Cut wood, Assemble frame, Upholster, Sand, Paint │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  MANUFACTURING ORDER CONFIRMATION                   │
│                                                                       │
│  Production manager confirms order                                  │
│  Status: CONFIRMED                                                  │
│  Action: Order placed with work centers                             │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   BOM COMPONENT AVAILABILITY CHECK                  │
│                                                                       │
│  Before starting: Verify all components in stock                    │
│                                                                       │
│  For each BOM component:                                            │
│    Inventory lookup by product                                      │
│    Check: on_hand_qty ≥ (qty_per_unit * MO_quantity)               │
│                                                                       │
│  If any shortage:                                                   │
│    → Work order cannot start (blocked)                              │
│    → Awaiting procurement completion                                │
│    → Marked in dashboard as "Material Shortage"                     │
│                                                                       │
│  If all available:                                                  │
│    → Ready for production                                           │
│    → Work orders released to shop floor                             │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
         ┌────────────────────────────────────────────┐
         │  PARALLEL: Procurement execution (see      │
         │  Supplier to Inventory flow)                │
         │  Raw materials arrive → Inventory updated   │
         └────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                 MANUFACTURING ORDER START                           │
│                                                                       │
│  Status: IN_PROGRESS                                                │
│  Timestamp: start_date recorded                                     │
│  Action: Release work orders to work centers                        │
│                                                                       │
│  Per BOM operation:                                                 │
│    Create WorkOrder                                                 │
│    Status: PENDING → IN_PROGRESS → COMPLETED                       │
│    Assign to work center (machine/department)                       │
│    Track times: start_time, end_time, duration_minutes              │
│    Monitor: completion_percent, assigned_user                       │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION EXECUTION                             │
│                                                                       │
│  For each WorkOrder:                                                │
│                                                                       │
│  1. MATERIAL CONSUMPTION:                                           │
│     On work order start:                                            │
│       - Lookup BOM component for this operation                     │
│       - Service: StockService.consume_stock()                       │
│       - on_hand_qty -= required_qty                                 │
│       - StockLedger: MOVEMENT_TYPE = production_consumption         │
│       - Audit: Manufacturing module, CONSUME action                 │
│                                                                       │
│  2. PRODUCTION PROGRESS:                                            │
│     As work completes:                                              │
│       - completion_percent updated                                  │
│       - duration tracked                                            │
│       - Status changes: PENDING → IN_PROGRESS → COMPLETED           │
│                                                                       │
│  3. QUALITY CONTROL:                                                │
│     (If scrap/defects):                                             │
│       - Adjust produced_qty                                         │
│       - Additional StockLedger entries                              │
│       - Scrap tracked separately (MOVEMENT_TYPE = scrap)            │
│                                                                       │
│  4. NEXT OPERATION:                                                 │
│     When WO completes:                                              │
│       - Next WO (by sequence) released                              │
│       - Uses output from previous operation                         │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  MANUFACTURING ORDER COMPLETION                     │
│                                                                       │
│  When all work orders complete:                                     │
│  Status: COMPLETED                                                  │
│  Timestamp: end_date recorded                                       │
│                                                                       │
│  Actions:                                                            │
│  1. Produce qty recorded: produced_qty = sum of actual output       │
│  2. Finished goods added to inventory:                              │
│     Service: StockService.receive_stock()                           │
│     on_hand_qty += produced_qty (for finished product)              │
│     StockLedger: MOVEMENT_TYPE = production_completion              │
│  3. Status: COMPLETED                                               │
│  4. Audit: Manufacturing module, COMPLETE action logged             │
│                                                                       │
│  If produced < ordered:                                             │
│    - Shortage tracked in order                                      │
│    - Additional MO may be created for remainder                     │
│    - Sales order may have partial delivery                          │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  MANUFACTURED GOODS READY FOR SALE                  │
│                                                                       │
│  Finished goods now in Inventory:                                   │
│    on_hand_qty: Available for picking                               │
│    free_to_use_qty: After removing any pre-allocated stock          │
│                                                                       │
│  Linked to Sales Orders: Can fulfill pending sales                  │
│  If safety_stock set: Excess triggers MTS (make-to-stock) flow      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Entities Involved:**
- Product → BOM → BomComponent + BomOperation
- ManufacturingOrder → WorkOrder → WorkCenter
- ManufacturingOrder → Inventory (component reservation)
- WorkOrder → StockLedger (material consumption)
- ManufacturingOrder → AuditLog (lifecycle events)
- ManufacturingOrder → Inventory (finished goods receipt)

---

### 2.4 Dashboard & Analytics Data Aggregation

```
┌─────────────────────────────────────────────────────────────────────┐
│             REAL-TIME DASHBOARD DATA ASSEMBLY                       │
│                                                                       │
│  Queries executed on each dashboard load:                           │
│                                                                       │
│  1. SALES METRICS:                                                   │
│     SELECT SUM(total_amount) WHERE status IN                        │
│       ('delivered', 'closed') AND order_date = this_month           │
│     Result: total_sales_value                                       │
│                                                                       │
│     SELECT COUNT(*) WHERE status IN ('draft', 'confirmed')          │
│     Result: open_orders_count                                       │
│                                                                       │
│  2. INVENTORY METRICS:                                               │
│     SELECT COUNT(*) FROM Inventory                                  │
│     Result: total_stock_items                                       │
│                                                                       │
│     SELECT COUNT(*) WHERE on_hand_qty <= product.safety_stock       │
│     Result: low_stock_items_count                                   │
│                                                                       │
│     SELECT SUM(on_hand_qty * product.cost_price)                    │
│     Result: total_stock_value (asset value)                         │
│                                                                       │
│  3. MANUFACTURING METRICS:                                          │
│     SELECT COUNT(*) WHERE status IN                                 │
│       ('draft', 'confirmed', 'in_progress')                         │
│     Result: active_manufacturing_orders_count                       │
│                                                                       │
│  4. PURCHASE METRICS:                                                │
│     SELECT COUNT(*) WHERE status IN                                 │
│       ('draft', 'confirmed', 'partially_received')                  │
│     Result: open_purchase_orders_count                              │
│                                                                       │
│  5. DELAYED ORDER DETECTION:                                         │
│     SELECT * FROM SalesOrder WHERE                                  │
│       status IN ('draft', 'confirmed') AND                          │
│       expected_date < NOW()                                         │
│     Result: delayed_sales_orders (late delivery risk)               │
│                                                                       │
│     SELECT * FROM PurchaseOrder WHERE                               │
│       status IN ('draft', 'confirmed') AND                          │
│       expected_date < NOW()                                         │
│     Result: delayed_purchase_orders (late receipt risk)             │
│                                                                       │
│  6. PRODUCTION QUEUE:                                                │
│     SELECT * FROM ManufacturingOrder WHERE                          │
│       status IN ('draft', 'confirmed', 'in_progress')               │
│       ORDER BY created_at ASC                                       │
│     Result: manufacturing_queue (FIFO order)                        │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│            DASHBOARD VISUALIZATION (Factory Control Center)         │
│                                                                       │
│  Display organized by operational concern:                          │
│                                                                       │
│  SECTION 1 - Command Panel (Top):                                   │
│    • Total Products: N                                              │
│    • Total Stock Value: Rs X (inventory asset)                      │
│    • Low Stock Items: N (risk alerts)                               │
│    • Free Inventory: N units (available for picking)                │
│                                                                       │
│  SECTION 2 - Sales Queue:                                           │
│    • Open Sales Orders: N                                           │
│    • Delayed Sales Orders: N (red flag)                             │
│    • Table: Order #, Customer, Status, Expected Date, Amount        │
│                                                                       │
│  SECTION 3 - Manufacturing Queue:                                   │
│    • Active Manufacturing Orders: N                                 │
│    • Table: MO #, Product, Qty, Status, Progress, Assignee          │
│                                                                       │
│  SECTION 4 - Purchase Queue:                                        │
│    • Open Purchase Orders: N                                        │
│    • Delayed Purchase Orders: N (red flag)                          │
│    • Table: PO #, Vendor, Status, Expected Date, Amount             │
│                                                                       │
│  SECTION 5 - Low Stock Alerts:                                      │
│    • Products Below Safety Stock: N                                 │
│    • Table: Product Name, SKU, On-Hand, Safety Level, Gap           │
│    • Action: Auto-trigger procurement requests                      │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              KPI SERVICE ANALYTICS CALCULATIONS                      │
│                                                                       │
│  Monthly Revenue:                                                   │
│    = SUM(SalesOrder.total_amount) for delivered/closed this month   │
│                                                                       │
│  Inventory Turnover Ratio:                                          │
│    = COGS / Average Inventory Value                                 │
│    COGS = SUM(PurchaseOrder.total_amount) received                  │
│    Avg Inv = AVG(on_hand_qty * product.cost_price)                 │
│                                                                       │
│  Inventory Velocity:                                                │
│    = Total Stock Value / Days in Period                             │
│    (How fast inventory turns over)                                  │
│                                                                       │
│  Order Fulfillment Rate:                                            │
│    = (Delivered Orders) / (Total Orders) * 100%                     │
│                                                                       │
│  Manufacturing Efficiency:                                          │
│    = (Completed MOs) / (Active MOs) * 100%                          │
│    = (Produced Qty) / (Ordered Qty) * 100%                          │
│                                                                       │
│  Procurement Efficiency:                                            │
│    = (On-time Receipts) / (Total Receipts) * 100%                   │
│                                                                       │
│  Stock Accuracy:                                                    │
│    = (Items w/o variance) / (Total Items) * 100%                    │
│    (tracked via StockLedger)                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. KEY MODELS & RELATIONSHIPS

### 3.1 Core Data Model Diagram

```
                         ┌─────────────┐
                         │   USERS     │
                         │  (username) │
                         └────────┬────┘
                                  │
                        ┌─────────┴──────────┐
                        │                    │
                   ┌────▼────┐          ┌────▼────┐
                   │  ROLES   │          │ AUDIT   │
                   │(name)    │          │ LOGS    │
                   └────┬────┘          └────────┘
                        │
                   ┌────▼──────────┐
                   │ PERMISSIONS   │
                   │ (codename)    │
                   └───────────────┘


         ┌──────────────┐              ┌──────────────┐
         │ CUSTOMERS    │              │   VENDORS    │
         │ (name, addr) │              │ (name, addr) │
         └──────┬───────┘              └──────┬───────┘
                │                             │
                │         ┌───────────────────┤
                │         │                   │
           ┌────▼──┐  ┌───▼────┐       ┌─────▼──────┐
           │SALES  │  │PURCHASE│       │ SUPPLIER   │
           │ORDERS │  │ ORDERS │       │ PRICING    │
           └───┬───┘  └────┬───┘       └────────────┘
               │           │
          ┌────▼───────────▼────┐
          │ SALES/PURCHASE      │
          │ ORDER LINES         │
          └────────┬────────────┘
                   │
           ┌───────▼──────────┐
           │   PRODUCTS       │
           │   (sku, name)    │
           ├──────────────────┤
           │ - cost_price     │
           │ - sales_price    │
           │ - product_type   │
           │ - procurement_   │
           │   type (MTS/MTO) │
           │ - reorder_level  │
           │ - safety_stock   │
           └────────┬─────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌───▼───┐  ┌────▼────┐ ┌────▼──────────┐
    │ BOMS  │  │INVENTORY│ │CATEGORIES    │
    └───┬───┘  └──┬──┬───┘ └──────────────┘
        │         │  │
    ┌───▼─────────┴──▼────┐
    │ BOM COMPONENTS &    │
    │ OPERATIONS          │
    │                     │
    │ BomComponent        │
    │ BomOperation        │
    └─────────────────────┘
        │
    ┌───▼─────────────────────────┐
    │ MANUFACTURING               │
    │                             │
    │ ManufacturingOrder  (MO)    │
    │ └─> work_orders (many)      │
    │     └─> work_center         │
    └─────────────────────────────┘


    ┌──────────────────────────────┐
    │ PROCUREMENT                   │
    │                               │
    │ ProcurementRequest            │
    │ - source_type (vendor/mfg)    │
    │ - source_id (vendor_id/mo_id) │
    │ └─> ProcurementRule           │
    │     └─> ReorderEngine         │
    │     └─> MtsEngine             │
    └──────────────────────────────┘


    ┌──────────────────────────────┐
    │ STOCK TRACKING               │
    │                              │
    │ StockLedger                  │
    │ - movement_type              │
    │   (receipt,consumption,etc)  │
    │ - before_qty / after_qty     │
    │ - user_id (who moved stock)  │
    └──────────────────────────────┘


    ┌──────────────────────────────┐
    │ RETAIL                        │
    │                              │
    │ PosSession (user, balance)   │
    │ └─> PosOrder (cart)          │
    │     └─> PosOrderLine (items) │
    └──────────────────────────────┘
```

### 3.2 Foreign Key Relationships

| Model | Foreign Key | Relationship |
|-------|------------|--------------|
| **SalesOrder** | customer_id | → Customer (many-to-one) |
| | user_id | → User (created_by) |
| **SalesOrderLine** | sales_order_id | → SalesOrder (one-to-many) |
| | product_id | → Product (many-to-one) |
| **PurchaseOrder** | vendor_id | → Vendor (many-to-one) |
| | user_id | → User (created_by) |
| **PurchaseOrderLine** | purchase_order_id | → PurchaseOrder (one-to-many) |
| | product_id | → Product (many-to-one) |
| **Inventory** | product_id | → Product (one-to-one unique) |
| **Product** | category_id | → Category (many-to-one) |
| **BOM** | product_id | → Product (one-to-one) |
| **BomComponent** | bom_id | → BOM (one-to-many) |
| | product_id | → Product (component material) |
| **BomOperation** | bom_id | → BOM (one-to-many) |
| | work_center_id | → WorkCenter |
| **ManufacturingOrder** | product_id | → Product (finished good) |
| | bom_id | → BOM (recipe) |
| | assignee_id | → User |
| **WorkOrder** | mo_id | → ManufacturingOrder (one-to-many) |
| | work_center_id | → WorkCenter (assigned to) |
| | assigned_to | → User |
| **ProcurementRequest** | product_id | → Product |
| | mo_id | → ManufacturingOrder (if source=mfg) |
| | po_id | → PurchaseOrder (if fulfilled) |
| **ProcurementRule** | product_id | → Product |
| | vendor_id | → Vendor (preferred) |
| **PosOrder** | session_id | → PosSession |
| | customer_id | → Customer (optional) |
| **PosOrderLine** | pos_order_id | → PosOrder |
| | product_id | → Product |
| **User** | role_id | → Role (many-to-one) |
| **AuditLog** | user_id | → User |
| **StockLedger** | product_id | → Product |
| | user_id | → User (who moved stock) |

---

## 4. USER WORKFLOWS FOR DIFFERENT ROLES

### 4.1 Sales Manager / Sales User

**Permissions:**
- `view_sales`, `create_sales`, `edit_sales`, `delete_sales`
- `view_inventory` (stock check)
- `view_dashboard` (sales KPIs)

**Daily Workflow:**

```
MORNING:
1. Login → Dashboard
   - Check "Delayed Orders" section
   - Review any cancelled orders from yesterday
   - Identify customers with credit issues

2. Sales Queue Review
   - Click "Sales Orders"
   - Filter by status: DRAFT, CONFIRMED
   - Check expected dates (any overdue?)
   - Prioritize shipments

3. Create New Sales Order
   - Click "+ New Order"
   - Select Customer (or create new)
   - Search products by name/SKU
   - Add items: Product → Quantity → Unit Price (auto-filled) → Add
   - Adjust prices if needed
   - Add notes (special requests?)
   - Save as DRAFT

4. Confirm Order (Release to Warehouse)
   - Find the draft order
   - Review stock availability (shows on form)
   - Click "Confirm" button
   - System reserves stock automatically
   - If insufficient → Alert shown
   - If sufficient → Status → CONFIRMED
   - Customer is notified of confirmation

5. Monitor Status
   - Check "In Progress" tab for picking
   - Verify delivery schedule
   - Update customer on delays
   - Manage special requests

AFTERNOON/END OF DAY:
6. Order Analysis
   - Generate report: Sales by Customer
   - Track total sales value
   - Check profit margins

7. Issues Log
   - Any orders stuck waiting for material?
   - Coordinate with procurement
   - Update customers with realistic dates
```

**Key Interactions:**
- **With Customers:** Creates, confirms, delivers orders
- **With Inventory:** Checks stock before confirmation (reserve_stock)
- **With Manufacturing:** Requests MO when stock unavailable
- **With Procurement:** Escalates shortage to procurement team
- **With Dashboard:** Monitors KPIs (revenue, open orders, delays)

**System Access Points:**
- Sales Orders List (search, filter, pagination)
- Sales Order Form (create/edit)
- Customer Master (lookup, create)
- Inventory Stock View (quick check)
- Dashboard (overview)

---

### 4.2 Purchase Manager / Procurement User

**Permissions:**
- `view_purchases`, `create_purchases`, `edit_purchases`
- `view_procurement_requests`
- `view_inventory`
- `view_dashboard` (purchase KPIs)

**Daily Workflow:**

```
MORNING:
1. Login → Dashboard
   - Check "Purchase Queue" (pending orders)
   - Check "Delayed Orders" in purchases (any overdue?)
   - Review low stock alerts

2. Procurement Requests Review
   - Click "Procurement"
   - View auto-generated requests from:
     * ReorderEngine (low stock)
     * Manufacturing (BOM shortage)
     * MtsEngine (make-to-stock rules)
   - Filter by: Status (OPEN, IN_PROGRESS), Source (vendor/mfg)

3. Vendor Selection
   - For each request:
     * Check preferred vendor in ProcurementRule
     * Compare pricing (if multiple options)
     * Check lead time vs. urgency
     * Consider stock status (immediate vs. 2 weeks)

4. Create Purchase Order
   - Click "+ New Purchase Order"
   - Select Vendor
   - Search procurement requests
   - Add line items from requests:
     * Product → Quantity → Unit Cost (lookup from vendor master)
     * Expected receipt date (vendor lead time + buffer)
   - Review total amount
   - Save as DRAFT
   - Link to procurement requests

5. Confirm Purchase Order
   - Review order details
   - Click "Confirm" button
   - Status → CONFIRMED
   - Inventory updated: incoming_qty += order_qty
   - Vendor notification (email, EDI, etc.)

6. Receipt Management
   - Monitor expected delivery dates
   - If delayed: Escalate to vendor
   - Alert manufacturing if blocking production

MID-DAY:
7. Goods Receipt Processing
   - Receiving team enters GRN (Goods Receipt Note)
   - System matches to PO
   - Accept: Full or Partial receipt
   - Inventory updated:
     * on_hand_qty += received_qty
     * incoming_qty -= received_qty
   - If partial: Mark as PARTIALLY_RECEIVED
   - If complete: Mark as RECEIVED

8. Procurement Request Closure
   - Once PO fully received
   - Mark request as CLOSED
   - Release dependent manufacturing orders

END OF DAY:
9. Analytics
   - Review purchase order metrics:
     * Total PO value (committed spend)
     * Open orders count
     * Overdue count
     * Average lead time by vendor

10. Vendor Performance
    - Track: On-time delivery rate
    - Quality issues (defects, returns)
    - Update vendor ratings
    - Plan vendor reviews
```

**Key Interactions:**
- **With Manufacturing:** Receives requests for BOM components
- **With Inventory:** Tracks incoming stock
- **With Vendors:** Creates, confirms, receives orders
- **With Sales:** Indirect (shortages impact delivery)
- **With Dashboard:** Monitors KPIs (purchase value, delays, vendor perf)

**System Access Points:**
- Procurement Requests List
- Purchase Orders List
- Purchase Order Form (create/edit)
- Vendor Master
- Goods Receipt Entry
- Dashboard (purchase queue, delays)

---

### 4.3 Manufacturing Manager / Production Supervisor

**Permissions:**
- `view_manufacturing`, `create_manufacturing`, `edit_manufacturing`
- `view_inventory` (component check)
- `view_bom`
- `view_dashboard` (production KPIs)

**Daily Workflow:**

```
MORNING STANDUP:
1. Login → Dashboard
   - Check "Manufacturing Queue"
   - Identify blocked MOs (waiting for materials)
   - Check material shortages (alert section)
   - Review production progress

2. Manufacturing Order Queue Review
   - Click "Manufacturing"
   - Filter by status: DRAFT, CONFIRMED, IN_PROGRESS
   - Sort by: Priority (sales deadline), FIFO (created_at)
   - Review for each MO:
     * Ordered qty vs. produced qty (progress)
     * Material availability status
     * Assigned work center capacity
     * Expected completion date

3. Material Shortage Analysis
   - For each BLOCKED MO:
     * View BOM explosion
     * Identify missing component
     * Check procurement status
     * Escalate to procurement if delayed

PRODUCTION RELEASE:
4. Start Manufacturing Order
   - Select CONFIRMED MO
   - Verify all materials in stock
   - If all available:
     * Click "Start"
     * Status → IN_PROGRESS
     * start_date recorded
     * Work orders released to shop floor
   - If shortage:
     * Mark as BLOCKED
     * Notify procurement
     * Move to secondary priority

5. Work Order Assignment
   - View work orders for active MO
   - For each operation (in sequence):
     * Assign to work center
     * Assign to operator/worker
     * Specify expected duration
     * Pass output from previous step as input

MID-PRODUCTION MONITORING:
6. Production Progress Update
   - Throughout day, workers update:
     * Start time for operation
     * % Completion
     * Any issues/delays
     * Expected end time

7. Quality Control
   - If defects identified:
     * Scrap recorded (separate stock ledger)
     * Yield % recalculated
     * Adjust final produced_qty
     * Log in audit trail

8. Component Consumption Tracking
   - As each operation starts:
     * BOM component consumed from inventory
     * on_hand_qty decreases
     * StockLedger entry created
     * Traceability for recalls

COMPLETION & HANDOFF:
9. Manufacturing Order Completion
   - When all work orders finish:
     * Manual: Click "Complete" button
     * Auto: System detects all WO done
     * produced_qty finalized
     * Finished goods added to inventory
     * on_hand_qty += produced_qty (for finished product)
     * Status → COMPLETED
     * Available for sales order fulfillment

10. Yield Analysis
    - Compare: ordered (10) vs. produced (9)
    - Shortfall (1 unit) triggers:
      * Additional MO for remainder, OR
      * Sales order partial delivery

END OF DAY:
11. Dashboard Review
    - Production metrics:
      * Active MOs count
      * Completed today
      * % utilization of work centers
      * Material shortage impact
      * Projected completion dates

12. Next Day Planning
    - Which MOs ready to start?
    - Material availability check
    - Work center capacity plan
    - Priority ranking
```

**Key Interactions:**
- **With Products/BOM:** Accesses recipes (what to make, how)
- **With Inventory:** Checks material availability, consumes stock, receives finished goods
- **With Work Centers:** Assigns work orders
- **With Procurement:** Requests shortages, receives confirmations
- **With Sales:** Fulfills sales order demand
- **With Dashboard:** Monitors production KPIs

**System Access Points:**
- Manufacturing Orders List
- Manufacturing Order Detail (create, start, complete)
- Work Orders List & Form
- BOM View (what's needed?)
- Inventory Stock View (components available?)
- Dashboard (queue, delays, shortages)

---

### 4.4 Warehouse / Inventory Manager

**Permissions:**
- `view_inventory`, `edit_inventory`
- `view_stock_ledger`
- `create_stock_adjustment`
- `create_stock_transfer`
- `view_dashboard` (inventory KPIs)

**Daily Workflow:**

```
MORNING:
1. Login → Dashboard
   - Check low stock alerts
   - Review total inventory value
   - Verify free (unreserved) qty

2. Stock Review
   - Click "Inventory"
   - Search by product name/SKU
   - View for each item:
     * on_hand_qty (physical stock)
     * reserved_qty (allocated to sales)
     * incoming_qty (purchase orders in transit)
     * free_to_use_qty (available for picking)
     * location (warehouse + bin)

PICKING & PACKING:
3. Sales Order Picking
   - View confirmed sales orders awaiting shipment
   - For each order:
     * Locate product in warehouse
     * Pick quantity from shelf
     * Update location if moved
     * Scan barcode to verify

4. Stock Consumption
   - For picking/shipping:
     * Service: StockService.consume_stock()
     * on_hand_qty -= picked_qty
     * reserved_qty -= picked_qty
     * StockLedger entry: MOVEMENT_TYPE = delivery
     * Audit log: Warehouse module, SHIP action

RECEIVING & INSPECTION:
5. Goods Receipt Processing
   - PO arrives from vendor
   - Inspect quality & quantity
   - Match against PO line items
   - Scan barcodes to verify
   - Accept goods or reject (if damage)

6. Goods Receipt Entry
   - Click "Receive Goods" in Purchase Order
   - Enter GRN number
   - Verify quantities
   - Accept as FULL or PARTIAL receipt
   - System updates inventory:
     * on_hand_qty += received_qty
     * incoming_qty -= received_qty
     * StockLedger: MOVEMENT_TYPE = receipt
     * Audit log: Inventory module, RECEIVE action

7. Storage & Putaway
   - Organize goods in warehouse location
   - Update location field in inventory
   - Ensure organized (FIFO, by product category)
   - Mark as "IN STOCK"

MID-DAY:
8. Stock Adjustments
   - Physical inventory discrepancies
   - Damage/breakage on shelf
   - Spillage or loss
   - Click "Stock Adjustment"
   - Select product
   - Enter adjustment quantity (positive/negative)
   - Reason: Damage, Shrinkage, Correction, etc.
   - Apply adjustment
   - System: on_hand_qty +/- qty
   - Audit log: Why adjusted

9. Stock Transfers
   - Between warehouses or locations
   - Click "Stock Transfer"
   - Select product
   - Enter qty
   - Select: From warehouse/location → To warehouse/location
   - Execute
   - System: From location on_hand -= qty, To location += qty
   - StockLedger: MOVEMENT_TYPE = transfer

10. Cycle Counting
    - Periodic spot-checks of sample locations
    - Compare physical count to system on_hand_qty
    - If variance: Create adjustment to correct
    - Build audit trail for accuracy
    - Target: 99%+ accuracy

END OF DAY:
11. Inventory Analytics
    - Click "Reports"
    - Stock value: on_hand_qty × cost_price
    - Low stock report: Items below safety_stock
    - Stock movement: Inbound vs. Outbound
    - Aging: Slow movers (high on-hand for long periods)

12. Stock Ledger Review
    - Click "Stock Ledger"
    - Filter by product or date range
    - Verify all movements logged:
      * Receipts (GRN)
      * Picks/Shipments
      * Adjustments
      * Transfers
    - Spot-check for accuracy
    - Resolve any discrepancies

PERIODIC (Weekly/Monthly):
13. Physical Inventory
    - Count all items in warehouse
    - Compare to on_hand_qty
    - Investigate variances > 1%
    - Perform mass adjustments if needed
    - Generate inventory accuracy report
```

**Key Interactions:**
- **With Sales:** Picks and ships orders (consume_stock)
- **With Procurement:** Receives goods (receive_stock)
- **With Manufacturing:** Tracks component consumption, receives finished goods
- **With Products:** Manages inventory per product
- **With Dashboard:** Monitors stock value, low items, free qty

**System Access Points:**
- Inventory Stock View
- Stock Ledger (history)
- Stock Adjustment Form
- Stock Transfer Form
- Goods Receipt Entry
- Dashboard (stock value, low items, free qty)

---

### 4.5 Finance / Accounting

**Permissions:**
- `view_reports` (all dashboards)
- `view_sales`, `view_purchases`
- `view_inventory` (for valuation)
- `view_audit` (compliance)

**Workflow:**

```
REVENUE RECOGNITION:
1. Monthly Revenue Report
   - Query: SalesOrder.total_amount WHERE status IN ('delivered', 'closed')
     AND order_date in current month
   - Revenue recognized on delivery (when consumed from inventory)
   - Excludes pending/draft/cancelled orders

2. Accounts Receivable
   - Track sales by customer
   - Days sales outstanding (DSO)
   - Credit limit vs. actual exposure
   - Collection aging: Current, 30, 60, 90+ days

COST OF GOODS SOLD (COGS):
3. Purchase Cost Analysis
   - Total purchases received this period
   - Average cost per product
   - Variance analysis (actual vs. budgeted)

4. Inventory Valuation
   - Method: Weighted average cost (from cost_price)
   - Total inventory value: Sum(on_hand_qty * cost_price)
   - Used for balance sheet asset valuation

5. Stock Movement Analysis
   - Inbound value: SUM(StockLedger qty × cost_price) for receipts
   - Outbound value: SUM(StockLedger qty × cost_price) for consumption
   - Variance value: Adjustments + Scrap

PROFITABILITY:
6. Margin Analysis
   - Per product: (sales_price - cost_price) / sales_price
   - Per order: (SalesOrder.subtotal - est. COGS) / subtotal
   - By customer segment

7. Inventory Turnover
   - Calculated: COGS / Average Inventory Value
   - Benchmark: Expected turns per industry
   - Slow movers: Low turnover items → Action needed

COMPLIANCE & AUDIT:
8. Audit Log Review
   - Filter by: Sales, Purchase, Inventory modules
   - Date range: Period being reviewed
   - Critical actions: Discounts, adjustments, deletions
   - Verify: Appropriate approvals, signatures

9. Reconciliation
   - Sales orders: Total delivered = Revenue
   - Purchase orders: Total received = COGS
   - Inventory: System on_hand vs. physical count
   - General ledger tie-in (if accounting system integrated)

REPORTING:
10. Financial Statements
    - Income Statement: Revenue - COGS - OpEx = Net Income
    - Balance Sheet: Inventory asset = on_hand_qty × cost_price
    - Cash Flow: Receivables, Payables, Inventory changes
    - KPI Dashboard: Revenue growth, ROI, margins
```

**Key Interactions:**
- **With Sales:** Revenue from delivered orders
- **With Purchase:** COGS from received orders
- **With Inventory:** Inventory valuation
- **With Audit Logs:** Compliance & traceability
- **With Dashboard:** Financial metrics & KPIs

---

### 4.6 POS Cashier

**Permissions:**
- `view_pos`, `create_pos`

**Workflow:**

```
OPENING:
1. Open POS Session
   - Click "Open Session"
   - Enter starting cash balance (e.g., Rs 1000 float)
   - System generates session_number: POS-00001
   - Status: OPEN
   - Ready to process transactions

SALES TRANSACTIONS:
2. Ring Up Sale (per customer)
   - Create new PosOrder
   - Optional: Select customer (if registered)
   - Add items:
     * Search/scan product
     * Enter quantity
     * System retrieves: unit_price, tax_percent
     * line_total = qty × unit_price × (1 + tax%)
     * Product deducted from on_hand_qty (real-time)
   - Repeat for each item in basket

3. Payment
   - Review order total
   - Select payment method:
     * Cash
     * Card
     * Check
     * Mixed
   - Mark payment_status: PAID
   - Generate receipt_number (auto)
   - Customer leaves with goods

4. Stock Impact
   - Real-time inventory deduction:
     * StockService.consume_stock() for each item
     * on_hand_qty -= sold_qty
     * StockLedger entry: MOVEMENT_TYPE = POS_sale
     * Audit: POS module, SALE action

CLOSING:
5. End of Day - Close Session
   - Click "Close Session"
   - Count actual cash drawer
   - Enter closing_balance
   - System: opening_balance + day_sales = expected_balance
   - Variance calculated (if any)
   - Reconcile discrepancies (cash shortage/overage)
   - Mark session: CLOSED

6. Daily Report
   - Total transactions: N orders
   - Total revenue: Rs X
   - Total tax collected: Rs Y
   - Payment breakdown: Cash Rs, Card Rs, etc.
   - Inventory consumed: N units

PERIODIC:
7. Session History
   - View all sessions (open/closed)
   - Review daily performance
   - Identify high-revenue days
   - Track cash handling accuracy
```

**Key Interactions:**
- **With Products:** Ring up items
- **With Inventory:** Real-time stock deduction
- **With Customers:** Optional loyalty/billing
- **With Finance:** Daily revenue, payment reconciliation

---

### 4.7 Admin / System Administrator

**Permissions:**
- All permissions

**Workflow:**

```
USER MANAGEMENT:
1. Create User
   - Username, email, password
   - Assign role: Sales, Purchase, Manufacturing, Inventory, Finance, Cashier
   - Role grants permissions automatically
   - Set is_active: True/False

2. Manage Roles & Permissions
   - View all roles
   - Edit role: Add/remove permissions
   - Default roles pre-configured:
     * Sales Manager
     * Purchase Manager
     * Manufacturing Manager
     * Warehouse Manager
     * Finance Manager
     * POS Cashier
     * Admin

MASTER DATA:
3. Products Master
   - Create/edit: Name, SKU, Barcode, Category
   - Set pricing: Cost, Sales price
   - Set supply parameters: Reorder level, Safety stock, Lead time
   - Assign BOM (if finished good)

4. Customers & Vendors
   - Create/maintain customer master
   - Set credit limits, addresses, contacts
   - Create/maintain vendor master
   - Track payment terms, lead times, ratings

5. Bills of Materials (BOM)
   - Create BOM for finished goods
   - Add components: Material + Qty required
   - Add operations: Steps + Work center + Cost
   - Calculate total cost automatically

6. Procurement Rules
   - Define procurement strategy per product
   - MTS vs. MTO vs. Reorder
   - Preferred vendor
   - Min/Max quantities

7. Work Centers
   - Create work centers (machines/departments)
   - Assign capacity, hourly rate
   - Link to operations

SYSTEM OPERATIONS:
8. Database Backup & Recovery
   - Regular backups (daily)
   - Recovery procedures
   - Data integrity checks

9. Reports & Exports
   - Generate all standard reports
   - Export to Excel/PDF
   - Schedule automated reports

10. Audit & Compliance
    - Review audit logs
    - Monitor user activity
    - Investigate anomalies
    - Prepare compliance reports (GST, etc.)

11. System Maintenance
    - Monitor performance
    - Clear old logs/data
    - Update configurations
    - Health checks
```

---

## 5. DATA FLOW: ENTRY TO REPORTING

### 5.1 Complete End-to-End Journey (Example: Customer Order to Revenue)

```
TIME: Day 1, Morning
┌────────────────────────────────────────────────────────┐
│ ENTRY POINT: Sales User creates order                  │
│                                                        │
│ Input: Customer "ABC Corp", Items:                     │
│   - Product: Chair (SKU: CHAIR-001)                    │
│     Qty: 100                                           │
│     Unit Price: Rs 5000                                │
│     Tax: 18%                                           │
│   - Product: Table (SKU: TABLE-001)                    │
│     Qty: 50                                            │
│     Unit Price: Rs 8000                                │
│     Tax: 18%                                           │
│                                                        │
│ Order Total: 100×5000 + 50×8000 = Rs 900,000         │
│ Tax: Rs 162,000                                        │
│ Grand Total: Rs 1,062,000                              │
│                                                        │
│ Status: DRAFT                                          │
│ Created at: 2024-06-13 09:30:00                       │
│ Created by: sales_user_1                               │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry #1: Sales module, CREATE action, SO-202406-0042]

┌────────────────────────────────────────────────────────┐
│ SYSTEM STORES: SalesOrder record + SalesOrderLine x2   │
│                                                        │
│ SalesOrder:                                            │
│   id: 42                                               │
│   order_number: "SO-202406-0042"                       │
│   customer_id: 5 (ABC Corp)                            │
│   status: "draft"                                      │
│   subtotal: 900000                                     │
│   tax_amount: 162000                                   │
│   total_amount: 1062000                                │
│   expected_date: 2024-06-20                            │
│   created_at: 2024-06-13 09:30                        │
│   user_id: 3                                           │
│                                                        │
│ SalesOrderLine #1:                                     │
│   product_id: 7 (Chair)                                │
│   quantity: 100                                        │
│   unit_price: 5000                                     │
│   tax_percent: 18                                      │
│   line_total: 500000                                   │
│                                                        │
│ SalesOrderLine #2:                                     │
│   product_id: 8 (Table)                                │
│   quantity: 50                                         │
│   unit_price: 8000                                     │
│   tax_percent: 18                                      │
│   line_total: 400000                                   │
└────────────────────────────────────────────────────────┘

TIME: Day 1, Late Morning
┌────────────────────────────────────────────────────────┐
│ CONFIRMATION WORKFLOW                                  │
│                                                        │
│ Sales user clicks "Confirm Order"                      │
│                                                        │
│ System checks inventory:                               │
│   Query: SELECT * FROM inventories                     │
│     WHERE product_id IN (7, 8)                         │
│                                                        │
│ Results:                                               │
│   Chair (product_id=7):                                │
│     on_hand_qty: 150                                   │
│     reserved_qty: 30                                   │
│     free_to_use_qty: 120                               │
│     Ordered: 100 ✓ SUFFICIENT                          │
│                                                        │
│   Table (product_id=8):                                │
│     on_hand_qty: 40                                    │
│     reserved_qty: 0                                    │
│     free_to_use_qty: 40                                │
│     Ordered: 50 ✗ SHORTAGE!                            │
│     Shortfall: 10 units                                │
│                                                        │
│ Decision: PARTIAL CONFIRMATION                         │
│ - Chair 100 units: Reserve                             │
│ - Table 50 units: Cannot reserve 10 units              │
│                                                        │
│ Option A: Reject order → Not suitable for user        │
│ Option B: Manufacturing request for short 10 units     │
│ Option C: Partial delivery (deliver 40 tables now)     │
│                                                        │
│ System Action: Create manufacturing request            │
│ for 10 tables + safeguard                              │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry #2: Inventory module, RESERVE action]

┌────────────────────────────────────────────────────────┐
│ STOCK RESERVATION                                      │
│                                                        │
│ Service: StockService.reserve_stock()                  │
│                                                        │
│ Chair (product_id=7):                                  │
│   Before: reserved_qty = 30                            │
│   Action: reserved_qty += 100                          │
│   After: reserved_qty = 130                            │
│   on_hand_qty: Still 150 (not yet consumed)            │
│   free_to_use_qty: 150 - 130 = 20                      │
│   StockLedger: MOVEMENT_TYPE = "reservation"          │
│                                                        │
│ Table (product_id=8):                                  │
│   Before: reserved_qty = 0                             │
│   Action: reserved_qty += 40 (only available qty)      │
│   After: reserved_qty = 40                             │
│   on_hand_qty: Still 40                                │
│   free_to_use_qty: 40 - 40 = 0                         │
│   Shortage noted: 10 units need manufacturing          │
│   StockLedger: MOVEMENT_TYPE = "partial_reservation"   │
│                                                        │
│ SalesOrder.status: DRAFT → CONFIRMED                   │
│ Created: Sales order split into:                       │
│   - Order A: 100 chairs + 40 tables (can deliver)      │
│   - Order B: 10 tables (await manufacturing)           │
│   OR                                                   │
│   - Single order with note: "10 tables on backorder"   │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry #3: Sales module, CONFIRM action, SO-202406-0042]

TIME: Day 1, Afternoon
┌────────────────────────────────────────────────────────┐
│ SHORTAGE DETECTED → PROCUREMENT AUTOMATION              │
│                                                        │
│ Trigger: Manufacturing needed for 10 tables            │
│                                                        │
│ System runs: ProcurementEngine.run()                   │
│   Check: Do we have a BOM for Table?                   │
│   Yes → Fetch BOM                                      │
│                                                        │
│ BOM for Table (SKU: TABLE-001):                        │
│   Components needed per 1 table:                       │
│     - Wood (Plywood Sheet): 2 qty @ Rs 2000 = Rs 4000  │
│     - Hardware (Screws pack): 1 qty @ Rs 500 = Rs 500  │
│     - Finish (Varnish): 0.5 ltr @ Rs 1000 = Rs 500    │
│   Total material cost: Rs 5000                         │
│                                                        │
│ For 10 tables needed:                                  │
│   - Wood: 20 sheets                                    │
│   - Hardware: 10 packs                                 │
│   - Finish: 5 liters                                   │
│                                                        │
│ Check inventory of components:                         │
│   Wood: on_hand = 10 (need 20) → Shortage 10          │
│   Hardware: on_hand = 5 (need 10) → Shortage 5        │
│   Finish: on_hand = 2 (need 5) → Shortage 3           │
│                                                        │
│ Generate Procurement Requests:                         │
│   PR-00101: Wood (shortage: 10 units)                  │
│     source_type: "vendor"                              │
│     status: "open"                                     │
│   PR-00102: Hardware (shortage: 5 units)               │
│     source_type: "vendor"                              │
│     status: "open"                                     │
│   PR-00103: Finish (shortage: 3 liters)                │
│     source_type: "vendor"                              │
│     status: "open"                                     │
│                                                        │
│ Alert sent to procurement manager:                     │
│   "3 procurement requests created for sales order"     │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry #4: Procurement module, REQUEST_CREATED x3]

TIME: Day 1-2, Evening
┌────────────────────────────────────────────────────────┐
│ PURCHASE ORDER CREATION (By Procurement Manager)        │
│                                                        │
│ Procurement manager reviews requests                   │
│ Selects vendor: "Timber Corp" (preferred for wood)     │
│                                                        │
│ Creates Purchase Order:                                │
│   PO-202406-0015: Timber Corp                          │
│     - Wood: 15 sheets (qty ordered = shortage 10 + buffer 5)      │
│     - Hardware: 10 packs                               │
│     - Finish: 5 liters                                 │
│     Total: Rs 45,000                                   │
│     Expected delivery: 2024-06-15 (lead time 2 days)  │
│     Status: DRAFT                                      │
│                                                        │
│ Procurement Requests linked:                           │
│   PR-00101.po_id = PO-202406-0015                      │
│   PR-00102.po_id = PO-202406-0015                      │
│   PR-00103.po_id = PO-202406-0015                      │
│   All: status = "in_progress"                          │
│                                                        │
│ System updates Inventory (incoming):                   │
│   Wood:                                                │
│     Before: incoming_qty = 0                           │
│     After: incoming_qty = 15                           │
│   Hardware:                                            │
│     After: incoming_qty = 10                           │
│   Finish:                                              │
│     After: incoming_qty = 5                            │
│                                                        │
│ PurchaseOrder.status: DRAFT → CONFIRMED               │
│ Vendor notified of order                               │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry #5: Purchase module, CREATE, PO-202406-0015]
[AuditLog Entry #6: Purchase module, CONFIRM, PO-202406-0015]

TIME: Day 2, Morning
┌────────────────────────────────────────────────────────┐
│ DASHBOARD SNAPSHOT (at this point)                     │
│                                                        │
│ Factory Control Center shows:                          │
│                                                        │
│ Sales Queue:                                           │
│   Open Orders: 1 (SO-202406-0042)                      │
│   Value: Rs 1,062,000                                  │
│   Status: CONFIRMED (waiting for manufacturing)       │
│                                                        │
│ Manufacturing Queue:                                  │
│   Pending: 0 (waiting for materials)                  │
│                                                        │
│ Material Shortages:                                    │
│   Wood: -10 sheets                                     │
│   Hardware: -5 packs                                   │
│   Finish: -3 liters                                    │
│                                                        │
│ Purchase Queue:                                        │
│   Open Orders: 1 (PO-202406-0015)                      │
│   Value: Rs 45,000                                     │
│   Expected: 2024-06-15                                 │
│   Status: CONFIRMED (ordered from vendor)             │
│                                                        │
│ Inventory Value:                                       │
│   Total on-hand: Rs 2,500,000                          │
│   Free (unreserved): Rs 1,800,000                      │
│   Reserved: Rs 700,000 (for sales orders)              │
│   Low stock items: 2                                   │
└────────────────────────────────────────────────────────┘

TIME: Day 3 (Delivery Day)
┌────────────────────────────────────────────────────────┐
│ GOODS RECEIPT (Purchase Order)                         │
│                                                        │
│ Vendor delivers: Wood (15), Hardware (10), Finish (5)  │
│ Warehouse team inspects, accepts goods                 │
│                                                        │
│ System processes GRN (Goods Receipt Note):             │
│   PO-202406-0015 → Receive                             │
│                                                        │
│ Inventory updated (all components):                    │
│   Wood:                                                │
│     Before: on_hand = 10, incoming = 15                │
│     After: on_hand = 25, incoming = 0                  │
│     StockLedger: MOVEMENT_TYPE = "receipt", qty +15   │
│                                                        │
│   Hardware:                                            │
│     Before: on_hand = 5, incoming = 10                 │
│     After: on_hand = 15, incoming = 0                  │
│     StockLedger: MOVEMENT_TYPE = "receipt", qty +10   │
│                                                        │
│   Finish:                                              │
│     Before: on_hand = 2, incoming = 5                  │
│     After: on_hand = 7, incoming = 0                   │
│     StockLedger: MOVEMENT_TYPE = "receipt", qty +5    │
│                                                        │
│ PurchaseOrder.status: CONFIRMED → RECEIVED            │
│ ProcurementRequests: status = "closed"                │
│ Alert sent to Manufacturing: "Materials ready"         │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry #7: Inventory module, RECEIVE, PO-202406-0015]

TIME: Day 3, Afternoon
┌────────────────────────────────────────────────────────┐
│ MANUFACTURING ORDER CREATION                           │
│                                                        │
│ Manufacturing manager notified of material availability│
│                                                        │
│ Creates Manufacturing Order for Tables:                │
│   MO-00089: Table                                      │
│   Product: Table (SKU: TABLE-001)                      │
│   Quantity: 10 units                                   │
│   BOM: Table BOM v1.0 (linked)                         │
│   Status: DRAFT                                        │
│                                                        │
│ Generates Work Orders from BOM operations:             │
│   WO-00289: Cut Wood (Sequence 1)                      │
│     Work center: Wood Shop                             │
│   WO-00290: Assemble Frame (Sequence 2)               │
│     Work center: Assembly Line                         │
│   WO-00291: Add Hardware (Sequence 3)                 │
│     Work center: Hardware Station                      │
│   WO-00292: Apply Finish (Sequence 4)                 │
│     Work center: Finishing Booth                       │
│   WO-00293: Quality Check (Sequence 5)                │
│     Work center: QC Station                            │
│                                                        │
│ Check component availability:                          │
│   Wood: need 20, have 25 ✓                             │
│   Hardware: need 10, have 15 ✓                         │
│   Finish: need 5, have 7 ✓                             │
│   All available → Ready to start                       │
│                                                        │
│ MO.status: DRAFT → CONFIRMED                           │
│ Release work orders to shop floor                      │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry #8: Manufacturing module, CREATE, MO-00089]

TIME: Day 3-4, Production (4 hours total)
┌────────────────────────────────────────────────────────┐
│ WORK ORDER EXECUTION & STOCK CONSUMPTION               │
│                                                        │
│ 10:00 AM: WO-00289 Starts (Cut Wood)                  │
│   Worker starts operation                              │
│   System trigger: Consume wood from inventory          │
│                                                        │
│   StockService.consume_stock(product_id=1, qty=20)    │
│   Wood inventory:                                      │
│     Before: on_hand = 25                               │
│     After: on_hand = 5                                 │
│     reserved_qty: stays 0 (manufacturing allocation)   │
│     StockLedger:                                       │
│       MOVEMENT_TYPE: "production_consumption"          │
│       quantity: -20                                    │
│       before_qty: 25                                   │
│       after_qty: 5                                     │
│       user_id: operator_3                              │
│       created_at: 2024-06-13 10:00                    │
│   Audit: Manufacturing, CONSUME, MO-00089, wood -20   │
│                                                        │
│ 11:30 AM: WO-00289 Completes                          │
│   Status: COMPLETED                                    │
│   Output: 10 units of "cut wood"                      │
│   Next: WO-00290 released                              │
│                                                        │
│ 12:00 PM: WO-00290 Starts (Assemble Frame)            │
│   Worker starts, takes cut wood from previous step    │
│   System trigger: Consume hardware                     │
│                                                        │
│   StockService.consume_stock(product_id=2, qty=10)    │
│   Hardware inventory:                                  │
│     Before: on_hand = 15                               │
│     After: on_hand = 5                                 │
│     StockLedger: MOVEMENT_TYPE = "production_consumption",│
│       quantity: -10                                    │
│   Audit: Manufacturing, CONSUME, MO-00089, hardware -10│
│                                                        │
│ 2:00 PM: WO-00291 Completes (Assemble Frame)         │
│   Status: COMPLETED                                    │
│   Output: 10 units of "assembled table frame"         │
│   Next: WO-00291 released                              │
│                                                        │
│ 3:00 PM: WO-00291 Starts (Add Hardware)                │
│   ... (repeats for each operation)                     │
│                                                        │
│ 4:30 PM: WO-00293 Completes (Quality Check)            │
│   Status: COMPLETED                                    │
│   Final output: 10 tables (100% produced)              │
│   manufactured_order.produced_qty = 10                 │
│   All work orders now COMPLETED                        │
└────────────────────────────────────────────────────────┘
                        ↓
[Multiple AuditLog entries: CONSUME for each material]

TIME: Day 4, Morning
┌────────────────────────────────────────────────────────┐
│ MANUFACTURING ORDER COMPLETION                         │
│                                                        │
│ System detects all work orders completed               │
│ MO.status: IN_PROGRESS → COMPLETED                     │
│ MO.produced_qty = 10 (actual output)                   │
│ MO.end_date = 2024-06-14 17:30                        │
│                                                        │
│ Add finished goods to inventory:                       │
│   Table (product_id=8):                                │
│     Before: on_hand = 40, reserved = 40               │
│     Produce: 10 units                                 │
│     After: on_hand = 50                                │
│     reserved_qty stays = 40 (already allocated to SO)  │
│     free_to_use_qty = 50 - 40 = 10                    │
│     StockLedger:                                       │
│       MOVEMENT_TYPE: "production_completion"           │
│       quantity: +10                                    │
│       before_qty: 40                                   │
│       after_qty: 50                                    │
│   Audit: Manufacturing, COMPLETE, MO-00089            │
│                                                        │
│ Consumption summary for costing:                       │
│   Wood consumed: 20 units                              │
│   Hardware consumed: 10 units                          │
│   Finish consumed: 5 liters                            │
│   Cost of goods manufactured: Rs 50,000 (10 × 5000)   │
│   These costs will flow to inventory valuation         │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry: Manufacturing, COMPLETE, MO-00089]

TIME: Day 4, Afternoon
┌────────────────────────────────────────────────────────┐
│ SALES ORDER FULFILLMENT & DELIVERY                     │
│                                                        │
│ Sales order SO-202406-0042 status check:               │
│   Chair: 100 units reserved, 150 on_hand ✓             │
│   Table: 50 units reserved, now 50 on_hand ✓           │
│   (Was 40 from stock + 10 from manufacturing)          │
│   All items available!                                 │
│                                                        │
│ Warehouse picks items:                                 │
│   - Chair: Pick 100 units                              │
│   - Table: Pick 50 units                               │
│   - Stage for shipment                                 │
│                                                        │
│ Sales confirms delivery:                               │
│   Click "Deliver Order" → SO-202406-0042              │
│                                                        │
│ System consumes reserved stock:                        │
│   Service: StockService.consume_stock() for each line  │
│                                                        │
│   Chair:                                               │
│     Before: on_hand = 150, reserved = 130              │
│     Action: Consume 100 units                          │
│     After: on_hand = 50, reserved = 30                 │
│     free_to_use_qty = 50 - 30 = 20                     │
│     StockLedger:                                       │
│       MOVEMENT_TYPE: "delivery"                        │
│       quantity: -100                                   │
│       Audit: Sales, DELIVER, SO-202406-0042, chair -100│
│                                                        │
│   Table:                                               │
│     Before: on_hand = 50, reserved = 40                │
│     Action: Consume 50 units                           │
│     After: on_hand = 0, reserved = 0                   │
│     free_to_use_qty = 0                                │
│     StockLedger:                                       │
│       MOVEMENT_TYPE: "delivery"                        │
│       quantity: -50                                    │
│       Audit: Sales, DELIVER, SO-202406-0042, table -50 │
│                                                        │
│ SalesOrder.status: CONFIRMED → DELIVERED              │
│ SalesOrder.delivery_date = 2024-06-14 15:00            │
│ Customer receives goods                                │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry: Sales, DELIVER, SO-202406-0042]

TIME: Day 4, Evening
┌────────────────────────────────────────────────────────┐
│ ORDER CLOSURE & REVENUE RECOGNITION                    │
│                                                        │
│ SalesOrder.status: DELIVERED → CLOSED                  │
│ SalesOrder.delivery_date recorded                      │
│                                                        │
│ Financial Impact:                                      │
│   Revenue (for accounting):                            │
│     = SalesOrder.total_amount = Rs 1,062,000           │
│     Recognized on delivery date (2024-06-14)           │
│     Customer billed & invoiced                         │
│                                                        │
│   Cost of Goods Sold (COGS):                           │
│     Chair: 100 × cost_price(5000) = Rs 500,000        │
│     Table: 50 × cost_price(5000) = Rs 250,000         │
│     Total COGS = Rs 750,000                            │
│                                                        │
│   Gross Profit:                                        │
│     = Revenue - COGS                                   │
│     = Rs 1,062,000 - Rs 750,000                        │
│     = Rs 312,000                                       │
│     Gross Margin = 29.4%                               │
│                                                        │
│   Inventory Value Change:                              │
│     Before: Total value included these goods           │
│     After: Goods moved from asset to expense (COGS)    │
└────────────────────────────────────────────────────────┘
                        ↓
[AuditLog Entry: Sales, CLOSE, SO-202406-0042]

TIME: End of Day 4 (Dashboard Refresh)
┌────────────────────────────────────────────────────────┐
│ ANALYTICS & KPI UPDATE                                 │
│                                                        │
│ Dashboard recalculates all metrics:                    │
│                                                        │
│ MONTHLY REVENUE:                                       │
│   Query: SELECT SUM(total_amount)                      │
│     WHERE status IN ('delivered', 'closed')            │
│     AND DATE_FORMAT(order_date, '%Y-%m') = '2024-06'   │
│   Result: Rs 1,062,000 + (previous orders)             │
│   Trend: Up 15% vs. May                                │
│                                                        │
│ INVENTORY TURNOVER:                                    │
│   COGS this month: Rs 750,000 (this order) + others   │
│   Average inventory value: Rs 2,400,000                │
│   Turnover = COGS / Avg Inv = 0.31 (annualized: 3.75) │
│                                                        │
│ SALES PERFORMANCE:                                     │
│   Open orders: 0 (SO-202406-0042 closed)               │
│   Delayed orders: 0 (delivered on time)                │
│   Completed orders: 1                                  │
│   Fulfillment rate: 100%                               │
│                                                        │
│ MANUFACTURING EFFICIENCY:                              │
│   MOs completed: 1 (MO-00089)                          │
│   Produced qty: 10, Ordered qty: 10                    │
│   Yield: 100%                                          │
│   Lead time: 1.5 days (from MO create to delivery)    │
│                                                        │
│ INVENTORY BALANCE:                                     │
│   Before transactions: Rs 2,500,000                    │
│   Purchased: +Rs 45,000 (PO)                           │
│   Manufactured: +Rs 50,000 (10 tables)                 │
│   Sold: -Rs 750,000 (COGS)                             │
│   Current value: Rs 1,845,000                          │
│   Change: -26.2%                                       │
│                                                        │
│ PURCHASE ORDER METRICS:                                │
│   Completed: 1 (PO-202406-0015)                        │
│   On-time delivery: Yes (2 days as expected)           │
│   Vendor performance score: +1                         │
│                                                        │
│ ALERTS & ACTIONS:                                      │
│   Low stock: None (resupplied by PO)                   │
│   Delayed orders: None                                 │
│   Material shortages: None (all fulfilled)             │
│   Next action: Replenish chairs (now at 50 from 150)   │
│   Recommendation: Create reorder for chairs            │
└────────────────────────────────────────────────────────┘
```

**Key Observations:**

1. **Complete Traceability:** Every action logged in AuditLog
   - Who: User ID (sales_user, operator, etc.)
   - When: Timestamp of each action
   - What: Module + Action + Entity changed
   - Before/After: Old values vs. new values

2. **Data Relationships Intact:**
   - SalesOrder → SalesOrderLine → Product
   - Inventory updated at every stage
   - StockLedger maintains history
   - Audit trail connects all changes

3. **Financial Accuracy:**
   - Revenue recognized on delivery (not just creation)
   - COGS calculated from actual consumed materials
   - Inventory value updated dynamically

4. **Operational Visibility:**
   - Dashboard shows current state at any moment
   - Delays, shortages, queue depths all visible
   - Enables real-time decision-making

5. **Multi-Process Parallel Execution:**
   - Sales, Manufacturing, Procurement happen independently but linked
   - Dashboard shows combined impact
   - Bottlenecks (material shortages) visible for action

---

## SUMMARY: DATA ARCHITECTURE

### Information Flows:
```
INBOUND (Demand):
Customer → Sales Order → Inventory Check → Stock Reservation/Shortage → Manufacturing Request → Procurement → Vendor

OUTBOUND (Fulfillment):
Vendor → Purchase Order → Goods Receipt → Inventory Update → Sales Fulfillment → Delivery → Revenue

REPORTING:
All transactions → StockLedger + AuditLog → Analytics → Dashboard + KPIs → Management Decisions
```

### Key Databases:
- **Transactional:** Products, Customers, Vendors, SalesOrders, PurchaseOrders, ManufacturingOrders
- **Inventory:** Inventory (current state), StockLedger (history)
- **Audit:** AuditLog (who/when/what), Permissions (access control)
- **Rules:** ProcurementRules, BOMs, WorkCenters (configuration)

### Data Quality Assurance:
- **Constraints:** Foreign keys ensure referential integrity
- **Audit Trail:** Every change logged with before/after values
- **Reconciliation:** StockLedger vs. Inventory balance
- **Accuracy Targets:** 99%+ inventory match, 100% order traceability

---

This completes the comprehensive NexusERP architecture analysis.
