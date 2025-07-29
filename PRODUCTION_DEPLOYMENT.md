# Production Deployment Guide for Accounting Updates

## 🚀 **Ensuring Reliable Accounting Updates in Production**

This guide ensures your accounting service updates work reliably when deployed to a live server.

## 📋 **Pre-Deployment Checklist**

### 1. **Database Setup**
```bash
# Ensure proper database configuration
python manage.py migrate
python manage.py check
```

### 2. **Environment Variables**
```bash
# Required environment variables for production
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=your-database-url
CELERY_BROKER_URL=redis://localhost:6379/0  # For background tasks
```

### 3. **Dependencies Installation**
```bash
# Install required packages
pip install celery[redis]  # For background tasks
pip install django-celery-beat  # For scheduled tasks
```

## 🔧 **Production Configuration**

### 1. **Celery Configuration (celery.py)**
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSMagic.settings')

app = Celery('POSMagic')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configure Celery for production
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)
```

### 2. **Settings Configuration (settings.py)**
```python
# Add to your settings.py
INSTALLED_APPS += [
    'django_celery_beat',
]

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Logging Configuration
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

## 🚀 **Deployment Steps**

### 1. **Initial Setup**
```bash
# 1. Deploy your code
git pull origin main

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Create superuser (if not exists)
python manage.py createsuperuser
```

### 2. **Start Celery Workers**
```bash
# Start Celery worker
celery -A POSMagic worker -l info

# Start Celery beat (for scheduled tasks)
celery -A POSMagic beat -l info

# Or use supervisor/systemd for production
```

### 3. **Initial Sync**
```bash
# Check current sync status
python manage.py check_accounting_sync --detailed

# Sync any missing entries
python manage.py sync_accounting_entries

# Verify sync
python manage.py check_accounting_sync
```

## 📅 **Scheduled Tasks Setup**

### 1. **Cron Jobs (Alternative to Celery Beat)**
```bash
# Add to crontab (crontab -e)
# Check accounting sync every hour
0 * * * * cd /path/to/your/app && python manage.py check_accounting_sync >> /var/log/accounting_sync.log 2>&1

# Sync missing entries daily at 2 AM
0 2 * * * cd /path/to/your/app && python manage.py sync_accounting_entries >> /var/log/accounting_sync.log 2>&1
```

### 2. **Celery Beat Schedule**
```python
# In settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-accounting-sync': {
        'task': 'accounts.tasks.sync_missing_accounting_entries_task',
        'schedule': crontab(hour='*/1'),  # Every hour
    },
}
```

## 🔍 **Monitoring & Maintenance**

### 1. **Regular Health Checks**
```bash
# Daily monitoring script
#!/bin/bash
cd /path/to/your/app

# Check accounting sync
python manage.py check_accounting_sync

# Check Celery workers
celery -A POSMagic inspect active

# Check logs
tail -n 50 /var/log/django/accounting.log
```

### 2. **Log Monitoring**
```bash
# Monitor accounting logs
tail -f /var/log/django/accounting.log

# Monitor Celery logs
tail -f /var/log/celery/worker.log
```

### 3. **Database Monitoring**
```sql
-- Check for missing accounting entries
SELECT 
    'sales' as type,
    COUNT(*) as total,
    COUNT(ae.id) as with_entries,
    COUNT(*) - COUNT(ae.id) as missing
FROM production_storesale s
LEFT JOIN accounts_journalentry ae ON s.id = ae.object_id AND ae.content_type_id = (SELECT id FROM django_content_type WHERE app_label='production' AND model='storesale')
WHERE s.total_amount > 0

UNION ALL

SELECT 
    'requisitions' as type,
    COUNT(*) as total,
    COUNT(ae.id) as with_entries,
    COUNT(*) - COUNT(ae.id) as missing
FROM production_requisition r
LEFT JOIN accounts_journalentry ae ON r.id = ae.object_id AND ae.content_type_id = (SELECT id FROM django_content_type WHERE app_label='production' AND model='requisition')
WHERE r.status IN ('approved', 'checking', 'delivered') AND r.total_cost > 0;
```

## 🚨 **Troubleshooting**

### 1. **Common Issues**
- **Signals not firing**: Check if signals are properly registered in `apps.py`
- **Celery tasks failing**: Check Celery worker logs and Redis connection
- **Database connection issues**: Verify database credentials and connection pool

### 2. **Emergency Recovery**
```bash
# If accounting sync is completely broken
python manage.py sync_accounting_entries --type=all

# If specific type is broken
python manage.py sync_accounting_entries --type=sales
python manage.py sync_accounting_entries --type=requisitions
```

### 3. **Rollback Plan**
```bash
# If needed, rollback to previous version
git checkout HEAD~1
python manage.py migrate
python manage.py sync_accounting_entries
```

## 📊 **Performance Optimization**

### 1. **Database Indexes**
```sql
-- Add indexes for better performance
CREATE INDEX idx_storesale_total_amount ON production_storesale(total_amount);
CREATE INDEX idx_requisition_status_cost ON production_requisition(status, total_cost);
CREATE INDEX idx_journalentry_content_type ON accounts_journalentry(content_type_id, object_id);
```

### 2. **Batch Processing**
```python
# For large datasets, process in batches
def sync_large_dataset(model_class, batch_size=1000):
    total = model_class.objects.count()
    for offset in range(0, total, batch_size):
        batch = model_class.objects.all()[offset:offset + batch_size]
        for item in batch:
            # Process item
            pass
```

## ✅ **Verification Checklist**

- [ ] All signals are properly registered
- [ ] Celery workers are running
- [ ] Scheduled tasks are configured
- [ ] Logging is properly configured
- [ ] Database indexes are created
- [ ] Initial sync is completed
- [ ] Monitoring is set up
- [ ] Backup procedures are in place

## 📞 **Support**

If you encounter issues:
1. Check the logs first
2. Run the diagnostic commands
3. Review this guide
4. Contact your system administrator

---

**Remember**: Always test accounting updates in a staging environment before deploying to production! 