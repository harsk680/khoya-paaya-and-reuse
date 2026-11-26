
const API = "http://127.0.0.1:8000";

let token = localStorage.getItem("access_token");

let currentUserId = null;

function showMessage(message) {
    alert(message);
}


function createModal(title, fields, submitText, onSubmit) {
    const oldModal = document.getElementById("app-modal");
    if (oldModal) oldModal.remove();

    const modal = document.createElement("div");
    modal.id = "app-modal";

    modal.style.cssText = `
        position:fixed;
        inset:0;
        background:rgba(0,0,0,0.6);
        display:flex;
        justify-content:center;
        align-items:center;
        z-index:9999;
        padding:20px;
    `;

    const form = document.createElement("form");
    form.style.cssText = `
        background:white;
        padding:30px;
        border-radius:12px;
        width:100%;
        max-width:450px;
        display:flex;
        flex-direction:column;
        gap:14px;
        max-height:90vh;
        overflow-y:auto;
    `;

    const heading = document.createElement("h2");
    heading.textContent = title;
    form.appendChild(heading);

    const fieldElements = {};

    fields.forEach(field => {
        const wrapper = document.createElement("div");
        wrapper.style.cssText = `
            display:flex;
            flex-direction:column;
            gap:6px;
        `;

        let input;

        if (field.type === "select") {
            input = document.createElement("select");

            field.options.forEach(option => {
                const optionElement = document.createElement("option");
                optionElement.value = option.value;
                optionElement.textContent = option.label;
                input.appendChild(optionElement);
            });

        } else if (field.type === "textarea") {
            input = document.createElement("textarea");
            input.rows = 3;
            input.placeholder = field.label;

        } else {
            input = document.createElement("input");
            input.type = field.type || "text";

            if (field.type === "file") {
                input.accept = "image/*";
                input.capture = "environment";
            } else {
                input.placeholder = field.label;
            }
        }

        input.name = field.name;
        input.required = field.required !== false;

        input.style.cssText = `
            padding:12px;
            border:1px solid #ccc;
            border-radius:6px;
            width:100%;
            box-sizing:border-box;
        `;

        const label = document.createElement("label");
        label.textContent = field.label;

        wrapper.appendChild(label);
        wrapper.appendChild(input);
        form.appendChild(wrapper);

        fieldElements[field.name] = {
            input,
            wrapper,
            field
        };
    });

    // Show/hide conditional fields
    function updateConditionalFields() {
        Object.values(fieldElements).forEach(({ input, wrapper, field }) => {
            if (field.showIf) {
                const controllingField = fieldElements[field.showIf.field];

                const shouldShow =
                    controllingField &&
                    controllingField.input.value === field.showIf.value;

                wrapper.style.display = shouldShow ? "flex" : "none";
                input.required = shouldShow && field.required !== false;

                if (!shouldShow) {
                    input.value = "";
                }
            }
        });
    }

    Object.values(fieldElements).forEach(({ input, field }) => {
        if (field.type === "select") {
            input.addEventListener("change", updateConditionalFields);
        }
    });

    updateConditionalFields();

    const submit = document.createElement("button");
    submit.type = "submit";
    submit.textContent = submitText;
    submit.style.background = "#222";
    submit.style.color = "white";
    form.appendChild(submit);

    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "Cancel";
    close.onclick = () => modal.remove();
    form.appendChild(close);

    form.onsubmit = async (event) => {
        event.preventDefault();

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        try {
            submit.disabled = true;
            await onSubmit(data, formData);
            modal.remove();
        } catch (error) {
            showMessage(error.message);
        } finally {
            submit.disabled = false;
        }
    };

    modal.appendChild(form);
    document.body.appendChild(modal);
}


async function apiRequest(endpoint, method, data, authenticated = false) {
    const headers = {
        "Content-Type": "application/json"
    };

    if (authenticated) {
        if (!token) {
            throw new Error("Please login first.");
        }
        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(API + endpoint, {
        method,
        headers,
        body: data ? JSON.stringify(data) : undefined
    });

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.detail || result.message || "Request failed");
    }

    if (result.status === "error") {
        throw new Error(result.message);
    }

    return result;
}

async function viewVerificationImage(foundId) {
    try {
        const response = await fetch(
            API + `/api/authority/found/${foundId}/verification-image`,
            {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            throw new Error("Unable to load verification image.");
        }

        const imageBlob = await response.blob();
        const imageUrl = URL.createObjectURL(imageBlob);

        const imageWindow = window.open("", "_blank");

        if (!imageWindow) {
            URL.revokeObjectURL(imageUrl);
            alert("Please allow pop-ups to view the image.");
            return;
        }

        imageWindow.document.write(`
            <html>
                <head><title>Verification Image</title></head>
                <body style="margin:0; display:flex; justify-content:center;
                align-items:center; background:#222; min-height:100vh;">
                    <img src="${imageUrl}" style="max-width:95%; max-height:95vh;">
                </body>
            </html>
        `);

    } catch (error) {
        alert(error.message);
    }
}


async function apiFormRequest(endpoint, formData, authenticated = false) {
    const headers = {};

    if (authenticated) {
        if (!token) {
            throw new Error("Please login first.");
        }

        headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(API + endpoint, {
        method: "POST",
        headers,
        body: formData
    });

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.detail || result.message || "Request failed");
    }

    if (result.status === "error") {
        throw new Error(result.message);
    }

    return result;
}


async function loadDashboard() {
    try {
        const result = await apiRequest("/api/me", "GET", null, true);

        const user = result.user;

        updateAuthUI(user);
        currentUserId = user.user_id;

        loadReuseListings();

        const dashboard = document.getElementById("dashboard");
        const studentDashboard = document.getElementById("student-dashboard");
        const authorityDashboard = document.getElementById("authority-dashboard");

        dashboard.style.display = "block";

        if (user.role === "authority") {

            studentDashboard.style.display = "none";
            authorityDashboard.style.display = "block";

            document.getElementById("authority-name").textContent = user.name;
            document.getElementById("authority-email").textContent = user.email;

            loadPendingClaims();
            loadClaimHistory();
            loadPossibleMatches();

        } else {

            authorityDashboard.style.display = "none";
            studentDashboard.style.display = "block";

            document.getElementById("user-name").textContent = user.name;
            document.getElementById("user-id").textContent = user.user_id;
            document.getElementById("user-email").textContent = user.email;
            document.getElementById("user-role").textContent = user.role;
        }

    } catch (error) {
        console.log("Dashboard error:", error.message);
    }
}


async function loadPendingClaims() {
    const container = document.getElementById("pending-claims-container");

    container.innerHTML = "<p>Loading pending claims...</p>";

    try {
        const result = await apiRequest(
            "/api/authority/pending-claims",
            "GET",
            null,
            true
        );

        container.innerHTML = "";

        if (!result.claims || result.claims.length === 0) {
            container.innerHTML = "<p>No pending claims available.</p>";
            return;
        }

        result.claims.forEach(claim => {
            const card = document.createElement("div");
            card.className = "dashboard-card";

            const title = document.createElement("h3");
            title.textContent = claim.title;

            const details = document.createElement("p");
            details.textContent =
                "Category: " + claim.category;

            const claimId = document.createElement("p");
            claimId.textContent =
                "Claim ID: #" + claim.claim_id;

            const foundId = document.createElement("p");
            foundId.textContent =
                "Found Item ID: #" + claim.found_id;

            const claimant = document.createElement("p");
            claimant.textContent =
                "Claimant: " + claim.claimant_name;

            const email = document.createElement("p");
            email.textContent =
                "Email: " + claim.claimant_email;

            const date = document.createElement("p");
            date.textContent =
                "Claim Date: " + claim.claim_date;

            const approveBtn = document.createElement("button");
            approveBtn.textContent = "Approve Claim";
            approveBtn.className = "approve-btn";
            approveBtn.addEventListener("click", () => {
                decideClaim(claim.claim_id, "approved");
            });
            const rejectBtn = document.createElement("button");
            rejectBtn.textContent = "Reject Claim";
            rejectBtn.className = "reject-btn";
            rejectBtn.addEventListener("click", () => {
                decideClaim(claim.claim_id, "rejected");
            });
            const imageBtn = document.createElement("button");
            imageBtn.textContent = "View Verification Image";
            imageBtn.className = "image-btn";
            imageBtn.addEventListener("click", () => {
                viewVerificationImage(claim.found_id);
            });


            card.append(title, details, claimId, foundId,claimant, email, date,imageBtn, approveBtn, rejectBtn);
            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML =
            "<p>Unable to load pending claims.</p>";

        console.error("Pending claims error:", error);
    }
}

async function loadClaimHistory() {
    const container = document.getElementById("claim-history-container");

    container.innerHTML = "<p>Loading claim history...</p>";

    try {
        const result = await apiRequest(
            "/api/authority/claim-history",
            "GET",
            null,
            true
        );

        container.innerHTML = "";

        if (!result.history || result.history.length === 0) {
            container.innerHTML = "<p>No claim history available.</p>";
            return;
        }

        result.history.forEach(record => {
            const card = document.createElement("div");
            card.className = "dashboard-card";

            card.innerHTML = `
                <h4>Claim #${record.claim_id}</h4>
                <p>Found Item ID: #${record.found_id}</p>
                <p>Decision: ${record.decision.toUpperCase()}</p>
                <p>Remarks: ${record.remarks || "No remarks"}</p>
                <p>Decided By: ${record.decided_by}</p>
                <p>Decision Date: ${record.decided_at || "-"}</p>
            `;

            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = "<p>Unable to load claim history.</p>";
        console.error("Claim history error:", error);
    }
}

async function loadPossibleMatches() {
    const container = document.getElementById("possible-matches-container");

    container.innerHTML = "<p>Loading possible AI matches...</p>";

    try {
        const result = await apiRequest(
            "/api/authority/possible-matches",
            "GET",
            null,
            true
        );

        container.innerHTML = "";

        if (!result.matches || result.matches.length === 0) {
            container.innerHTML = "<p>No possible AI matches found.</p>";
            return;
        }

        result.matches.forEach(match => {
            const card = document.createElement("div");
            card.className = "dashboard-card";

            const heading = document.createElement("h4");
            heading.textContent = `AI Match #${match.match_id}`;

            const details = [
                `Lost Item: ${match.lost_title}`,
                `Found Item: ${match.found_title}`,
                `Lost Category: ${match.lost_category}`,
                `Found Category: ${match.found_category}`,
                `Lost Location: ${match.lost_location}`,
                `Found Location: ${match.found_location}`,
                `Status: ${match.match_status}`,
                `Created At: ${match.created_at || "-"}`
            ];

            card.appendChild(heading);

            details.forEach(detail => {
                const paragraph = document.createElement("p");
                paragraph.textContent = detail;
                card.appendChild(paragraph);
            });
            const scoreSection = document.createElement("div");
            scoreSection.className = "ai-score-section";
            const scoreHeading = document.createElement("h3");
            scoreHeading.textContent = `AI Match Score: ${match.match_score}%`;
            const progressTrack = document.createElement("div");
            progressTrack.className = "ai-progress-track";
            const progressBar = document.createElement("div");
            progressBar.className = "ai-progress-bar";
            progressBar.style.width = `${Math.min(100, Math.max(0, Number(match.match_score)))}%`;
            progressTrack.appendChild(progressBar);
            scoreSection.appendChild(scoreHeading);
            scoreSection.appendChild(progressTrack);
            card.appendChild(scoreSection);


            const note = document.createElement("p");
            note.textContent = "Possible match — authority verification required.";
            card.appendChild(note);

            container.appendChild(card);
        });

    } catch (error) {
        container.innerHTML = "<p>Unable to load possible AI matches.</p>";
        console.error("Possible AI matches error:", error);
    }
}

async function decideClaim(claimId, decision) {
    const remarks = prompt("Enter remarks for this decision:");

    if (remarks === null) {
        return;
    }

    if (!remarks.trim()) {
        alert("Please enter remarks.");
        return;
    }

    try {
        const result = await apiRequest(
            "/api/committee-decision",
            "POST",
            {
                claim_id: claimId,
                decision: decision,
                remarks: remarks
            },
            true
        );

        if (result.status === "error") {
            throw new Error(result.message);
        }

        alert(result.message || "Decision submitted successfully.");

        loadPendingClaims();

    } catch (error) {
        alert("Error: " + error.message);
    }
}


// UPDATE NAVBAR AND ACCOUNT SIDEBAR
function updateAuthUI(user) {
    document.querySelector(".login-btn").style.display = "none";
    document.querySelector(".register-btn").style.display = "none";

    const accountBtn = document.getElementById("account-btn");
    accountBtn.style.display = "flex";

    document.getElementById("nav-user-name").textContent =
        user.name || "My Account";

    document.getElementById("sidebar-user-name").textContent =
        user.name || "My Account";

    document.getElementById("sidebar-user-email").textContent =
        user.email || "";

    const role = user.role ||
        localStorage.getItem("user_role") ||
        "student";

    document.getElementById("sidebar-user-role").textContent =
        "Role: " + role.charAt(0).toUpperCase() + role.slice(1);

        const authorityLink = document.getElementById("authority-dashboard-link");
        if (authorityLink) {
            authorityLink.style.display =
            user.role === "authority" ? "flex" : "none";
        }
    }

// LOGIN
function openLogin() {
    createModal("Student Login", [
        { name: "email", label: "Email", type: "email" },
        { name: "password", label: "Password", type: "password" }
    ], "Login", async (data) => {
        const result = await apiRequest("/api/login", "POST", data);

        token = result.access_token;
        localStorage.setItem("access_token", token);
        localStorage.setItem("user_name", result.name);
        localStorage.setItem("user_role", result.role);

        showMessage("Login successful!");
        await loadDashboard();
    });
}

// REGISTER

function openRegister() {
    createModal("Account Registration", [
        {
            name: "name",
            label: "Full Name"
        },
        {
            name: "email",
            label: "Email",
            type: "email"
        },
        {
            name: "password",
            label: "Password",
            type: "password"
        },
        {
            name: "role",
            label: "Account Type",
            type: "select",
            options: [
                { value: "student", label: "Student" },
                { value: "authority", label: "Authority" }
            ]
        },
        {
            name: "authority_code",
            label: "Authority Registration Code",
            type: "password",
            showIf: {
                field: "role",
                value: "authority"
            }
        }
    ], "Register", async (data) => {

        const result = await apiRequest(
            "/api/register",
            "POST",
            data
        );

        if (result.status === "error") {
            throw new Error(result.message);
        }

        showMessage(result.message);
    });
}


// REPORT LOST ITEM
function openLostForm() {
    createModal("Report Lost Item", [
        { name: "title", label: "Item Name" },
        { name: "description", label: "Description", type: "textarea" },
        { name: "category", label: "Category" },
        { name: "location", label: "Last Seen Location" },
        { name: "lost_date", label: "Date and Time", type: "datetime-local" }
    ], "Submit Lost Report", async (data) => {
        const result = await apiRequest("/api/lost", "POST", data, true);
        showMessage(result.message);
    });
}

// REPORT FOUND ITEM
function openFoundForm() {
    createModal("Report Found Item", [
        { name: "title", label: "Item Name" },
        { name: "description", label: "Description", type: "textarea" },
        { name: "category", label: "Category" },
        { name: "location", label: "Found Location" },
        { name: "found_date", label: "Date and Time", type: "datetime-local" },
        { name: "verification_image", label: "Upload Verification Photo", type: "file" }
    ], "Submit Found Report", async (data, formData) => {
        const result = await apiFormRequest("/api/found", formData, true);
        showMessage(result.message);
    });
}

// CREATE REUSE LISTING
function openReuseForm() {
    createModal("Create Reuse Listing", [
        { name: "title", label: "Item Name" },
        { name: "description", label: "Description", type: "textarea" },
        { name: "category", label: "Category" },
        { name: "price", label: "Price (Enter 0 for Free)", type: "number" },
        { name: "condition_status", label: "Condition (Good / New / Used)" },
        { name: "image", label: "Select Item Photo (Optional)", type: "file", required: false }
    ], "Create Listing", async (data, formData) => {
        const result = await apiFormRequest("/api/reuse", formData, true);
        showMessage(result.message);
    });
}

// LOGOUT
function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_role");

    token = null;
    currentUserId = null;

    // Show Login and Register buttons
    document.querySelector(".login-btn").style.display = "inline-block";
    document.querySelector(".register-btn").style.display = "inline-block";

    // Hide account button
    document.getElementById("account-btn").style.display = "none";

    // Close sidebar
    closeAccountSidebar();

    // Hide dashboard
    document.getElementById("dashboard").style.display = "none";

    // Refresh marketplace
    loadReuseListings();

    showMessage("Logged out successfully.");
}

// BUTTON CONNECTIONS
document.querySelector(".login-btn")?.addEventListener("click", openLogin);

document.querySelector(".register-btn")?.addEventListener("click", openRegister);

document.querySelectorAll(".hero-buttons button")[0]
    ?.addEventListener("click", openLostForm);

document.querySelectorAll(".hero-buttons button")[1]
    ?.addEventListener("click", openFoundForm);

document.querySelector(".action-section .primary-btn")
    ?.addEventListener("click", openLostForm);

document.querySelector(".reuse-section .primary-btn")
    ?.addEventListener("click", openReuseForm);

console.log("Khoya-Paaya frontend connected successfully!");

// LOAD REUSE MARKETPLACE
async function loadReuseListings() {
    const container = document.getElementById("reuse-listings");

    if (!container) return;

    try {
        const result = await apiRequest(
            "/api/reuse",
            "GET",
            null,
            false
        );

        container.innerHTML = "";

        if (!result.listings || result.listings.length === 0) {
            container.textContent = "No reuse items available yet.";
            return;
        }

        result.listings.forEach(listing => {
            const card = document.createElement("div");
            card.className = "reuse-card";

            // Item image
            const image = document.createElement("img");
            image.className = "reuse-image";
            image.alt = listing.title;

            if (listing.image_available) {
                image.src = `${API}/api/reuse/${listing.listing_id}/image`;
            } else {
                image.src = "https://placehold.co/400x250?text=No+Image";
            }

            // Item details
            const details = document.createElement("div");
            details.className = "reuse-details";

            const title = document.createElement("h3");
            title.textContent = listing.title;

            const description = document.createElement("p");
            description.textContent = listing.description || "No description";

            const category = document.createElement("p");
            category.textContent = "Category: " + listing.category;

            const condition = document.createElement("p");
            condition.textContent = "Condition: " + listing.condition_status;

            const price = document.createElement("h3");
            price.textContent = listing.price === 0
                ? "FREE"
                : "₹" + listing.price;

            details.append(
                title,
                description,
                category,
                condition,
                price
            );
            
            // Contact Seller button
            const contactButton = document.createElement("button");
            contactButton.textContent = "Contact Seller";
            contactButton.className = "contact-seller-btn";
            contactButton.onclick = async () => {
                try {
                    const result = await apiRequest(
                        `/api/reuse/${listing.listing_id}/seller`,
                        "GET",
                        null,
                        true
                    );
                    const seller = result.seller;
                    alert(
                        "Seller Details\n\n" +
                        "Name: " + seller.name + "\n" +
                        "Email: " + seller.email
                    );
                } catch (error) {
                    showMessage(error.message);
                }
            };

            if (Number(listing.user_id) === Number(currentUserId)) {
    const deleteButton = document.createElement("button");

    deleteButton.textContent = "Delete Listing";
    deleteButton.className = "delete-listing-btn";

    deleteButton.onclick = async () => {
        const confirmDelete = confirm(
            "Are you sure you want to delete this listing?"
        );

        if (!confirmDelete) return;

        try {
            const result = await apiRequest(
                `/api/reuse/${listing.listing_id}`,
                "DELETE",
                null,
                true
            );

            showMessage(result.message);
            loadReuseListings();

        } catch (error) {
            showMessage(error.message);
        }
    };

    card.appendChild(deleteButton);
}
            card.append(image, details, contactButton);
            container.appendChild(card);
        });

    } catch (error) {
        console.error("Reuse marketplace error:", error);
        container.textContent = "Unable to load reuse listings.";
    }
}

async function loadFoundItems() {
    const container = document.getElementById("found-items-container");

    try {
        const result = await apiRequest("/api/found", "GET");

        container.innerHTML = "";

        if (!result.found_items || result.found_items.length === 0) {
            container.textContent = "No found items reported yet.";
            return;
        }

        result.found_items.forEach(item => {
            const card = document.createElement("div");
            card.className = "reuse-card";

            const details = document.createElement("div");
            details.className = "reuse-details";

            const title = document.createElement("h3");
            title.textContent = "Found Item";

            const category = document.createElement("p");
            category.textContent = "Category: " + item.category;

            const date = document.createElement("p");
            date.textContent = "Found Date: " + item.found_date;

            const id = document.createElement("p");
            id.textContent = "Reference ID: #" + item.found_id;

            details.append(title, category, date, id);
            details.append(title, category, date, id);
            // This might be mine button
            const claimButton = document.createElement("button");
            claimButton.textContent = "This might be mine";
            claimButton.className = "contact-seller-btn";
            claimButton.onclick = async () => {
                try {
                    const result = await apiRequest(
                        "/api/claim",
                        "POST",
                        { found_id: item.found_id },
                        true
                    );
                    showMessage(result.message);
                    claimButton.disabled = true;
                    claimButton.textContent = "Claim Submitted";
                } catch (error) {
                    showMessage(error.message);
                }
            };
            card.append(details, claimButton);
            container.appendChild(card);
        });
    } catch (error) {
        container.textContent = "Unable to load found items.";
        console.error("Found items error:", error);
    }
}

// Load listings when page opens
document.addEventListener("DOMContentLoaded", loadReuseListings);



// Automatically load dashboard if user is already logged in
if (token) {
    loadDashboard();
}

// ACCOUNT SIDEBAR OPEN/CLOSE

const accountBtn = document.getElementById("account-btn");
const accountSidebar = document.getElementById("account-sidebar");
const sidebarOverlay = document.getElementById("sidebar-overlay");
const closeSidebarBtn = document.getElementById("close-sidebar");

function openAccountSidebar() {
    accountSidebar.classList.add("active");
    sidebarOverlay.classList.add("active");
}

function closeAccountSidebar() {
    accountSidebar.classList.remove("active");
    sidebarOverlay.classList.remove("active");
}

accountBtn.addEventListener("click", openAccountSidebar);
closeSidebarBtn.addEventListener("click", closeAccountSidebar);
sidebarOverlay.addEventListener("click", closeAccountSidebar);

// Close sidebar after selecting a menu link
document.querySelectorAll(".sidebar-link").forEach(link => {
    link.addEventListener("click", closeAccountSidebar);
});


async function loadMyListings() {
    const container = document.getElementById("my-listings-container");

    if (!container) return;

    if (!token || !currentUserId) {
        container.textContent = "Please login to view your listings.";
        return;
    }

    try {
        const result = await apiRequest("/api/reuse", "GET", null, false);

        const myListings = result.listings.filter(
            listing => Number(listing.user_id) === Number(currentUserId)
        );

        container.innerHTML = "";

        if (myListings.length === 0) {
            container.textContent = "You have not created any listings yet.";
            return;
        }

        myListings.forEach(listing => {
            const card = document.createElement("div");
            card.className = "reuse-card";

            const image = document.createElement("img");
            image.className = "reuse-image";
            image.alt = listing.title;

            image.src = listing.image_available
                ? `${API}/api/reuse/${listing.listing_id}/image`
                : "https://placehold.co/400x250?text=No+Image";

            const details = document.createElement("div");
            details.className = "reuse-details";

            const title = document.createElement("h3");
            title.textContent = listing.title;

            const description = document.createElement("p");
            description.textContent = listing.description || "No description";

            const price = document.createElement("h3");
            price.textContent = listing.price === 0
                ? "FREE"
                : "₹" + listing.price;

            details.append(title, description, price);
            card.append(image, details);

            container.appendChild(card);
        });

    } catch (error) {
        console.error("My Listings error:", error);
        container.textContent = "Unable to load your listings.";
    }
}

// LOAD MY LISTINGS WHEN SIDEBAR LINK IS CLICKED

document.querySelector('a[href="#my-listings"]')
    .addEventListener("click", () => {
        loadMyListings();
    });

    // ACCOUNT INFORMATION
document.getElementById("account-info-btn")
    .addEventListener("click", async () => {
        if (!token) {
            showMessage("Please login first.");
            return;
        }

        try {
            const result = await apiRequest(
                "/api/me", "GET", null, true
            );

            const user = result.user;

            alert(
                "ACCOUNT INFORMATION\n\n" +
                "Name: " + user.name + "\n" +
                "Email: " + user.email + "\n" +
                "User ID: " + user.user_id + "\n" +
                "Role: " + user.role
            );

        } catch (error) {
            showMessage(error.message);
        }
    });

    // DARK MODE

const themeButton = document.getElementById("theme-toggle-btn");

// Apply saved theme
if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark-mode");
    themeButton.textContent = "Enable Light Mode";
}

// Toggle theme
themeButton.addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");

    const isDark = document.body.classList.contains("dark-mode");

    localStorage.setItem("theme", isDark ? "dark" : "light");

    themeButton.textContent = isDark
        ? "Enable Light Mode"
        : "Enable Dark Mode";
});


// NOTIFICATION PREFERENCE

const notificationToggle = document.getElementById("notification-toggle");

// Load saved preference
const savedNotification = localStorage.getItem("notifications");

if (savedNotification !== null) {
    notificationToggle.checked = savedNotification === "enabled";
}

// Save preference when changed
notificationToggle.addEventListener("change", () => {
    localStorage.setItem(
        "notifications",
        notificationToggle.checked ? "enabled" : "disabled"
    );

    showMessage(
        notificationToggle.checked
            ? "Notifications enabled."
            : "Notifications disabled."
    );
});


// CHANGE PASSWORD

document.getElementById("change-password-btn")
    .addEventListener("click", () => {

        createModal("Change Password", [
            {
                name: "old_password",
                label: "Current Password",
                type: "password"
            },
            {
                name: "new_password",
                label: "New Password",
                type: "password"
            },
            {
                name: "confirm_password",
                label: "Confirm New Password",
                type: "password"
            }
        ], "Update Password", async (data) => {

            if (data.new_password !== data.confirm_password) {
                showMessage("New passwords do not match.");
                return;
            }

            if (data.new_password.length < 8) {
                showMessage("Password must be at least 8 characters.");
                return;
            }

            try {
                const result = await apiRequest(
                    "/api/change-password",
                    "POST",
                    {
                        old_password: data.old_password,
                        new_password: data.new_password
                    },
                    true
                );

                showMessage(result.message);

            } catch (error) {
                showMessage(error.message);
            }
        });
    });

    loadFoundItems();