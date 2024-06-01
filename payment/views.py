from datetime import datetime
from decimal import Decimal
from django.shortcuts import render
from .models import CommissionRate, Transaction
from cart.cart import Cart
from payment.forms import OrderDetailsForm
from POSMagicApp.models import Staff

# Create your views here.
def payment_success(request):
    context = {
		"appSidebarHide": 1,
		"appHeaderHide": 1,
		"appContentClass": 'p-0'
	}
    return render(request, 'payment/payment_success.html', context)

def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_prods()
    quantities = cart.get_quants
    totals = cart.cart_total()

    print(quantities())

    if request.method == 'POST':
        order_details_form = OrderDetailsForm(request.POST)

        if order_details_form.is_valid():
            order_details = order_details_form.save(commit=False)
            order_details.save()

             # Calculate commission based on chosen commission rate exclude saloon materials
            allowed_commission_products = cart_products.exclude(category="SALOOMATERIALS")
            allowed_total = 0
            for key, value in quantities().items():
                key = int(key)
                for product in allowed_commission_products:
                    if product.id == key:
                        allowed_total += product.price * int(value)
            
            commission_rate = order_details.commission_rate.percentage if order_details.commission_rate else Decimal('0.00')
            commission_amount = allowed_total * (commission_rate / Decimal('100.00'))  # Ensure decimal division


            transaction = Transaction.objects.create(
                customer=order_details.customer,
                total_amount=totals,
                date=datetime.now(),
                status='pending',
                is_delivery=order_details.is_delivery,
                staff=order_details.staff,
                branch=order_details.branch,
                notes=order_details.notes,
                commission_percentage =order_details.commission_rate.percentage,
                commission_amount=commission_amount,
                
            )
            # Add products from the cart to the transaction
            for product in cart_products:
                transaction.products.add(product)

            cart.clear()
            return render(request, 'payment/payment_success.html')
    else:
        order_details_form = OrderDetailsForm()

    context ={
        'order_details_form': order_details_form,
        'totals': totals,
        'cart': cart,
        'cart_products': cart_products,
        'quantities': quantities,
    }
    return render(request, 'payment/checkout.html', context)