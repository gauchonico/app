# 🏭 LIVARA BUSINESS MODEL → CHART OF ACCOUNTS MAPPING

## 📋 **Business Process Flow & Accounting Integration**

---

### 🛒 **1. PROCUREMENT CYCLE** (Requisitions → LPO → Payment)

#### **Models Involved:**
- `Requisition` → `LPO` → `PaymentVoucher` → `GoodsReceivedNote`
- `DebitNote` (for discrepancies)
- `CreditNote` (for returns)

#### **Accounting Flow:**

**📝 Step 1: Requisition Created**
```
Dr. Raw Materials Inventory (1200)           XXX
Cr. Accounts Payable - Suppliers (2000)          XXX
```

**📋 Step 2: LPO Generated**
- No journal entry (just commitment)
- Track in purchasing system

**💰 Step 3: Payment Voucher (Payment Made)**
```
Dr. Accounts Payable - Suppliers (2000)      XXX
Cr. Cash/Bank/Mobile Money (1000/1020/1010)      XXX
```

**📦 Step 4: Goods Received Note**
- Verify quantities match
- Adjust inventory if discrepancies

**⚠️ Step 5: Debit Note (if shortages/damages)**
```
Dr. Accounts Payable - Suppliers (2000)      XXX
Cr. Raw Materials Inventory (1200)               XXX
```

---

### 🏭 **2. MANUFACTURING CYCLE** (Raw Materials → Finished Goods)

#### **Models Involved:**
- `ProductionOrder` → `ManufactureProduct` → `ManufacturedProductInventory`
- `ManufacturedProductIngredient` (raw materials used)

#### **Accounting Flow:**

**🔄 Step 1: Production Started**
```
Dr. Work in Process Inventory (1210)         XXX
Cr. Raw Materials Inventory (1200)               XXX
```

**⚙️ Step 2: Manufacturing Overhead**
```
Dr. Work in Process Inventory (1210)         XXX
Cr. Manufacturing Overhead (5020)                XXX
```

**✅ Step 3: Production Completed**
```
Dr. Finished Goods Inventory (1220)          XXX
Cr. Work in Process Inventory (1210)             XXX
```

**🧪 Step 4: Quality Control Costs**
```
Dr. Quality Control Costs (5040)             XXX
Cr. Cash/Supplies (1000/1250)                    XXX
```

---

### 🛍️ **3. STORE SALES CYCLE** (B2B Sales)

#### **Models Involved:**
- `StoreSale` → `SaleItem` → `StoreSaleReceipt`
- `Customer` accounts receivable

#### **Accounting Flow:**

**📋 Step 1: Store Sale Invoiced**
```
Dr. Accounts Receivable - Store Sales (1100)  XXX
Cr. Store Sales Revenue - Products (4100)         XXX
Cr. VAT Payable (2020)                            XXX (if applicable)
```

**💰 Step 2: Payment Received**
```
Dr. Cash/Bank/Mobile Money (1000/1020/1010)   XXX
Cr. Accounts Receivable - Store Sales (1100)     XXX
```

**📦 Step 3: Cost of Goods Sold**
```
Dr. Raw Materials Used (5000)                XXX
Cr. Finished Goods Inventory (1220)              XXX
```

---

### 💅 **4. SERVICE SALES CYCLE** (Salon Services)

#### **Models Involved:**
- `ServiceSale` → `ServiceSaleItem` → `Payment`
- `StaffCommission` for staff commissions

#### **Accounting Flow:**

**📋 Step 1: Service Sale Invoiced**
```
Dr. Accounts Receivable - Service Sales (1110) XXX
Cr. Service Sales Revenue (4110)                   XXX
```

**💰 Step 2: Payment Received**
```
Dr. Cash/Bank/Mobile Money (1000/1020/1010)    XXX
Cr. Accounts Receivable - Service Sales (1110)    XXX
```

**💼 Step 3: Staff Commission Earned**
```
Dr. Service Commission Expense (6015)          XXX
Cr. Commission Payable (2110)                      XXX
```

**💸 Step 4: Commission Paid**
```
Dr. Commission Payable (2110)                  XXX
Cr. Cash/Bank (1000/1020)                          XXX
```

---

### 🎒 **5. ACCESSORY SALES CYCLE**

#### **Models Involved:**
- `AccessorySaleItem` → part of `ServiceSale`
- `AccessoryInventory` management

#### **Accounting Flow:**

**💰 Step 1: Accessory Sale**
```
Dr. Accounts Receivable (1100/1110)           XXX
Cr. Accessory Sales Revenue (4120)                XXX
```

**📦 Step 2: Cost of Accessories Sold**
```
Dr. Raw Materials Used (5000)                 XXX
Cr. Accessories Inventory (1240)                  XXX
```

---

### 📊 **6. COMMISSION SYSTEM** (Staff Performance)

#### **Models Involved:**
- `StaffCommission` (service commissions)
- `StaffProductCommission` (product commissions)
- `MonthlyStaffCommission` (compiled monthly)

#### **Accounting Flow:**

**💼 Step 1: Service Commission Earned**
```
Dr. Service Commission Expense (6015)          XXX
Cr. Commission Payable (2110)                      XXX
```

**🛍️ Step 2: Product Commission Earned**
```
Dr. Product Commission Expense (6016)          XXX
Cr. Commission Payable (2110)                      XXX
```

**💰 Step 3: Monthly Commission Payment**
```
Dr. Commission Payable (2110)                  XXX
Cr. Cash/Bank/Mobile Money (1000/1020/1010)       XXX
```

---

## 🎯 **KEY ACCOUNT MAPPING BY MODEL**

### **Inventory Models → Chart Accounts:**
- `LivaraMainStore` → **1200** (Raw Materials Inventory)
- `ManufacturedProductInventory` → **1220** (Finished Goods)
- `StoreInventory` → **1230** (Store Products)
- `AccessoryInventory` → **1240** (Accessories)

### **Sales Models → Chart Accounts:**
- `StoreSale` → **4100** (Store Sales Revenue)
- `ServiceSale` → **4110** (Service Sales Revenue)
- `AccessorySaleItem` → **4120** (Accessory Sales Revenue)

### **Purchasing Models → Chart Accounts:**
- `Requisition` → **2000** (Accounts Payable)
- `PaymentVoucher` → **1000/1020/1010** (Cash/Bank)
- `LPO` → Commitment tracking (no journal entry)

### **Commission Models → Chart Accounts:**
- `StaffCommission` → **6015** (Service Commission Expense)
- `StaffProductCommission` → **6016** (Product Commission Expense)
- `MonthlyStaffCommission` → **2110** (Commission Payable)

### **Customer Models → Chart Accounts:**
- Store Customers → **1100** (A/R Store Sales)
- Service Customers → **1110** (A/R Service Sales)

---

## 🔧 **IMPLEMENTATION STEPS**

### **Phase 1: Setup Chart of Accounts**
```bash
python manage.py setup_livara_chart_of_accounts
```

### **Phase 2: Update Existing Models**
- Add `chart_account` ForeignKey to relevant models
- Create signals for automatic journal entries
- Update views to show accounting integration

### **Phase 3: Create Accounting Services**
- `RequisitionAccountingService` for procurement
- `ManufacturingAccountingService` for production
- `SalesAccountingService` for store/service sales
- `CommissionAccountingService` (already implemented)

### **Phase 4: Financial Reports**
- Manufacturing Cost Reports
- Sales Performance by Revenue Stream
- Commission Expense Analysis
- Inventory Valuation Reports

---

## 📈 **FINANCIAL STATEMENT IMPACT**

### **Income Statement Structure:**
```
REVENUE
├── Store Sales Revenue (4100)
├── Service Sales Revenue (4110)
├── Accessory Sales Revenue (4120)
└── Other Revenue (4200-4999)

COST OF GOODS SOLD
├── Raw Materials Used (5000)
├── Direct Labor (5010)
├── Manufacturing Overhead (5020)
└── Inventory Adjustments (5100-5199)

OPERATING EXPENSES
├── Staff Costs (6000-6199)
├── Store Operations (6200-6399)
├── Manufacturing Operations (6400-6599)
└── Marketing & Sales (6600-6799)
```

### **Balance Sheet Structure:**
```
ASSETS
├── Current Assets
│   ├── Cash & Equivalents (1000-1025)
│   ├── Accounts Receivable (1100-1130)
│   └── Inventory (1200-1260)
└── Fixed Assets (1500-1720)

LIABILITIES
├── Current Liabilities
│   ├── Accounts Payable (2000-2050)
│   ├── Staff Liabilities (2100-2120)
│   └── Customer Liabilities (2200-2220)
└── Long-term Liabilities (2500-2999)
```

This mapping ensures your LIVARA business operations are properly reflected in your financial statements with accurate cost tracking, revenue recognition, and cash flow management! 🚀
