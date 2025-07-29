# Simple Production Guide for Accounting Updates (No Redis/Celery)

## 🚀 **Reliable Accounting Updates Without Complex Infrastructure**

This guide shows you how to ensure your accounting updates work reliably on live servers using only Django signals and simple cron jobs.

## ✅ **What We've Already Set Up**

### 1. **Enhanced Django Signals** (`accounts/signals.py`)
- ✅ Error handling and logging
- ✅ Duplicate prevention
- ✅ Transaction safety
- ✅ Non-blocking error recovery

### 2. **Management Commands**
- ✅ `check_accounting_sync` - Monitor sync status
- ✅ `simple_sync_accounting` - Manual sync (no Celery needed)
- ✅ `sync_accounting_entries` - Full sync with options

## 🛠️ **Simple Production Setup**

### 1. **Basic Requirements**
```bash
# No additional packages needed beyond your existing requirements
# Just ensure your Django app is running properly
```

### 2. **Environment Setup**
```bash
# Set these environment variables
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=your-database-url
```

### 3. **Logging Configuration** (Add to settings.py)
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/accounting.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'accounts': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 📅 **Cron Job Setup (The Simple Way)**

### 1. **Set Up Cron Jobs**
```bash
# Edit crontab
crontab -e

# Add these lines (adjust paths to your app location):
# Check accounting sync every hour
0 * * * * cd /path/to/your/app && python manage.py check_accounting_sync >> /var/log/accounting_sync.log 2>&1

# Sync missing entries daily at 2 AM (processes 100 entries at a time)
0 2 * * * cd /path/to/your/app && python manage.py simple_sync_accounting --limit=100 >> /var/log/accounting_sync.log 2>&1

# Full sync weekly on Sunday at 3 AM
0 3 * * 0 cd /path/to/your/app && python manage.py sync_accounting_entries >> /var/log/accounting_sync.log 2>&1
```

### 2. **Create Log Directory**
```bash
# Create log directory
sudo mkdir -p /var/log/django
sudo chown your-user:your-group /var/log/django
```

## 🔍 **Monitoring & Maintenance**

### 1. **Daily Health Check**
```bash
# Check sync status
python manage.py check_accounting_sync

# Check logs
tail -n 50 /var/log/django/accounting.log
tail -n 50 /var/log/accounting_sync.log
```

### 2. **Manual Sync When Needed**
```bash
# Quick sync (100 entries)
python manage.py simple_sync_accounting

# Full sync
python manage.py sync_accounting_entries

# Dry run to see what would be synced
python manage.py simple_sync_accounting --dry-run
```

### 3. **Monitor Cron Jobs**
```bash
# Check if cron is running
sudo systemctl status cron

# View cron logs
sudo tail -f /var/log/cron

# Check your specific cron job logs
tail -f /var/log/accounting_sync.log
```

## 🚨 **Troubleshooting**

### 1. **Signals Not Working**
```bash
# Check if signals are registered
python manage.py shell
>>> from django.apps import apps
>>> apps.get_app_config('accounts').ready()
```

### 2. **Cron Jobs Not Running**
```bash
# Check cron service
sudo systemctl status cron

# Check cron logs
sudo tail -f /var/log/cron

# Test cron manually
cd /path/to/your/app && python manage.py check_accounting_sync
```

### 3. **Database Issues**
```bash
# Check database connection
python manage.py dbshell

# Check for missing entries
python manage.py check_accounting_sync --detailed
```

## 📊 **Performance Tips**

### 1. **Database Indexes** (Optional but Recommended)
```sql
-- Add these indexes for better performance
CREATE INDEX idx_storesale_total_amount ON production_storesale(total_amount);
CREATE INDEX idx_requisition_status_cost ON production_requisition(status, total_cost);
CREATE INDEX idx_journalentry_content_type ON accounts_journalentry(content_type_id, object_id);
```

### 2. **Batch Processing**
The `simple_sync_accounting` command already processes entries in batches (default 100). You can adjust this:
```bash
# Process 50 entries at a time
python manage.py simple_sync_accounting --limit=50

# Process 200 entries at a time
python manage.py simple_sync_accounting --limit=200
```

## ✅ **Verification Checklist**

- [ ] Django signals are working (test by creating a sale/requisition)
- [ ] Cron jobs are set up and running
- [ ] Log files are being created
- [ ] Initial sync is completed
- [ ] Monitoring is in place
- [ ] Backup procedures are in place

## 🎯 **How It Works**

### **Real-time Updates (Signals)**
1. When a sale is created → Signal fires → Accounting entry created
2. When a requisition is approved → Signal fires → Accounting entry created
3. If signal fails → Error logged → Manual sync will catch it later

### **Backup Sync (Cron Jobs)**
1. Hourly check → Identifies missing entries
2. Daily sync → Processes up to 100 missing entries
3. Weekly full sync → Processes all missing entries

### **Error Recovery**
- Signals don't block main operations if they fail
- Cron jobs catch any missed entries
- Logs provide visibility into what's happening

## 🚀 **Deployment Steps**

### 1. **Deploy Your Code**
```bash
git pull origin main
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

### 2. **Set Up Cron Jobs**
```bash
crontab -e
# Add the cron jobs mentioned above
```

### 3. **Initial Sync**
```bash
# Check current status
python manage.py check_accounting_sync --detailed

# Run initial sync
python manage.py sync_accounting_entries

# Verify
python manage.py check_accounting_sync
```

### 4. **Test**
```bash
# Create a test sale/requisition
# Check if accounting entry is created automatically
# Check logs for any errors
```

## 💡 **Advantages of This Approach**

✅ **Simple** - No complex infrastructure needed  
✅ **Reliable** - Multiple layers of protection  
✅ **Scalable** - Can handle growing data  
✅ **Maintainable** - Easy to understand and debug  
✅ **Cost-effective** - No additional services required  

## 🔄 **When to Upgrade to Celery**

Consider upgrading to Celery when:
- You have thousands of transactions per day
- You need real-time processing guarantees
- You want more sophisticated retry mechanisms
- You need distributed task processing

---

**This approach will work reliably for most businesses and can handle significant growth before needing more complex solutions!** 