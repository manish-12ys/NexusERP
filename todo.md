# NexusERP – 18 Hour Hackathon Execution Plan

## Goal

Build a working **Demand-to-Delivery Manufacturing ERP** that demonstrates:

* Product Management
* Inventory Management
* Sales Management
* Purchase Management
* Manufacturing
* BoM Management
* Procurement Automation
* Audit Logs
* Role-Based Access
* AI Operations Copilot (Standout Feature)

## 🔑 Demo Login Credentials

| Username | Password | Role | Primary Features |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | System Admin | User & Role Management |
| `owner` | `owner123` | Business Owner | Factory Control Center, Analytics |
| `sales` | `sales123` | Sales User | Customer registry, Sales Orders |
| `purchase` | `purchase123` | Purchase User | Vendor registry, Purchase Orders |
| `manufacturing` | `manufacturing123` | Manufacturing User | BOM recipes, Mfg & Work Orders |
| `inventory` | `inventory123` | Inventory Manager | Product setup, Stock adjustments |
| `cashier` | `cashier123` | POS Cashier | POS Terminal Checkout |

---

# Phase 1 – Project Setup & Foundation (1 Hour)

## Objective

Create the project structure and core architecture.

### TODO

* [x] Setup Flask project
* [x] Setup SQLite database
* [x] Configure SQLAlchemy
* [x] Configure Authentication
* [x] Create Base Layout
* [x] Create Dashboard Layout
* [x] Setup Navigation Sidebar
* [x] Setup Role Management
* [x] Create Database Migration Setup

### Deliverable

Users can login and access the dashboard.

---

# Phase 2 – Authentication & User Roles (1 Hour)

## Objective

Secure the ERP.

### Roles

* Admin
* Sales User
* Purchase User
* Manufacturing User
* Inventory Manager
* Business Owner

### TODO

* [x] Login Page
* [x] Logout Functionality
* [x] User Management
* [x] Role Assignment
* [x] Permission Middleware
* [x] Route Protection
* [x] Access Restrictions

### Deliverable

Each role sees only their allowed modules.

---

# Phase 3 – Product Management (2 Hours)

## Objective

Create the central inventory model.

### TODO

### Product Master

* [x] Create Product
* [x] Edit Product
* [x] Delete Product
* [x] Product Listing

### Product Details

* [x] Product Name
* [x] SKU
* [x] Category
* [x] Cost Price
* [x] Selling Price

### Procurement Configuration

* [x] MTS Support
* [x] MTO Support
* [x] Procurement Type Selection
* [x] Purchase Procurement
* [x] Manufacturing Procurement

### Inventory Fields

* [x] On Hand Quantity
* [x] Reserved Quantity
* [x] Free Quantity

### Deliverable

Products become the foundation of all ERP operations.

---

# Phase 4 – Inventory & Stock Ledger (2 Hours)

## Objective

Track every inventory movement.

### TODO

### Inventory Dashboard

* [x] Stock Summary
* [x] Inventory Search
* [x] Low Stock Indicator

### Stock Ledger

* [x] Movement History
* [x] Inward Stock
* [x] Outward Stock
* [x] Manufacturing Consumption
* [x] Manufacturing Production

### Inventory Metrics

* [x] On Hand Qty
* [x] Reserved Qty
* [x] Free Qty

### Deliverable

Complete stock visibility.

---

# Phase 5 – Sales Management (2 Hours)

## Objective

Manage customer demand.

### TODO

### Customer Management

* [x] Customer Creation
* [x] Customer Listing

### Sales Orders

* [x] Create SO
* [x] Product Selection
* [x] Quantity Selection
* [x] Price Calculation

### Workflow

* [x] Draft
* [x] Confirmed
* [x] Delivered
* [x] Cancelled

### Business Logic

* [x] Stock Validation
* [x] Quantity Reservation
* [x] Inventory Updates
* [x] Procurement Trigger

### Deliverable

Sales orders reserve stock automatically.

---

# Phase 6 – Purchase Management (1.5 Hours)

## Objective

Replenish inventory.

### TODO

### Vendor Management

* [x] Vendor Creation
* [x] Vendor Listing

### Purchase Orders

* [x] Create PO
* [x] Confirm PO
* [x] Receive Products

### Workflow

* [x] Draft
* [x] Confirmed
* [x] Partially Received
* [x] Fully Received

### Business Logic

* [x] Increase Inventory
* [x] Ledger Updates

### Deliverable

Purchases automatically increase stock.

---

# Phase 7 – Bill of Materials (BoM) (1 Hour)

## Objective

Define manufacturing recipes.

### TODO

### BoM Management

* [x] Create BoM
* [x] Add Components
* [x] Component Quantities

### Operations

* [x] Assembly
* [x] Painting
* [x] Packaging

### Deliverable

Products can now be manufactured.

---

# Phase 8 – Manufacturing Module (2 Hours)

## Objective

Convert raw materials into finished goods.

### TODO

### Manufacturing Orders

* [x] Create MO
* [x] Assign Product
* [x] Assign Quantity

### Component Reservation

* [x] Reserve Components
* [x] Validate Availability

### Work Orders

* [x] Assembly
* [x] Painting
* [x] Packaging

### Completion

* [x] Consume Components
* [x] Produce Finished Goods
* [x] Update Ledger

### Deliverable

End-to-end manufacturing workflow.

---

# Phase 9 – Procurement Automation (1.5 Hours)

## Objective

Solve the main business problem.

### TODO

### MTS Logic

* [x] Deliver From Stock

### MTO Logic

* [x] Detect Shortages

### Auto Procurement

* [x] Auto Purchase Order Creation
* [x] Auto Manufacturing Order Creation

### Replenishment Engine

* [x] Shortage Calculation
* [x] Procurement Recommendation

### Deliverable

ERP automatically reacts to demand.

---

# Phase 10 – Audit Logs (30 Minutes)

## Objective

Provide traceability.

### TODO

Track:

* [x] Product Changes
* [x] Inventory Changes
* [x] Sales Changes
* [x] Purchase Changes
* [x] Manufacturing Changes
* [x] User Actions

### Log Details

* [x] User
* [x] Action
* [x] Timestamp
* [x] Old Value
* [x] New Value

### Deliverable

Full traceability.

---

# Phase 11 – Dashboard & Analytics (1 Hour)

## Objective

Give owners complete visibility.

### TODO

### KPI Cards

* [x] Sales Orders
* [x] Purchase Orders
* [x] Manufacturing Orders
* [x] Inventory Value

### Alerts

* [x] Low Stock
* [x] Delayed Orders
* [x] Pending Procurement

### Charts

* [x] Inventory Movement
* [x] Sales Trends
* [x] Manufacturing Trends

### Deliverable

Business command center.

---

# Phase 12 – Standout Features (2 Hours)

## Feature 1 – AI Operations Copilot

### TODO

* [x] AI Chat Interface
* [x] ERP Data Context
* [x] Business Insights

Queries:

* [x] What should I manufacture today?
* [x] Which products are running low?
* [x] Why is this order delayed?
* [x] Show inventory shortages.

---

## Feature 2 – Delivery Risk Predictor

### TODO

* [x] Check Stock
* [x] Check Component Availability
* [x] Check Manufacturing Queue
* [x] Generate Risk Level

Output:

* [x] Low Risk
* [x] Medium Risk
* [x] High Risk

---

## Feature 3 – Production Kanban Board

### TODO

Columns

* [x] To Manufacture
* [x] Assembly
* [x] Painting
* [x] Packaging
* [x] Completed

### Deliverable

Visual manufacturing pipeline.

---

# Final Demo Scenario (30 Minutes)

### Judge Flow

1. Create Product
2. Create BoM
3. Add Raw Materials
4. Create Sales Order
5. Detect Stock Shortage
6. Auto Generate Manufacturing Order
7. Reserve Components
8. Complete Work Orders
9. Produce Finished Goods
10. Deliver Sales Order
11. Show Dashboard Updates
12. Show Audit Logs
13. Ask AI Copilot Questions

---

# One-Line Summary of Each Phase

| Phase | Summary                  |
| ----- | ------------------------ |
| 1     | Setup ERP Foundation     |
| 2     | Authentication & Roles   |
| 3     | Product Management       |
| 4     | Inventory & Stock Ledger |
| 5     | Sales Management         |
| 6     | Purchase Management      |
| 7     | Bill of Materials        |
| 8     | Manufacturing            |
| 9     | Procurement Automation   |
| 10    | Audit Logs               |
| 11    | Dashboard & Analytics    |
| 12    | Standout AI Features     |
| 13    | End-to-End Demo          |

This plan directly maps every feature to the problem statement while highlighting the AI Copilot, Risk Predictor, and Production Kanban Board as differentiators that can help the project stand out during judging.
