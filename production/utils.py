from decimal import Decimal
from django.db import transaction
from production.models import ManufacturedProductInventory, PurchaseOrder, RequisitionItem, RestockRequest, StoreInventory, RawMaterialPrice


def check_ingredient_availability_for_production(production_order, quantity_to_produce):
    """
    Check if there are enough raw materials to produce the requested quantity.
    Returns detailed availability information for each ingredient.
    Properly handles unit conversions: ingredients in base units (g, ml), stock in larger units (kg, l).
    
    Args:
        production_order: ProductionOrder instance
        quantity_to_produce: int - quantity to check availability for
    
    Returns:
        dict with availability details and overall feasibility
    """
    
    def convert_stock_to_base_unit(stock_quantity, unit_measurement):
        """Convert raw material stock to base units for comparison with ingredient requirements"""
        from decimal import Decimal
        
        # Ensure stock_quantity is Decimal
        if not isinstance(stock_quantity, Decimal):
            stock_quantity = Decimal(str(stock_quantity))
            
        unit_lower = unit_measurement.lower()
        if unit_lower in ['kilograms', 'kg']:
            return stock_quantity * Decimal('1000')  # Convert kg stock to grams for comparison
        elif unit_lower in ['liters', 'litres', 'l']:
            return stock_quantity * Decimal('1000')  # Convert liter stock to ml for comparison
        return stock_quantity  # Return as is for base units like pieces, bottles
    
    from decimal import Decimal
    
    product = production_order.product
    ingredients_check = []
    overall_sufficient = True
    
    try:
        # Ensure quantity_to_produce is Decimal
        quantity_to_produce = Decimal(str(quantity_to_produce))
        
        for ingredient in product.productioningredients.all():
            # Calculate required quantity for this ingredient (already in base units: g, ml, pieces)
            quantity_needed_per_unit = ingredient.quantity_per_unit_product_volume
            
            # Ensure it's Decimal
            if not isinstance(quantity_needed_per_unit, Decimal):
                quantity_needed_per_unit = Decimal(str(quantity_needed_per_unit))
                
            total_quantity_needed = quantity_needed_per_unit * quantity_to_produce
            
            # Get current stock and convert to base units for comparison
            raw_stock_quantity = ingredient.raw_material.quantity or Decimal('0')
            
            # Ensure it's Decimal
            if not isinstance(raw_stock_quantity, Decimal):
                raw_stock_quantity = Decimal(str(raw_stock_quantity))
                
            current_stock_base_units = convert_stock_to_base_unit(
                raw_stock_quantity, 
                ingredient.raw_material.unit_measurement
            )
            
            # Check if sufficient (both in base units now)
            is_sufficient = current_stock_base_units >= total_quantity_needed
            if not is_sufficient:
                overall_sufficient = False
            
            # Calculate shortage in base units
            shortage_base_units = max(Decimal('0'), total_quantity_needed - current_stock_base_units)
            
            # Get price information for cost estimation (price is per larger unit: kg, liter)
            price_info = get_raw_material_price_with_fallback(ingredient.raw_material)
            
            # Ensure price is Decimal
            price = price_info['price']
            if not isinstance(price, Decimal):
                price = Decimal(str(price))
            
            # Convert shortage back to larger units for cost calculation
            if ingredient.raw_material.unit_measurement.lower() in ['kilograms', 'kg']:
                shortage_larger_units = shortage_base_units / Decimal('1000')  # grams to kg
                display_unit = 'kg'
            elif ingredient.raw_material.unit_measurement.lower() in ['liters', 'litres', 'l']:
                shortage_larger_units = shortage_base_units / Decimal('1000')  # ml to liters
                display_unit = 'liters'
            else:
                shortage_larger_units = shortage_base_units
                display_unit = ingredient.raw_material.unit_measurement
            
            ingredient_data = {
                'raw_material': ingredient.raw_material,
                'quantity_needed_per_unit': quantity_needed_per_unit,
                'total_quantity_needed': total_quantity_needed,
                'total_quantity_needed_display': total_quantity_needed,  # Already in base units
                'current_stock': raw_stock_quantity,  # Stock in larger units (kg, l)
                'current_stock_base_units': current_stock_base_units,  # Stock converted to base units
                'is_sufficient': is_sufficient,
                'shortage': shortage_larger_units,  # Shortage in larger units for cost calc
                'shortage_base_units': shortage_base_units,  # Shortage in base units for display
                'shortage_percentage': (shortage_base_units / total_quantity_needed * Decimal('100')) if total_quantity_needed > 0 else Decimal('0'),
                'unit_measurement': ingredient.raw_material.unit_measurement,
                'display_unit': display_unit,
                'price_per_unit': price,
                'shortage_cost': shortage_larger_units * price,
                'price_source': price_info['details']
            }
            
            ingredients_check.append(ingredient_data)
    
    except Exception as e:
        print(f"Error checking ingredient availability: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'ingredients': [],
            'overall_sufficient': False,
            'error': str(e),
            'can_produce_quantity': 0,
            'total_shortage_cost': 0
        }
    
    # Calculate maximum quantity that can be produced with current stock
    max_producible = None
    for ingredient_data in ingredients_check:
        if ingredient_data['quantity_needed_per_unit'] > 0:
            # Use base units for calculation
            possible_quantity = ingredient_data['current_stock_base_units'] / ingredient_data['quantity_needed_per_unit']
            if max_producible is None or possible_quantity < max_producible:
                max_producible = possible_quantity
    
    max_producible = int(max_producible) if max_producible is not None else 0
    
    # Calculate total shortage cost
    total_shortage_cost = sum(item['shortage_cost'] for item in ingredients_check)
    
    return {
        'ingredients': ingredients_check,
        'overall_sufficient': overall_sufficient,
        'can_produce_quantity': max_producible,
        'requested_quantity': int(quantity_to_produce),
        'total_shortage_cost': total_shortage_cost,
        'error': None
    }


def get_raw_material_price_with_fallback(raw_material, supplier=None):
    """
    Centralized function to get raw material price with proper fallback logic.
    Priority: 1. Latest requisition price, 2. RawMaterialPrice, 3. Zero
    
    Args:
        raw_material: RawMaterial instance
        supplier: Supplier instance (optional, for more specific price lookup)
    
    Returns:
        dict with price, source, and details
    """
    try:
        # Priority 1: Get the most recent requisition item for this raw material
        requisition_filter = {'raw_material': raw_material, 'price_per_unit__gt': 0}
        if supplier:
            requisition_filter['requisition__supplier'] = supplier
            
        latest_requisition_item = RequisitionItem.objects.filter(
            **requisition_filter
        ).order_by('-requisition__created_at').first()
        
        if latest_requisition_item:
            return {
                'price': latest_requisition_item.price_per_unit,
                'source': 'requisition',
                'details': f"Requisition: {latest_requisition_item.requisition.requisition_no}",
                'supplier': latest_requisition_item.requisition.supplier.name,
                'date': latest_requisition_item.requisition.created_at
            }
        
        # Priority 2: Try to get from RawMaterialPrice
        price_filter = {'raw_material': raw_material, 'is_current': True}
        if supplier:
            price_filter['supplier'] = supplier
            
        latest_raw_material_price = RawMaterialPrice.objects.filter(
            **price_filter
        ).order_by('-effective_date').first()
        
        if latest_raw_material_price:
            return {
                'price': latest_raw_material_price.price,
                'source': 'market_price',
                'details': f"Market price: {latest_raw_material_price.supplier.name}",
                'supplier': latest_raw_material_price.supplier.name,
                'date': latest_raw_material_price.effective_date
            }
        
        # No price found
        return {
            'price': Decimal('0.00'),
            'source': 'none',
            'details': "No pricing information available",
            'supplier': 'N/A',
            'date': None
        }
        
    except Exception as e:
        return {
            'price': Decimal('0.00'),
            'source': 'error',
            'details': f"Error: {str(e)}",
            'supplier': 'N/A',
            'date': None
        }


def cost_per_unit(self):
  ingredient_costs = []
  for ingredient in self.productioningredients.all():
    # Use the centralized price function with fallback logic
    price_info = get_raw_material_price_with_fallback(ingredient.raw_material)
    
    if price_info['price'] > 0:
        print(f"Found price for {ingredient.raw_material.name}: {price_info['price']} from {price_info['source']}")
        unit_of_measurement = ingredient.raw_material.unit_measurement.lower()
        
        purchase_price_per_unit = price_info['price']

      # Conversion factor to convert base units (e.g., grams, milliliters) to the stored unit (kilograms, liters)

        if unit_of_measurement in ['kilograms', 'kg']:
                price_per_base_unit = purchase_price_per_unit / 1000  # Convert kg to gram price
        elif unit_of_measurement in ['liters', 'litres', 'l']:
                price_per_base_unit = purchase_price_per_unit / 1000  # Convert liter to ml price
        else:
            price_per_base_unit = purchase_price_per_unit  # Use price per unit for items like bottles or pieces
        
        cost_per_ingredient = price_per_base_unit * ingredient.quantity_per_unit_product_volume
    else:
        # No price found
        print(f"No price found for {ingredient.raw_material.name}: {price_info['details']}")
        cost_per_ingredient = 0
        price_per_base_unit = 0
    
    ingredient_cost_data = {
        'name': ingredient.raw_material.name,
        'quantity_per_unit': ingredient.quantity_per_unit_product_volume,
        'price_per_base_unit': price_per_base_unit,
        'cost_per_ingredient': cost_per_ingredient,
        'price_source': price_info['details'],  # Add source information for transparency
        'price_supplier': price_info['supplier'],  # Add supplier information
        'price_date': price_info['date'],  # Add date information
        'unit_of_measurement': ingredient.raw_material.unit_measurement
    }
    ingredient_costs.append(ingredient_cost_data)
    
  return ingredient_costs

def calculate_percentage_inclusion(ingredient, exclude_names=['Bottle Top', 'Label']):
  """Calculates the percentage inclusion of a raw material in a product ingredient.

  Args:
      ingredient: A ProductionIngredient object.
      exclude_names: A list of raw material names (optional) to exclude from calculation.

  Returns:
      The percentage inclusion as a decimal value, or None if excluded.
  """
  if ingredient.raw_material.name in exclude_names:
    return None

  return ingredient.quantity_per_unit_product_volume * Decimal('0.10')

def approve_restock_request(request_id):
  with transaction.atomic():
    restock_request = RestockRequest.objects.get(pk=request_id)
    if restock_request.status == "approved":
      inventory = ManufacturedProductInventory.objects.filter(product=restock_request.product).first()
      if inventory and inventory.quantity >= restock_request.quantity:
        # Check for existing StoreInventory record
        existing_inventory = StoreInventory.objects.filter(
            product=restock_request.product,
            store=restock_request.store
        ).first()
        if existing_inventory:
          # Update existing record quantity
          existing_inventory.quantity += restock_request.quantity
          existing_inventory.save()
        else:
          # Create new StoreInventory record if none exists
          StoreInventory.objects.create(
              product=restock_request.product,
              store=restock_request.store,
              quantity=restock_request.quantity,
          )
        inventory.quantity -= restock_request.quantity
        inventory.save()
        restock_request.status = "delivered"
      else:
        restock_request.status = "rejected"
        restock_request.comments = "Insufficient manufactured product inventory."
      restock_request.save()