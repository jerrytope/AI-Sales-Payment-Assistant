/* Client-Side JavaScript Logic for Conversational Commerce Dashboard */

let activeCustomerId = null;
let chatPollInterval = null;

// --- UTILITIES ---
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('en-NG', { timeZone: 'Africa/Lagos', hour12: true });
}

function formatCurrency(amountKobo) {
    return (amountKobo / 100).toLocaleString('en-NG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// --- CONVERSATIONS VIEW ---
function initConversationsView() {
    fetchCustomers();
    
    // Search Box Listener
    document.getElementById("search-box").addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase();
        filterCustomerCards(query);
    });

    // Refresh every 10 seconds for customer list
    setInterval(fetchCustomers, 10000);
}

function fetchCustomers() {
    fetch("/api/customers/")
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById("customer-list-container");
            const customers = data.results || data;
            
            if (!customers || customers.length === 0) {
                container.innerHTML = `<div style="padding: 20px; text-align: center; color: var(--text-secondary);">No conversations found.</div>`;
                return;
            }

            let html = '';
            customers.forEach(c => {
                const isActive = activeCustomerId === c.id ? 'active' : '';
                const lastMsgText = c.extra_data && c.extra_data.last_message ? c.extra_data.last_message : 'No messages yet';
                const dateDisplay = c.last_message_at ? new Date(c.last_message_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
                
                html += `
                    <div class="customer-card ${isActive}" onclick="selectCustomer(${c.id})" data-id="${c.id}" data-search="${(c.name || '').toLowerCase()} ${c.phone_number}">
                        <div class="card-header">
                            <span class="customer-name">${c.name || c.phone_number}</span>
                            <span class="customer-time">${dateDisplay}</span>
                        </div>
                        <div class="card-body">
                            <span class="last-msg">${c.phone_number}</span>
                            <span class="badge badge-${c.workflow_state.toLowerCase()}">${c.workflow_state.replace('_', ' ')}</span>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        })
        .catch(err => console.error("Error fetching customers:", err));
}

function filterCustomerCards(query) {
    const cards = document.querySelectorAll(".customer-card");
    cards.forEach(card => {
        const searchText = card.getAttribute("data-search");
        if (searchText.includes(query)) {
            card.style.display = "block";
        } else {
            card.style.display = "none";
        }
    });
}

function selectCustomer(id) {
    activeCustomerId = id;
    
    // Update active visual class
    document.querySelectorAll(".customer-card").forEach(card => {
        card.classList.remove("active");
        if (parseInt(card.getAttribute("data-id")) === id) {
            card.classList.add("active");
        }
    });

    loadChat(id);

    // Setup chat polling
    if (chatPollInterval) clearInterval(chatPollInterval);
    chatPollInterval = setInterval(() => loadChat(id, true), 3000);
}

function loadChat(id, isPoll = false) {
    fetch(`/api/customers/${id}/`)
        .then(res => res.json())
        .then(c => {
            const panel = document.getElementById("chat-window-panel");
            
            // Build Messages html
            let msgsHtml = '';
            if (c.messages && c.messages.length > 0) {
                c.messages.forEach(m => {
                    const bubbleClass = m.direction === 'INBOUND' ? 'message-inbound' : 'message-outbound';
                    const senderLabel = m.sender_type;
                    const senderBadge = senderLabel === 'USER' ? 'User' : (senderLabel === 'BOT' ? 'Bot' : 'Admin');
                    const badgeClass = senderLabel.toLowerCase();

                    msgsHtml += `
                        <div class="message-bubble ${bubbleClass}">
                            <p>${m.body}</p>
                            <div class="msg-meta">
                                <span class="msg-sender badge badge-${badgeClass}">${senderBadge}</span>
                                <span class="msg-time">${formatDate(m.created_at)}</span>
                            </div>
                        </div>
                    `;
                });
            } else {
                msgsHtml = `<div style="text-align: center; color: var(--text-secondary); margin: auto;">No messages in this chat.</div>`;
            }

            // Header elements
            const takeoverText = c.human_takeover ? 'Release Takeover' : 'Take Over Chat';
            const takeoverBtnClass = c.human_takeover ? 'btn-secondary' : 'btn-danger';
            const statusBadgeText = c.human_takeover ? 'Takeover Active' : 'AI Active';
            const statusBadgeClass = c.human_takeover ? 'badge-takeover' : 'badge-bot';

            // Only redraw wrapper if not polling (prevents scroll jumps or input redraws)
            if (!isPoll || !document.getElementById("active-chat-header")) {
                panel.innerHTML = `
                    <div class="window-header" id="active-chat-header">
                        <div class="window-user-info">
                            <span class="window-name">${c.name || 'Anonymous Customer'}</span>
                            <span class="window-phone">${c.phone_number}</span>
                        </div>
                        <div class="window-actions">
                            <span class="badge ${statusBadgeClass}" style="display: flex; align-items: center;">${statusBadgeText}</span>
                            <button class="btn ${takeoverBtnClass}" onclick="handleTakeover(${c.id})">${takeoverText}</button>
                        </div>
                    </div>
                    
                    <div class="chat-messages" id="message-container">
                        ${msgsHtml}
                    </div>
                    
                    <div class="chat-input-area">
                        <input type="text" id="admin-message-input" class="chat-input" placeholder="Type manual message (this will automatically activate takeover)...">
                        <button class="btn btn-primary" onclick="sendAdminMessage(${c.id})">Send</button>
                    </div>
                `;
                
                // Add Enter listener on input
                document.getElementById("admin-message-input").addEventListener("keypress", (e) => {
                    if (e.key === "Enter") {
                        sendAdminMessage(c.id);
                    }
                });
                
                scrollChatToBottom();
            } else {
                // Just update messages and headers without re-rendering inputs
                const container = document.getElementById("message-container");
                const wasScrolledBottom = container.scrollHeight - container.clientHeight <= container.scrollTop + 50;
                
                container.innerHTML = msgsHtml;
                
                // Update takeover button and badges
                const actionBtn = panel.querySelector(".window-actions button");
                actionBtn.className = `btn ${takeoverBtnClass}`;
                actionBtn.innerText = takeoverText;
                
                const statusBadge = panel.querySelector(".window-actions .badge");
                statusBadge.className = `badge ${statusBadgeClass}`;
                statusBadge.innerText = statusBadgeText;
                
                if (wasScrolledBottom) {
                    scrollChatToBottom();
                }
            }
        })
        .catch(err => console.error("Error loading chat:", err));
}

function scrollChatToBottom() {
    const container = document.getElementById("message-container");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function handleTakeover(id) {
    fetch(`/api/customers/${id}/takeover/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken
        }
    })
    .then(res => res.json())
    .then(data => {
        showNotification(data.human_takeover ? "Human agent takeover activated" : "Takeover released back to AI bot");
        loadChat(id);
        fetchCustomers();
    })
    .catch(err => console.error("Error toggling takeover:", err));
}

function sendAdminMessage(id) {
    const input = document.getElementById("admin-message-input");
    const body = input.value.trim();
    if (!body) return;

    // Clear input instantly
    input.value = '';

    fetch(`/api/customers/${id}/send-message/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken
        },
        body: JSON.stringify({ body })
    })
    .then(res => {
        if (!res.ok) throw new Error("Failed to send message");
        return res.json();
    })
    .then(data => {
        showNotification("Message sent successfully!");
        loadChat(id);
        fetchCustomers();
    })
    .catch(err => {
        showNotification("Failed to send message. Check Twilio credentials.", "error");
        console.error("Error sending admin message:", err);
    });
}

// --- PAYMENTS VIEW ---
function initPaymentsView() {
    fetchOrders();

    // Filters event listeners
    document.getElementById("status-filter").addEventListener("change", fetchOrders);
    document.getElementById("payments-search-box").addEventListener("input", fetchOrders);
}

function fetchOrders() {
    const statusFilter = document.getElementById("status-filter").value;
    const searchVal = document.getElementById("payments-search-box").value.toLowerCase();
    
    let url = "/api/orders/";
    const params = [];
    if (statusFilter) params.push(`status=${statusFilter}`);
    if (params.length > 0) url += `?${params.join("&")}`;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById("payments-table-body");
            const orders = data.results || data;
            
            if (!orders || orders.length === 0) {
                container.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 40px;">No transaction records found.</td></tr>`;
                return;
            }

            // Client side search mapping
            const filteredOrders = orders.filter(o => {
                const searchString = `${o.paystack_reference} ${o.customer_phone || ''}`.toLowerCase();
                return searchString.includes(searchVal);
            });

            if (filteredOrders.length === 0) {
                container.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 40px;">No matching records found.</td></tr>`;
                return;
            }

            let html = '';
            filteredOrders.forEach(o => {
                html += `
                    <tr>
                        <td><strong>${o.customer_name || 'Anonymous'}</strong><br><span style="font-size:0.8rem; color:var(--text-secondary);">${o.customer_phone}</span></td>
                        <td><code style="background:rgba(255,255,255,0.05); padding:4px 8px; border-radius:4px; font-size:0.85rem;">${o.paystack_reference}</code></td>
                        <td><strong>₦${formatCurrency(o.amount_kobo)}</strong></td>
                        <td><span class="badge badge-${o.status.toLowerCase()}">${o.status}</span></td>
                        <td style="text-align:center;">${o.reminder_count}</td>
                        <td>${formatDate(o.created_at)}</td>
                        <td>${o.paid_at ? formatDate(o.paid_at) : '<span style="color:var(--text-secondary);">-</span>'}</td>
                    </tr>
                `;
            });
            container.innerHTML = html;
        })
        .catch(err => console.error("Error fetching orders:", err));
}

// --- SETTINGS VIEW ---
function initSettingsView() {
    fetchSettings();

    // Form submit listener
    document.getElementById("settings-form").addEventListener("submit", saveSettings);
}

function fetchSettings() {
    fetch("/api/settings/")
        .then(res => res.json())
        .then(settingsList => {
            const settings = settingsList.results || settingsList;
            settings.forEach(s => {
                const field = document.getElementById(`setting-${s.setting_key}`);
                if (field) {
                    field.value = s.setting_value;
                }
            });
        })
        .catch(err => console.error("Error fetching business settings:", err));
}

function saveSettings(e) {
    e.preventDefault();

    const keys = ["business_name", "support_phone", "product_catalog", "ai_base_prompt"];
    let promises = [];

    // Verify product_catalog is valid JSON
    const catalogInput = document.getElementById("setting-product_catalog").value;
    try {
        JSON.parse(catalogInput);
    } catch(e) {
        showNotification("Product catalog field must be in valid JSON format!", "error");
        return;
    }

    keys.forEach(key => {
        const val = document.getElementById(`setting-${key}`).value;
        const promise = fetch(`/api/settings/${key}/`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrftoken
            },
            body: JSON.stringify({
                setting_key: key,
                setting_value: val
            })
        });
        promises.push(promise);
    });

    Promise.all(promises)
        .then(responses => {
            const failed = responses.filter(r => !r.ok);
            if (failed.length > 0) {
                showNotification("Failed to save some settings.", "error");
            } else {
                showNotification("All settings successfully saved!");
            }
        })
        .catch(err => {
            showNotification("Failed to connect to configurations API.", "error");
            console.error("Error saving settings:", err);
        });
}
