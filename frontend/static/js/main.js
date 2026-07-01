function logout() {
    localStorage.removeItem("access_token");
    window.location.href = "/";
}

// Protect pages that require login
(function () {
    const token = localStorage.getItem("access_token");
    const protectedPaths = ["/dashboard", "/daily", "/monthly", "/lab"];

    if (!token && protectedPaths.includes(window.location.pathname)) {
        window.location.href = "/";
    }
})();
