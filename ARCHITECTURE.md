# NexusERP Architecture Specification

## Intelligent Demand-to-Delivery Manufacturing ERP

---

# 1. System Architecture

NexusERP follows a layered architecture that separates presentation, application logic, domain services, persistence, and database storage.

```mermaid
flowchart TD

    UI["Presentation Layer<br/>HTML5 • Bootstrap 5.3 • Jinja2 • JavaScript"]

    ROUTES["API Layer<br/>Flask Blueprints<br/>WTForms Validation<br/>Permission Middleware"]

    SERVICES["Business Service Layer<br/>Sales Service<br/>Inventory Service<br/>Purchase Service<br/>Manufacturing Service<br/>Procurement Engine<br/>Analytics Engine<br/>AI Copilot"]

    MODELS["Data Access Layer<br/>SQLAlchemy ORM Models"]

    DB["Database Layer<br/>SQLite<br/>Alembic Migrations"]

    UI --> ROUTES
    ROUTES --> SERVICES
    SERVICES --> MODELS
    MODELS --> DB
```

---

# 2. Component Architecture

```mermaid
flowchart LR

    User["User"]

    Dashboard["Dashboard"]
    Sales["Sales"]
    Purchase["Purchase"]
    Inventory["Inventory"]
    Manufacturing["Manufacturing"]
    POS["POS"]
    Reports["Analytics"]
    AI["AI Copilot"]

    User --> Dashboard
    User --> Sales
    User --> Purchase
    User --> Inventory
    User --> Manufacturing
    User --> POS
    User --> Reports
    User --> AI

    Sales --> Inventory
    Purchase --> Inventory
    Manufacturing --> Inventory
    Manufacturing --> Purchase
    Sales --> Manufacturing

    Inventory --> Reports
    Sales --> Reports
    Purchase --> Reports
    Manufacturing --> Reports
```

---

# 3. Folder Structure

```text
app/
│
├── extensions/
│   ├── db.py
│   ├── login_manager.py
│   ├── bcrypt.py
│   └── socketio.py
│
├── models/
│   ├── user.py
│   ├── role.py
│   ├── permission.py
│   ├── product.py
│   ├── inventory.py
│   ├── stock_ledger.py
│   ├── sales_order.py
│   ├── purchase_order.py
│   ├── bom.py
│   ├── manufacturing_order.py
│   └── audit_log.py
│
├── routes/
│   ├── auth/
│   ├── dashboard/
│   ├── inventory/
│   ├── sales/
│   ├── purchase/
│   ├── manufacturing/
│   ├── reports/
│   ├── pos/
│   └── ai/
│
├── services/
│   ├── auth/
│   ├── inventory/
│   ├── sales/
│   ├── purchase/
│   ├── manufacturing/
│   ├── procurement/
│   ├── analytics/
│   ├── audit/
│   └── ai/
│
├── templates/
├── static/
├── utils/
├── migrations/
└── seed/
```

---

# 4. Database Entity Relationship Diagram

```mermaid
erDiagram

    USER {
        int id PK
        string username
        string email
        string password_hash
    }

    ROLE {
        int id PK
        string name
    }

    PERMISSION {
        int id PK
        string code
    }

    PRODUCT {
        int id PK
        string sku
        string name
        string barcode
        float cost_price
        float sales_price
    }

    INVENTORY {
        int id PK
        int product_id FK
        int on_hand_qty
        int reserved_qty
        int incoming_qty
        int outgoing_qty
    }

    STOCK_LEDGER {
        int id PK
        int product_id FK
        string movement_type
        int quantity
        datetime created_at
    }

    CUSTOMER {
        int id PK
        string name
    }

    SALES_ORDER {
        int id PK
        string order_number
        string status
        float total_amount
    }

    SALES_ORDER_LINE {
        int id PK
        int quantity
        float unit_price
    }

    VENDOR {
        int id PK
        string name
    }

    PURCHASE_ORDER {
        int id PK
        string order_number
        string status
    }

    PURCHASE_ORDER_LINE {
        int id PK
        int quantity
        float unit_cost
    }

    BOM {
        int id PK
        string name
    }

    BOM_COMPONENT {
        int id PK
        int quantity
    }

    MANUFACTURING_ORDER {
        int id PK
        string mo_number
        string status
    }

    WORK_ORDER {
        int id PK
        string operation_name
        string status
    }

    AUDIT_LOG {
        int id PK
        string action
        string module
    }

    USER ||--o{ AUDIT_LOG : creates
    USER }o--o{ ROLE : assigned
    ROLE }o--o{ PERMISSION : contains

    PRODUCT ||--|| INVENTORY : owns
    PRODUCT ||--o{ STOCK_LEDGER : generates
    PRODUCT ||--o{ SALES_ORDER_LINE : sold
    PRODUCT ||--o{ PURCHASE_ORDER_LINE : purchased
    PRODUCT ||--o{ BOM_COMPONENT : component

    CUSTOMER ||--o{ SALES_ORDER : places
    SALES_ORDER ||--o{ SALES_ORDER_LINE : contains

    VENDOR ||--o{ PURCHASE_ORDER : receives
    PURCHASE_ORDER ||--o{ PURCHASE_ORDER_LINE : contains

    BOM ||--o{ BOM_COMPONENT : contains
    BOM ||--o{ MANUFACTURING_ORDER : used_in

    MANUFACTURING_ORDER ||--o{ WORK_ORDER : contains
```

---

# 5. Demand-to-Delivery Workflow

```mermaid
sequenceDiagram

    actor Customer

    participant Sales
    participant Inventory
    participant Manufacturing
    participant Ledger

    Customer->>Sales: Create Sales Order

    Sales->>Inventory: Check Stock Availability

    alt Stock Available

        Inventory-->>Sales: Available

        Sales->>Inventory: Reserve Stock

        Sales->>Sales: Confirm Order

    else Stock Shortage

        Inventory-->>Sales: Shortage

        Sales->>Manufacturing: Create Manufacturing Order

    end

    Sales->>Inventory: Deliver Goods

    Inventory->>Ledger: Record Stock Movement

    Inventory->>Inventory: Reduce On-Hand Quantity

    Sales->>Customer: Complete Delivery
```

---

# 6. Smart Procurement Workflow

```mermaid
sequenceDiagram

    participant ProcurementEngine
    participant Inventory
    participant PurchaseOrder
    participant Supplier

    loop Scheduled Check

        ProcurementEngine->>Inventory: Check Reorder Levels

        alt Below Threshold

            ProcurementEngine->>PurchaseOrder: Generate Draft PO

        end

    end

    PurchaseOrder->>Supplier: Send Purchase Order

    Supplier-->>PurchaseOrder: Ship Materials

    PurchaseOrder->>Inventory: Receive Stock

    Inventory->>Inventory: Increase On-Hand Quantity

    Inventory->>Inventory: Reduce Incoming Quantity
```

---

# 7. Manufacturing Workflow

```mermaid
sequenceDiagram

    actor ProductionManager

    participant MO
    participant BOM
    participant Inventory
    participant WorkOrder

    ProductionManager->>MO: Create Manufacturing Order

    MO->>BOM: Load Components

    BOM-->>MO: Components List

    MO->>Inventory: Check Components

    alt Components Available

        Inventory-->>MO: Available

        MO->>Inventory: Reserve Components

    else Components Missing

        MO->>Inventory: Trigger Procurement

    end

    MO->>WorkOrder: Generate Tasks

    WorkOrder->>Inventory: Consume Components

    WorkOrder->>MO: Complete Production

    MO->>Inventory: Add Finished Product

    MO->>MO: Mark Completed
```

---

# 8. Inventory Movement Architecture

```mermaid
flowchart LR

    PurchaseReceipt["Purchase Receipt"]
    ProductionOutput["Manufacturing Output"]
    SalesDelivery["Sales Delivery"]
    StockAdjustment["Stock Adjustment"]

    Inventory["Inventory Balance"]

    Ledger["Stock Ledger"]

    PurchaseReceipt --> Inventory
    ProductionOutput --> Inventory

    Inventory --> SalesDelivery

    StockAdjustment --> Inventory

    Inventory --> Ledger
```

---

# 9. Role-Based Access Control (RBAC)

```mermaid
flowchart TD

    Admin["System Admin"]
    Owner["Business Owner"]
    Sales["Sales Representative"]
    Purchase["Purchasing Agent"]
    Inventory["Inventory Manager"]
    Production["Production Manager"]
    Cashier["POS Cashier"]

    Permissions["Permissions"]

    Admin --> Permissions
    Owner --> Permissions
    Sales --> Permissions
    Purchase --> Permissions
    Inventory --> Permissions
    Production --> Permissions
    Cashier --> Permissions
```

---

# 10. Audit Logging Architecture

```mermaid
flowchart TD

    UserAction["User Action"]

    Service["Business Service"]

    AuditEngine["Audit Engine"]

    AuditTable["Audit Log Table"]

    UserAction --> Service

    Service --> AuditEngine

    AuditEngine --> AuditTable
```

---

# 11. AI Copilot Architecture

```mermaid
flowchart TD

    User["User Query"]

    Intent["Intent Parser"]

    Context["Context Builder"]

    Database["ERP Database"]

    Gemini["Gemini AI"]

    Response["Business Insights"]

    User --> Intent

    Intent --> Context

    Context --> Database

    Database --> Context

    Context --> Gemini

    Gemini --> Response
```

---

# 12. Complete Module Interaction Diagram

```mermaid
flowchart TD

    Sales["Sales"]

    Purchase["Purchase"]

    Manufacturing["Manufacturing"]

    Inventory["Inventory"]

    Warehouse["Warehouse"]

    Procurement["Procurement Engine"]

    POS["POS"]

    Analytics["Analytics"]

    AI["AI Copilot"]

    Sales --> Inventory

    Inventory --> Procurement

    Procurement --> Purchase

    Purchase --> Inventory

    Manufacturing --> Inventory

    Inventory --> Warehouse

    POS --> Inventory

    Inventory --> Analytics

    Sales --> Analytics

    Purchase --> Analytics

    Manufacturing --> Analytics

    Analytics --> AI
```
