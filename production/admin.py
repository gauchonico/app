from django.contrib import admin
from .models import *

# Register your models here.

@admin.register(TaxCode)
class TaxCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'rate', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name']
    ordering = ['code']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'rate', 'is_active')
        }),
        ('Additional Details', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('code')
    
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    
admin.site.register(ServiceCategory, ServiceCategoryAdmin)
admin.site.register(Refreshment)
admin.site.register(Profile)

@admin.register(StoreCreditNote)
class StoreCreditNoteAdmin(admin.ModelAdmin):
    list_display = ('credit_note_number', 'date_created', 'get_customer_name', 'total_amount', 'status', 'get_note_type_display')
    list_filter = ('status', 'note_type', 'date_created')
    search_fields = ('credit_note_number', 'customer__first_name', 'customer__last_name', 'reason')
    readonly_fields = ('credit_note_number', 'date_created', 'date_updated', 'get_created_by', 'get_updated_by')
    fieldsets = (
        (None, {
            'fields': ('credit_note_number', 'status', 'note_type', 'reason', 'total_amount')
        }),
        ('Related Sales', {
            'fields': ('product_sale', 'service_sale', 'customer')
        }),
        ('Refund Information', {
            'fields': ('is_refunded', 'refund_date', 'refund_method', 'refund_reference'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'updated_by', 'created_at', 'date_updated'),
            'classes': ('collapse',)
        }),
    )

    def get_created_by(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else '-'
    get_created_by.short_description = 'Created By'

    def get_updated_by(self, obj):
        return obj.updated_by.get_full_name() if obj.updated_by else '-'
    get_updated_by.short_description = 'Updated By'

    def get_customer_name(self, obj):
        return obj.customer.get_full_name() if obj.customer else '-'
    get_customer_name.short_description = 'Customer'


@admin.register(CreditNoteItem)
class CreditNoteItemAdmin(admin.ModelAdmin):
    list_display = ('credit_note', 'product', 'service', 'quantity', 'unit_price', 'total_price')
    list_filter = ('credit_note__status',)
    search_fields = ('credit_note__credit_note_number', 'product__name', 'service__name', 'reason')
    

