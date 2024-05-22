from decimal import Decimal
from production.models import PurchaseOrder


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
        'cost_per_unit': cost_per_ingredient
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