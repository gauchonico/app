/*
Template Name: HUD DJANGO - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud-django/
*/

var handleFilter = function() {
	"use strict";
	
	$(document).on('click', '.pos-menu [data-filter]', function(e) {
		e.preventDefault();
		
		var targetType = $(this).attr('data-filter');
		
		$(this).addClass('active');
		$('.pos-menu [data-filter]').not(this).removeClass('active');
		if (targetType == 'all') {
			$('.pos-content [data-type]').removeClass('d-none');
		} else {
			$('.pos-content [data-type="'+ targetType +'"]').removeClass('d-none');
			$('.pos-content [data-type]').not('.pos-content [data-type="'+ targetType +'"]').addClass('d-none');
		}
	});
};

document.addEventListener('DOMContentLoaded', function() {
	handleFilter();
});

// show service model
function showServiceModal(serviceId, serviceName, servicePrice) {
    console.log('Opening service modal:', serviceId);
    selectedService = {
        id: serviceId,
        name: serviceName,
        price: parseFloat(servicePrice)
    };
    
    // Update modal content
    document.getElementById('serviceName').textContent = serviceName;
    
    // Show the modal using Bootstrap
    const modal = new bootstrap.Modal(document.getElementById('serviceModal'));
    modal.show();
}

// Update the product modal display
function showProductModal(productId, name, price, stock) {
    selectedProduct = {
        id: productId,
        name: name,
        defaultPrice: parseFloat(price),
        stock: parseInt(stock)
    };
    
    document.getElementById('productName').textContent = name;
    document.getElementById('productQuantity').value = 1;
    document.getElementById('productQuantity').max = stock;
    
    // Fetch available price groups for this product
    fetch(`/api/product/${productId}/price-groups/`)
        .then(response => response.json())
        .then(data => {
            const priceGroupSelect = document.getElementById('priceGroup');
            priceGroupSelect.innerHTML = '<option value="">Default Price</option>';
            
            data.price_groups.forEach(group => {
                priceGroupSelect.innerHTML += `
                    <option value="${group.id}" data-price="${group.price}">
                        ${group.name} - $${group.price}
                    </option>
                `;
            });
            
            updateDisplayPrice();
        });
    
    new bootstrap.Modal(document.getElementById('productModal')).show();
}

// Update price display when price group changes
function updateDisplayPrice() {
    const priceGroupSelect = document.getElementById('priceGroup');
    const selectedOption = priceGroupSelect.selectedOptions[0];
    const price = selectedOption.dataset.price || selectedProduct.defaultPrice;
    
    document.getElementById('productPrice').textContent = `$${parseFloat(price).toFixed(2)}`;
}

// Update the addProductToCart function
function addProductToCart() {
    const quantity = parseInt(document.getElementById('productQuantity').value);
    const priceGroupSelect = document.getElementById('priceGroup');
    const priceGroupId = priceGroupSelect.value;
    const selectedOption = priceGroupSelect.selectedOptions[0];
    const price = selectedOption.dataset.price || selectedProduct.defaultPrice;
    
    const productItem = {
        type: 'product',
        id: selectedProduct.id,
        name: selectedProduct.name,
        quantity: quantity,
        price_group_id: priceGroupId || null,
        unit_price: parseFloat(price),
        total: parseFloat(price) * quantity
    };
    
    cart.items.products.push(productItem);
    updateCartDisplay();
    calculateTotals();
    
    bootstrap.Modal.getInstance(document.getElementById('productModal')).hide();
}

// Add this to your JavaScript file or console to test
document.addEventListener('DOMContentLoaded', function() {
    const testModal = new bootstrap.Modal(document.getElementById('serviceModal'));
    testModal.show(); // Uncomment to test
});