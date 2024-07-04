from decimal import Decimal
from django.db import transaction
from production.models import ManufacturedProductInventory, PurchaseOrder, RestockRequest, StoreInventory


def cost_per_unit(self):
  ingredient_costs = []
  for ingredient in self.productioningredients.all():
    # Get most recent purchase order for the ingredient
    latest_purchase = PurchaseOrder.objects.filter(
        raw_material=ingredient.raw_material
    ).order_by('-created_at').first()  # Order by descending creation date

    if latest_purchase:
      unit_of_measurement = latest_purchase.raw_material.unit_measurement

      conversion_factor = 1
      if unit_of_measurement == 'Kilograms':
          conversion_factor = 1000  # Convert ml to liters
      elif unit_of_measurement == 'Liters':
          # Add conversion for grams if applicable
          conversion_factor = 1000  # Implement conversion based on your data
      
      quantity_in_desired_unit = ingredient.quantity_per_unit_product_volume / conversion_factor
      cost_per_ingredient =  quantity_in_desired_unit * latest_purchase.unit_price 
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