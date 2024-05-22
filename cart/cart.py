from POSMagicApp.models import Product
class Cart():
    def __init__(self, request):
        self.session = request.session

        #Get key if current session is available
        cart = self.session.get('session_key')

        #if user is new no session key
        if 'session_key' not in request.session:
            cart = self.session['session_key']={}

        #makesure cart is available on all web pages
        self.cart = cart
    
    def add(self, product, quantity):
        product_id = str(product.id)
        product_qty = str(quantity)
        message = None
        # product_qty = str(quantity)

        #logic
        if product_id in self.cart:
            message = f"{product.name} is already in your cart."
            pass
        else:
            # self.cart[product_id] = {'price': str(product.price)}
            self.cart[product_id] = int(product_qty)
            message = f"{product.name} has been added to your cart."

        self.session.modified = True
        return {
            'message': message
        }
    
    def __len__(self):
        return len(self.cart)
    
    def get_prods(self):
        #get ids from cart
        product_ids = self.cart.keys()

        #use ids to lookup products in database
        products = Product.objects.filter(id__in=product_ids)

        return products
    def get_quants(self):
        quantities = self.cart
        return quantities
    def update(self, product, quantity):
        product_id = str(product)
        product_qty = str(quantity)

        # get cart 
        outcart = self.cart
        #update cart
        outcart[product_id] = product_qty

        self.session.modified = True

        thing = self.cart
        return thing
    def delete(self, product):
        product_id = str(product)
        #Delete from cart
        if product_id in self.cart:
            del self.cart[product_id]
        
        self.session.modified = True

    def cart_total(self):
        #get product ids
        product_ids = self.cart.keys()

        #look up keys in our product db model
        products = Product.objects.filter(id__in=product_ids)

        #get quantities
        quantities = self.cart

        total = 0
        for key, value in quantities.items():
            key = int(key)
            for product in products:
                if product.id == key:
                    total += product.price * int(value)

        return total
    
    def clear(self):
        self.session['session_key'] = {}
        self.session.modified = True



