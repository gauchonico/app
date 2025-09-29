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
function showProductModal(productId, productName, stock) {
    // Store product details
    selectedProduct = {
        id: productId,
        name: productName,
        stock: parseInt(stock) || 0
    };
    
    // Update modal title
    document.getElementById('productName').textContent = productName;
    document.getElementById('productQuantity').value = 1;
    document.getElementById('productQuantity').max = stock;
    document.getElementById('selectedPrice').textContent = 'Loading price...';

    const url = `/production/get_product_price_groups/${productId}/`;

    // Fetch retail price
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.price_groups && data.price_groups.length > 0) {
                const retailPrice = data.price_groups[0];
                document.getElementById('priceGroup').value = retailPrice.id;
                document.getElementById('selectedPrice').textContent = 
                    parseFloat(retailPrice.price).toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'UGX',
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 0
                    });
                // Enable the Add Product button
                document.querySelector('#productModal .btn-theme').disabled = false;
            } else {
                // Show message and disable Add Product button when no retail price is found
                document.getElementById('selectedPrice').innerHTML = `
                    <div class="text-danger">
                        <i class="bi bi-exclamation-triangle"></i> No retail price set
                    </div>
                    <small class="text-muted">Please add a retail price for this product first</small>
                `;
                // Disable the Add Product button
                document.querySelector('#productModal .btn-theme').disabled = true;
            }
        })
        .catch(error => {
            console.error('Error fetching price:', error);
            document.getElementById('selectedPrice').innerHTML = `
                <div class="text-danger">
                    <i class="bi bi-exclamation-triangle"></i> Error loading price
                </div>
                <small class="text-muted">Please ensure a retail price is set for this product</small>
            `;
            // Disable the Add Product button
            document.querySelector('#productModal .btn-theme').disabled = true;
        });

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('productModal'));
    modal.show();
}

// Function to update the displayed price when price group changes
function updateProductPrice() {
    const priceGroupSelect = document.getElementById('priceGroup');
    const selectedOption = priceGroupSelect.selectedOptions[0];
    const priceDisplay = document.getElementById('selectedPrice');
    
    if (selectedOption && selectedOption.dataset.price) {
        const price = parseFloat(selectedOption.dataset.price);
        const formattedPrice = price.toLocaleString('en-US', {
            style: 'currency',
            currency: 'UGX',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
        priceDisplay.textContent = formattedPrice;
    } else {
        priceDisplay.textContent = 'Please select a price group';
    }
}

// Update price display when price group changes
function updateDisplayPrice() {
    const priceGroupSelect = document.getElementById('priceGroup');
    const selectedOption = priceGroupSelect.selectedOptions[0];
    const price = selectedOption.dataset.price || selectedProduct.defaultPrice;
    
    document.getElementById('productPrice').textContent = `$${parseFloat(price).toFixed(2)}`;
}



// Update the modal HTML to pass the modal ID

function showAccessoryModal(accessoryId, name, price, stock) {
    console.log('Opening accessory modal:', accessoryId);
    selectedAccessory = {
        id: accessoryId,
        name: name,
        price: parseFloat(price),
        stock: parseInt(stock)
    };
    
    document.getElementById('accessoryName').textContent = name;
    document.getElementById('accessoryQuantity').value = 1;
    document.getElementById('accessoryQuantity').max = stock;
    
    const modal = new bootstrap.Modal(document.getElementById('accessoryModal'));
    modal.show();
}

// Add new customer model 
function showNewCustomerModal() {
    const modal = new bootstrap.Modal(document.getElementById('newCustomerModal'));
    modal.show();
}

// Add event listener for new customer form submission
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('newCustomerForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch('/api/customers/create/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Add new customer to select dropdown
                const select = document.getElementById('customerSelect');
                const option = new Option(
                    `${data.customer.first_name} ${data.customer.last_name}`,
                    data.customer.id
                );
                select.add(option);
                select.value = data.customer.id;
                
                // Close modal and reset form
                bootstrap.Modal.getInstance(document.getElementById('newCustomerModal')).hide();
                this.reset();
            } else {
                alert(data.message || 'Error creating customer');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error creating customer');
        });
    });
});

// Product quantity handlers
function incrementQuantity(modalId) {
    const input = document.getElementById(`${modalId}Quantity`);
    const max = parseInt(input.max) || Infinity;
    const currentValue = parseInt(input.value);
    if (currentValue < max) {
        input.value = currentValue + 1;
    }
}

function decrementQuantity(modalId) {
    const input = document.getElementById(`${modalId}Quantity`);
    const currentValue = parseInt(input.value);
    if (currentValue > 1) {
        input.value = currentValue - 1;
    }
}


// Cart management
let cart = {
    customer: null,
    items: [],
    totals: {
        subtotal: 0,
        total: 0
    }
};

function addServiceToCart() {
    const staffSelect = document.getElementById('serviceStaff');
    const selectedStaff = Array.from(staffSelect.selectedOptions).map(option => ({
        id: option.value,
        name: option.text
    }));
    
    if (selectedStaff.length === 0) {
        alert('Please select at least one staff member');
        return;
    }
    
    const serviceItem = {
        type: 'service',
        id: parseInt(selectedService.id),
        name: selectedService.name,
        quantity: 1,
        price: parseFloat(selectedService.price),
        total: parseFloat(selectedService.price),
        selected_staff: selectedStaff.map(staff => staff.id)  // Just keep the IDs
    };
    
    cart.items.push(serviceItem);
    updateCartDisplay();
    calculateTotals();
    
    bootstrap.Modal.getInstance(document.getElementById('serviceModal')).hide();
}

// Function to add product to cart
function addProductToCart() {
    const priceGroupId = document.getElementById('priceGroup').value;
    const staffSelect = document.getElementById('productStaff');
    const selectedStaff = staffSelect.value ? {
        id: staffSelect.value,
        name: staffSelect.options[staffSelect.selectedIndex].text
    } : null;

    if (!priceGroupId) {
        alert('Price not available for this product');
        return;
    }

    const quantity = parseInt(document.getElementById('productQuantity').value);
    const price = parseFloat(document.getElementById('selectedPrice').textContent.replace(/[^0-9.-]+/g, ''));
    
    const productItem = {
        type: 'product',
        id: selectedProduct.id,
        name: selectedProduct.name,
        quantity: quantity,
        price_group_id: priceGroupId,
        price_group_name: 'Retail',
        unit_price: price,
        total: price * quantity,
        staff: selectedStaff
    };
    
    cart.items.push(productItem);
    updateCartDisplay();
    calculateTotals();
    
    bootstrap.Modal.getInstance(document.getElementById('productModal')).hide();
}

function addAccessoryToCart() {
    const quantity = parseInt(document.getElementById('accessoryQuantity').value);
    const unitPrice = parseFloat(selectedAccessory.price);
    
    const accessoryItem = {
        type: 'accessory',
        id: parseInt(selectedAccessory.id),
        name: selectedAccessory.name,
        quantity: quantity,
        unit_price: unitPrice,  // Store unit price separately
        price: parseFloat(selectedAccessory.price).toFixed(2),
        total: parseFloat(selectedAccessory.price).toFixed(2) * quantity
    };
    
    cart.items.push(accessoryItem);
    updateCartDisplay();
    // calculateTotals(); only show don't add on totals
    
    bootstrap.Modal.getInstance(document.getElementById('accessoryModal')).hide();
}

function updateCartDisplay() {
    const cartContainer = document.getElementById('cartItems');
    cartContainer.innerHTML = '';
    
    cart.items.forEach((item, index) => {
        const itemElement = document.createElement('div');
        itemElement.className = 'pos-order';
        
        let staffHtml = '';
        if (item.type === 'service' && item.staff) {
            staffHtml = `
                <div class="small">
                    Staff: ${item.staff.map(s => s.name).join(', ')}
                </div>
            `;
        }

        let quantityHtml = item.type !== 'service' ? 
            `<div class="small">Quantity: ${item.quantity}</div>` : '';

        itemElement.innerHTML = `
            <div class="pos-order-product">
                <div class="flex-1">
                    <div class="h6 mb-1">${item.name}</div>
                    ${quantityHtml}
                    ${staffHtml}
                    
                </div>
                <div class="pos-order-price">
                    $${item.total.toFixed(0)}
                </div>
                <button class="btn btn-sm btn-danger ms-2" onclick="removeFromCart(${index})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        
        cartContainer.appendChild(itemElement);
    });
}

function removeFromCart(index) {
    cart.items.splice(index, 1);
    updateCartDisplay();
    calculateTotals();
}

function calculateTotals() {
    cart.totals.subtotal = cart.items.reduce((sum, item) => sum + item.total, 0);
    cart.totals.total = cart.totals.subtotal;
    
    document.getElementById('subtotal').textContent = cart.totals.subtotal.toFixed(0);
    document.getElementById('total').textContent = cart.totals.total.toFixed(0);

    // Return the total for use in other functions
    return cart.totals.total;
}

function clearCart() {
    cart.items = [];
    updateCartDisplay();
    calculateTotals();
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
function submitSale() {
    // Get required data
    const customerId = document.getElementById('customerSelect').value;
    const storeId = document.getElementById('storeId').value; // Add this hidden input to your template
    console.log('Store ID:', storeId);  // Debug log
    // Debug log for cart items
    console.log('Full cart contents:', cart.items);
    
    if (!customerId) {
        alert('Please select a customer');
        return;
    }

    if (!storeId || storeId === '') {
        alert('Store ID is missing. Please contact your administrator.');
        return;
    }

    if (!cart.items || cart.items.length === 0) {
        alert('Cart is empty');
        return;
    }
    // Get the total amount from calculateTotals
    const totalAmount = calculateTotals();

    // Separate items by type
    const productItems = [];
    const serviceItems = [];
    const accessoryItems = [];
    const url = `/production/new_create_service_sale/`;

    // Filter and validate items before mapping
    const saleData = {
        customer_id: parseInt(customerId),  // Convert to integer
        store_id: parseInt(storeId),       // Convert to integer
        product_items: cart.items
            .filter(item => item.type === 'product')
            .map(item => ({
                product_id: parseInt(item.id),
                quantity: parseInt(item.quantity),
                price_group_id: item.price_group_id ? parseInt(item.price_group_id) : null,
                total_price: parseFloat(item.total),
                staff_id: item.staff ? parseInt(item.staff.id) : null  // Add staff ID here
            })),
        service_items: cart.items
            .filter(item => item.type === 'service')
            .map(item => ({
                service_id: parseInt(item.id),
                quantity: parseFloat(item.quantity),
                staff_ids: item.selected_staff,
                total_price: parseFloat(item.total)
            })),
        accessory_items: cart.items
            .filter(item => item.type === 'accessory')
            .map(item => ({
                accessory_id: parseInt(item.id),
                quantity: parseFloat(item.quantity),
                price: parseFloat(item.unit_price).toFixed(2),
                total_price: parseFloat(item.total).toFixed(2) 
            })),
        total_amount: totalAmount.toFixed(2),
        paid_status: 'not_paid',
        payment_mode: 'cash'
    };

    console.log('Submitting sale data:', saleData);  // Debug log



    // Submit the sale
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(saleData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Sale created successfully!');
            // Clear the cart
            cart.items = [];
            updateCartDisplay();
            // Redirect to the sale detail page
            window.location.href = data.redirect_url;
        } else {
            alert('Error creating sale: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error creating sale. Please try again.');
    });
}