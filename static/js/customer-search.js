/**
 * Reusable Customer Search Functionality
 * This file provides customer search and creation functionality that can be used across different POS pages
 */

class CustomerSearch {
    constructor(options = {}) {
        this.customers = options.customers || [];
        this.searchInputId = options.searchInputId || 'customerSearch';
        this.dropdownId = options.dropdownId || 'customerDropdown';
        this.selectedCustomerIdId = options.selectedCustomerIdId || 'selectedCustomerId';
        this.selectedCustomerInfoId = options.selectedCustomerInfoId || 'selectedCustomerInfo';
        this.selectedCustomerNameId = options.selectedCustomerNameId || 'selectedCustomerName';
        this.modalId = options.modalId || 'customerModal';
        this.formId = options.formId || 'newCustomerForm';
        this.createUrl = options.createUrl || '/api/customers/create/';
        this.onCustomerSelect = options.onCustomerSelect || null;
        this.onCustomerClear = options.onCustomerClear || null;
        
        this.selectedCustomerId = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupCustomerSearch();
    }
    
    setupEventListeners() {
        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const searchInput = document.getElementById(this.searchInputId);
            const dropdown = document.getElementById(this.dropdownId);
            
            if (searchInput && dropdown && 
                !searchInput.contains(e.target) && 
                !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });
    }
    
    setupCustomerSearch() {
        const customerSearch = document.getElementById(this.searchInputId);
        const customerDropdown = document.getElementById(this.dropdownId);
        
        if (!customerSearch || !customerDropdown) {
            console.error('Customer search elements not found');
            return;
        }
        
        customerSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            console.log('Customer search query:', query);
            console.log('Available customers:', this.customers);
            
            if (query.length < 1) {
                customerDropdown.style.display = 'none';
                return;
            }
            
            const filteredCustomers = this.customers.filter(customer => 
                customer.first_name.toLowerCase().includes(query) ||
                customer.last_name.toLowerCase().includes(query) ||
                customer.phone.includes(query)
            );
            
            console.log('Filtered customers:', filteredCustomers);
            
            if (filteredCustomers.length > 0) {
                customerDropdown.innerHTML = filteredCustomers.map(customer => 
                    `<div class="customer-item" onclick="window.customerSearchInstance.selectCustomer(${customer.id}, '${customer.first_name} ${customer.last_name}')">
                        <strong>${customer.first_name} ${customer.last_name}</strong><br>
                        <small class="text-muted">${customer.phone}</small>
                    </div>`
                ).join('');
                customerDropdown.style.display = 'block';
            } else {
                customerDropdown.innerHTML = `
                    <div class="customer-item" onclick="window.customerSearchInstance.showNewCustomerModal()">
                        <i class="fas fa-plus me-2"></i>Create new customer: "${query}"
                    </div>
                `;
                customerDropdown.style.display = 'block';
            }
        });
    }
    
    selectCustomer(customerId, customerName) {
        this.selectedCustomerId = customerId;
        
        const selectedCustomerIdElement = document.getElementById(this.selectedCustomerIdId);
        const selectedCustomerNameElement = document.getElementById(this.selectedCustomerNameId);
        const selectedCustomerInfoElement = document.getElementById(this.selectedCustomerInfoId);
        const searchInput = document.getElementById(this.searchInputId);
        const dropdown = document.getElementById(this.dropdownId);
        
        if (selectedCustomerIdElement) selectedCustomerIdElement.value = customerId;
        if (selectedCustomerNameElement) selectedCustomerNameElement.textContent = customerName;
        if (selectedCustomerInfoElement) selectedCustomerInfoElement.style.display = 'block';
        if (searchInput) searchInput.value = '';
        if (dropdown) dropdown.style.display = 'none';
        
        // Call custom callback if provided
        if (this.onCustomerSelect && typeof this.onCustomerSelect === 'function') {
            this.onCustomerSelect(customerId, customerName);
        }
    }
    
    clearCustomer() {
        this.selectedCustomerId = null;
        
        const selectedCustomerIdElement = document.getElementById(this.selectedCustomerIdId);
        const selectedCustomerInfoElement = document.getElementById(this.selectedCustomerInfoId);
        
        if (selectedCustomerIdElement) selectedCustomerIdElement.value = '';
        if (selectedCustomerInfoElement) selectedCustomerInfoElement.style.display = 'none';
        
        // Call custom callback if provided
        if (this.onCustomerClear && typeof this.onCustomerClear === 'function') {
            this.onCustomerClear();
        }
    }
    
    showNewCustomerModal() {
        const dropdown = document.getElementById(this.dropdownId);
        if (dropdown) dropdown.style.display = 'none';
        
        // Pre-fill the form with the search query if it looks like a name
        const searchInput = document.getElementById(this.searchInputId);
        if (searchInput) {
            const searchQuery = searchInput.value.trim();
            if (searchQuery) {
                const nameParts = searchQuery.split(' ');
                const firstNameInput = document.getElementById('newCustomerFirstName');
                const lastNameInput = document.getElementById('newCustomerLastName');
                
                if (nameParts.length >= 2 && firstNameInput && lastNameInput) {
                    firstNameInput.value = nameParts[0];
                    lastNameInput.value = nameParts.slice(1).join(' ');
                } else if (firstNameInput) {
                    firstNameInput.value = searchQuery;
                }
            }
        }
        
        const modal = document.getElementById(this.modalId);
        if (modal) {
            new bootstrap.Modal(modal).show();
        }
    }
    
    createCustomer() {
        const firstName = document.getElementById('newCustomerFirstName')?.value;
        const lastName = document.getElementById('newCustomerLastName')?.value;
        const phone = document.getElementById('newCustomerPhone')?.value;
        const email = document.getElementById('newCustomerEmail')?.value;
        
        if (!firstName || !lastName || !phone) {
            alert('Please fill in all required fields');
            return;
        }
        
        // Create customer via AJAX
        fetch(this.createUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify({
                first_name: firstName,
                last_name: lastName,
                phone: phone,
                email: email
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Add to customers array
                this.customers.push(data.customer);
                // Select the new customer
                this.selectCustomer(data.customer.id, `${data.customer.first_name} ${data.customer.last_name}`);
                // Close modal
                const modal = document.getElementById(this.modalId);
                if (modal) {
                    bootstrap.Modal.getInstance(modal).hide();
                }
                // Clear form
                const form = document.getElementById(this.formId);
                if (form) form.reset();
            } else {
                alert('Error creating customer: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error creating customer');
        });
    }
    
    getCookie(name) {
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
    
    // Method to update customers array
    updateCustomers(newCustomers) {
        this.customers = newCustomers;
    }
    
    // Method to get selected customer ID
    getSelectedCustomerId() {
        return this.selectedCustomerId;
    }
}

// Global functions for backward compatibility and easy access
window.customerSearchInstance = null;

function setupCustomerSearch(options = {}) {
    window.customerSearchInstance = new CustomerSearch(options);
    return window.customerSearchInstance;
}

function selectCustomer(customerId, customerName) {
    if (window.customerSearchInstance) {
        window.customerSearchInstance.selectCustomer(customerId, customerName);
    }
}

function clearCustomer() {
    if (window.customerSearchInstance) {
        window.customerSearchInstance.clearCustomer();
    }
}

function showNewCustomerModal() {
    if (window.customerSearchInstance) {
        window.customerSearchInstance.showNewCustomerModal();
    }
}

function createCustomer() {
    if (window.customerSearchInstance) {
        window.customerSearchInstance.createCustomer();
    }
}

// Export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CustomerSearch;
}
