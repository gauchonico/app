from .cart import Cart

#cart to work on all pages
def cart(request):
     return {'cart': Cart(request)}