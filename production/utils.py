from decimal import Decimal
from django.db import transaction
from production.models import ManufacturedProductInventory, PurchaseOrder, RequisitionItem, RestockRequest, StoreInventory


def cost_per_unit(self):
  ingredient_costs = []
  for ingredient in self.productioningredients.all():
    # Get most recent purchase order for the ingredient
    latest_requisition_item = RequisitionItem.objects.filter(
        raw_material=ingredient.raw_material,
        requisition__status='delivered' #ensure that requisitioin has been finally delivered into items in store
    ).order_by('-requisition__created_at').first()  # Order by descending creation date

    if latest_requisition_item:
        print(latest_requisition_item)
        print(latest_requisition_item.raw_material)
        print(latest_requisition_item.raw_material.__dict__)
        unit_of_measurement = latest_requisition_item.raw_material.unit_measurement.lower()
        
        purchase_price_per_unit = latest_requisition_item.price_per_unit

      # Conversion factor to convert base units (e.g., grams, milliliters) to the stored unit (kilograms, liters)

        if unit_of_measurement in ['kilograms', 'kg']:
                price_per_base_unit = purchase_price_per_unit / 1000  # Convert kg to gram price
        elif unit_of_measurement in ['liters', 'litres', 'l']:
                price_per_base_unit = purchase_price_per_unit / 1000  # Convert liter to ml price
        else:
            price_per_base_unit = purchase_price_per_unit  # Use price per unit for items like bottles or pieces
        
        cost_per_ingredient = price_per_base_unit * ingredient.quantity_per_unit_product_volume
    else:
      # Handle case where no purchase history exists (optional: set default cost)
      cost_per_ingredient = 0  # You might want to set a default cost here
    
    ingredient_cost_data = {
        'name': ingredient.raw_material.name,
        'quantity': ingredient.quantity_per_unit_product_volume,
        'cost_per_unit': cost_per_ingredient,
        'unit_measurement': ingredient.raw_material.unit_measurement
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