/* ============================================================
   GLOBAL USER HANDLING (used by ALL pages)
   Ensures user is always saved consistently in localStorage.
============================================================ */

/* Save user object */
function saveUser(user){
    localStorage.setItem("zoma_user", JSON.stringify(user));
}

/* Load user object */
function loadUser(){
    return JSON.parse(localStorage.getItem("zoma_user") || "null");
}

/* Load logged in email */
function getUserEmail(){
    const u = loadUser();
    return u ? u.email : null;
}

/* Ensure login before accessing protected pages */
function requireLogin(redirectPage){
    const u = loadUser();
    if(!u){
        window.location.href = "login.html?redirect=" + redirectPage;
    }
}

/* Save address */
function saveUserAddress(address){
    let u = loadUser() || {};
    u.address = address;
    saveUser(u);
}

/* Save location */
function saveLocation(lat, lon){
    let u = loadUser() || {};
    u.lat = lat;
    u.lon = lon;
    saveUser(u);
}

/* Admin settings */
function getAdminSettings(){
    return JSON.parse(localStorage.getItem("admin_settings") || JSON.stringify({
        gst: 5,
        platformFee: 10,
        universalCoupon: null,
        deliveryFee: 0,
        packagingFee: 0
    }));
}

function saveAdminSettings(settings){
    localStorage.setItem("admin_settings", JSON.stringify(settings));
}

/* Vendor charges */
function getVendorCharges(email){
    return JSON.parse(localStorage.getItem("vendor_charges_" + email) || JSON.stringify({
        deliveryFee: 0,
        packagingFee: 0,
        offer: 0
    }));
}

function saveVendorCharges(email, charges){
    localStorage.setItem("vendor_charges_" + email, JSON.stringify(charges));
}
