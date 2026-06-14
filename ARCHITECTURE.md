# NexusERP Architecture

## Intelligent Demand-to-Delivery Manufacturing Operating System

---

# 1. High-Level System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                      │
│                                                             │
│  • Bootstrap 5.3 UI                                         │
│  • Jinja Templates                                          │
│  • Chart.js Dashboards                                      │
│  • POS Terminal                                             
│  • AI Copilot Interface                                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
│                                                             │
│  Flask Blueprints                                           │
│  • Authentication                                           │
│  • Dashboard                                                │
│  • Products                                                 │
│  • Inventory                                                │
│  • Sales                                                    │
│  • Procurement                                              │
│  • Manufacturing                                            │
│  • POS                                                      │
│  • Reports                                                  │
│  • AI Copilot                                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│                                                             │
│  Auth Service                                               │
│  Inventory Service                                          │
│  Sales Service                                              │
│  Purchase Service                                           │
│  Manufacturing Service                                      │
│  Procurement Engine                                         │
│  POS Service                                                │
│  Analytics Service                                          │
│  Audit Service                                              │
│  AI Copilot Service                                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     Persistence Layer                       │
│                                                             │
│  SQLAlchemy ORM                                             │
│  Database Models                                            │
│  Repositories                                               │
│  Query Services                                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                       Database Layer                        │
│                                                             │
│  SQLite                                                     │
│  Flask-Migrate                                              │
│  Alembic                                                    │
└─────────────────────────────────────────────────────────────┘
```

---

# 2. Module Architecture

```text
                           NexusERP
                               │
      ┌────────────────────────┼────────────────────────┐
      │                        │                        │
      ▼                        ▼                        ▼

 Product & Inventory      Sales Management      Purchase Management
      │                        │                        │
      │                        │                        │
      ▼                        ▼                        ▼

 Stock Ledger          Sales Orders           Purchase Orders
 Stock Adjustment      Reservations           Goods Receipts
 Reorder Rules         Risk Predictor         Supplier Management

      └────────────────────────┼────────────────────────┘
                               │
                               ▼

                    Manufacturing Management

                               │

                ┌──────────────┼──────────────┐
                │              │              │

                ▼              ▼              ▼

             BOM          Work Orders      Kanban Board

                               │
                               ▼

                        Finished Goods

                               │
                               ▼

                         Inventory

                               │
                               ▼

                        Analytics Layer

                               │
                               ▼

                         AI Copilot
```

---

# 3. Request Flow Architecture

```text
User Request
     │
     ▼
Browser UI
     │
     ▼
Flask Blueprint
     │
     ▼
Permission Validation
     │
     ▼
Business Service
     │
     ▼
SQLAlchemy Models
     │
     ▼
SQLite Database
     │
     ▼
Response Returned
     │
     ▼
Dashboard Update
```

---

# 4. Inventory Architecture

```text
                 PRODUCT

                     │

     ┌───────────────┼───────────────┐

     ▼               ▼               ▼

 On-Hand         Reserved        Incoming

     │               │               │

     └───────────────┼───────────────┘
                     │

                     ▼

              Free To Use

       Free = OnHand - Reserved

                     │

                     ▼

              Stock Ledger

                     │

                     ▼

         Complete Audit Trail
```

---

# 5. Demand-to-Delivery Workflow

```text
Customer Order
      │
      ▼

Sales Order Created
      │
      ▼

Inventory Check
      │
      ├──────── Stock Available ────────┐
      │                                 │
      ▼                                 │

Reserve Inventory                       │
      │                                 │
      ▼                                 │

Delivery                                │
      │                                 │
      ▼                                 │

Stock Consumption                       │
      │                                 │
      ▼                                 │

Order Completed                         │
                                        │
      └──── Stock Shortage ─────────────┘
                    │
                    ▼

         Manufacturing Order

                    │
                    ▼

            Product Produced

                    │
                    ▼

              Inventory Updated
```

---

# 6. Procurement Architecture

```text
Inventory Monitoring
        │
        ▼

Check Reorder Level
        │
        ▼

Below Threshold?
        │
   ┌────┴────┐
   │         │

  No        Yes
   │         │
   │         ▼

   │   Create Purchase Order
   │         │
   │         ▼

   │   Select Supplier
   │         │
   │         ▼

   │   Receive Goods
   │         │
   │         ▼

   │   Update Inventory
   │
   ▼

Continue Monitoring
```

---

# 7. Manufacturing Architecture

```text
Manufacturing Order
        │
        ▼

Load BOM
        │
        ▼

Check Components
        │
        ▼

Reserve Materials
        │
        ▼

Generate Work Orders
        │
        ▼

Assembly
        │
        ▼

Painting
        │
        ▼

Packaging
        │
        ▼

Finished Goods
        │
        ▼

Inventory Update
```

---

# 8. POS Architecture

```text
Cashier Login
      │
      ▼

Open Session
      │
      ▼

Scan Products
      │
      ▼

Inventory Validation
      │
      ▼

Calculate Taxes
      │
      ▼

Payment Processing
      │
      ▼

Generate Receipt
      │
      ▼

Update Inventory
      │
      ▼

Update Session Sales
      │
      ▼

Close Session
```

---

# 9. AI Copilot Architecture

```text
User Question
      │
      ▼

Intent Parser
      │
      ▼

Context Builder
      │
      ▼

ERP Database Queries
      │
      ▼

Business Context
      │
      ▼

Google Gemini
      │
      ▼

Operational Insights
      │
      ▼

Recommendations
```

---

# 10. Security Architecture

```text
User
 │
 ▼

Authentication
 │
 ▼

Role Assignment
 │
 ▼

Permission Matrix
 │
 ▼

Module Access Control
 │
 ▼

Business Operations
 │
 ▼

Audit Logging
```

---

# 11. Audit Trail Architecture

```text
User Action
      │
      ▼

Business Service
      │
      ▼

Change Detection
      │
      ▼

Audit Engine
      │
      ▼

Audit Log Table
      │
      ▼

Historical Traceability
```

---

# 12. Core Database Domains

```text
Users & Security
        │
        ├── Users
        ├── Roles
        └── Permissions

Sales
        │
        ├── Customers
        ├── Sales Orders
        └── Sales Lines

Inventory
        │
        ├── Products
        ├── Inventory
        └── Stock Ledger

Purchasing
        │
        ├── Vendors
        ├── Purchase Orders
        └── Receipts

Manufacturing
        │
        ├── BOM
        ├── Manufacturing Orders
        └── Work Orders

POS
        │
        ├── Sessions
        ├── Orders
        └── Order Lines

Analytics
        │
        ├── KPIs
        ├── Metrics
        └── Reports

Audit
        │
        └── Audit Logs
```
