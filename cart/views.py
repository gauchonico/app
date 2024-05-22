from django.shortcuts import get_object_or_404, render, redirect

from POSMagicApp.models import Product

from .cart import Cart
from django.http import Http404, JsonResponse

# Create your views here.

def cart_summary(request):
    cart = Cart(request)
    cart_products = cart.get_prods()
    quantities = cart.get_quants
    totals = cart.cart_total()
    context ={
        'totals': totals,
        'cart': cart,
        'cart_products': cart_products,
        'quantities': quantities,
    }
    return render(request, 'cart_summary.html', context)

def cart_add(request):
    # Get cart
    cart = Cart(request)

    # Check for POST request
    if request.POST.get('action') == 'post':
        # Extract product ID
        try:
            product_id = int(request.POST.get('product_id'))
            # Extract product quantity
            product_qty = int(request.POST.get('product_qty'))

        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid Prodcut Id'})

        

        try:
            product = get_object_or_404(Product, id=product_id)
        except Http404:
            return JsonResponse({'error': 'Product Not found'})

        cart.add(product=product, quantity=product_qty)
        # cart_products = list(cart.cart.items())
        total_cart = cart.__len__()

        response = JsonResponse({'qty': total_cart})
        return response

def cart_delete(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        #Get stuff
        product_id = int(request.POST.get('product_id'))
        # Get delete function
        cart.delete(product=product_id)

        response = JsonResponse({'product': product_id})
        return response

def cart_update(request):
    cart = Cart(request)
    if request.POST.get('action') == 'post':
        #Get stuff
        product_id = int(request.POST.get('product_id'))
        product_qty = int(request.POST.get('product_qty'))

        cart.update(product=product_id, quantity=product_qty)

        response = JsonResponse({'qty': product_qty})
        return response