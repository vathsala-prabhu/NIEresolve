const { useState, useEffect, useRef } = React;

// API Helper
const API = {
    async request(url, options = {}) {
        const token = localStorage.getItem("nieresolve_token");
        const headers = {
            ...(options.headers || {}),
        };
        if (token && !headers["Authorization"]) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
            headers["Content-Type"] = "application/json";
        }

        try {
            const res = await fetch(url, { ...options, headers });
            if (res.status === 401) {
                // Token expired
                localStorage.removeItem("nieresolve_token");
                localStorage.removeItem("nieresolve_user");
                window.location.reload();
                throw new Error("Session expired. Please log in again.");
            }
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.detail || data.message || "An error occurred");
            }
            return data;
        } catch (err) {
            console.error(`[API Error] ${url}:`, err);
            throw err;
        }
    }
};

// Priority Badge Component
function PriorityBadge({ priority, size = "sm" }) {
    const p = priority || "Medium";
    let bg = "bg-blue-100 text-blue-800 border-blue-200";
    if (p === "Critical") bg = "bg-red-100 text-red-800 border-red-300 font-semibold";
    else if (p === "High") bg = "bg-amber-100 text-amber-800 border-amber-300";
    else if (p === "Medium") bg = "bg-yellow-50 text-yellow-800 border-yellow-200";
    else if (p === "Low") bg = "bg-slate-100 text-slate-700 border-slate-200";

    const textClass = size === "lg" ? "text-sm px-3 py-1" : "text-xs px-2.5 py-0.5";
    return (
        <span className={`inline-flex items-center gap-1 rounded-full border ${textClass} ${bg}`}>
            {p === "Critical" && <span className="w-1.5 h-1.5 rounded-full bg-red-600 animate-ping"></span>}
            {p}
        </span>
    );
}

// Status Badge Component
function StatusBadge({ status }) {
    const s = status || "submitted";
    const labels = {
        submitted: { label: "Submitted", color: "bg-blue-50 text-blue-700 border-blue-200" },
        verified: { label: "Verified", color: "bg-indigo-50 text-indigo-700 border-indigo-200" },
        assigned: { label: "Assigned", color: "bg-purple-50 text-purple-700 border-purple-200" },
        under_investigation: { label: "Under Investigation", color: "bg-amber-50 text-amber-700 border-amber-200" },
        action_taken: { label: "Action Taken", color: "bg-teal-50 text-teal-700 border-teal-200" },
        resolved: { label: "Resolved", color: "bg-emerald-50 text-emerald-700 border-emerald-200 font-medium" },
        closed: { label: "Closed", color: "bg-slate-100 text-slate-700 border-slate-300" },
        reopened: { label: "Reopened", color: "bg-rose-50 text-rose-700 border-rose-200" },
    };
    const conf = labels[s] || { label: s, color: "bg-slate-100 text-slate-700 border-slate-200" };
    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs border ${conf.color}`}>
            {conf.label}
        </span>
    );
}

// Tier Badge Component
function TierBadge({ tier }) {
    const t = tier || "tier_1";
    const labels = {
        tier_1: { label: "Tier 1: Department", color: "bg-sky-50 text-sky-800 border-sky-200" },
        tier_2: { label: "Tier 2: Grievance Cell", color: "bg-purple-50 text-purple-800 border-purple-200 font-medium" },
        tier_3: { label: "Tier 3: Principal", color: "bg-rose-50 text-rose-800 border-rose-200 font-semibold" },
    };
    const conf = labels[t] || { label: t, color: "bg-slate-100 text-slate-700 border-slate-200" };
    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border ${conf.color}`}>
            {conf.label}
        </span>
    );
}

// Deadline Countdown Pill
function DeadlinePill({ deadline, daysPending, isPaused }) {
    if (isPaused) {
        return (
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono border border-slate-200">
                Timer Paused
            </span>
        );
    }
    if (!deadline) {
        return <span className="text-xs text-slate-500 font-mono">{daysPending}d pending</span>;
    }
    const diffDays = Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24));
    let color = "bg-emerald-50 text-emerald-700 border-emerald-200";
    let text = `${diffDays} days left`;
    if (diffDays < 0) {
        color = "bg-red-50 text-red-700 border-red-200 font-semibold";
        text = `Overdue by ${Math.abs(diffDays)}d`;
    } else if (diffDays <= 3) {
        color = "bg-amber-50 text-amber-800 border-amber-300 font-medium";
        text = `${diffDays}d left (Warning)`;
    }
    return (
        <span className={`text-xs px-2 py-0.5 rounded font-mono border ${color}`}>
            {text}
        </span>
    );
}

// Toast Notification System
function ToastContainer({ toasts, removeToast }) {
    return (
        <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
            {toasts.map((t) => (
                <div
                    key={t.id}
                    className={`pointer-events-auto p-4 rounded-lg shadow-lg border text-sm flex items-start gap-3 transition-all transform translate-y-0 ${
                        t.type === "error"
                            ? "bg-red-50 text-red-800 border-red-200"
                            : t.type === "warning"
                            ? "bg-amber-50 text-amber-800 border-amber-200"
                            : "bg-emerald-50 text-emerald-800 border-emerald-200"
                    }`}
                >
                    <div className="flex-1">
                        {t.title && <p className="font-semibold">{t.title}</p>}
                        <p>{t.message}</p>
                    </div>
                    <button
                        onClick={() => removeToast(t.id)}
                        className="text-slate-400 hover:text-slate-600"
                    >
                        &times;
                    </button>
                </div>
            ))}
        </div>
    );
}

// MAIN APPLICATION ROOT
function App() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [view, setView] = useState("dashboard"); // dashboard, submit, tracking, scholarships, escalations, analytics, admin
    const [selectedComplaintId, setSelectedComplaintId] = useState(null);
    const [toasts, setToasts] = useState([]);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [unreadNotifCount, setUnreadNotifCount] = useState(0);
    const [isNotifOpen, setIsNotifOpen] = useState(false);

    // Add toast
    const addToast = (message, type = "success", title = null) => {
        const id = Date.now() + Math.random();
        setToasts((prev) => [...prev, { id, message, type, title }]);
        setTimeout(() => removeToast(id), 5000);
    };

    const removeToast = (id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    // Check user profile on mount
    useEffect(() => {
        const savedToken = localStorage.getItem("nieresolve_token");
        if (savedToken) {
            API.request("/api/auth/me")
                .then((userData) => {
                    setUser(userData);
                    loadNotifications();
                })
                .catch(() => {
                    localStorage.removeItem("nieresolve_token");
                    localStorage.removeItem("nieresolve_user");
                })
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    // Load notifications periodically
    const loadNotifications = () => {
        API.request("/api/notifications")
            .then((data) => {
                setNotifications(data.notifications || []);
                setUnreadNotifCount(data.unread_count || 0);
            })
            .catch(() => {});
    };

    const handleLogout = () => {
        localStorage.removeItem("nieresolve_token");
        localStorage.removeItem("nieresolve_user");
        setUser(null);
        setView("dashboard");
        addToast("Logged out successfully.", "info");
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-nie-navy border-t-nie-gold rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-slate-600 font-medium">Loading NIEresolve Platform...</p>
                </div>
            </div>
        );
    }

    if (!user) {
        return (
            <LoginPage
                onLogin={(userData, token) => {
                    localStorage.setItem("nieresolve_token", token);
                    setUser(userData);
                    addToast(`Welcome back, ${userData.full_name}!`, "success");
                    loadNotifications();
                }}
                addToast={addToast}
            />
        );
    }

    return (
        <div className="min-h-screen flex flex-col bg-slate-50">
            {/* Top Institutional Header */}
            <header className="institutional-banner text-white px-4 py-2.5 shadow-sm sticky top-0 z-30">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-white/10 border border-nie-gold/40 flex items-center justify-center font-bold text-nie-gold text-lg">
                            N
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="font-bold text-lg tracking-tight">NIEresolve</span>
                                <span className="text-[10px] bg-nie-gold text-white font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider">
                                    Official
                                </span>
                            </div>
                            <p className="text-xs text-slate-300 hidden sm:block">
                                The National Institute of Engineering, Mysuru &bull; Every Concern Deserves a Response
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        {/* Notification Bell */}
                        <div className="relative">
                            <button
                                onClick={() => setIsNotifOpen(!isNotifOpen)}
                                className="relative p-2 rounded-lg hover:bg-white/10 transition text-slate-200 hover:text-white"
                                title="Notifications"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                </svg>
                                {unreadNotifCount > 0 && (
                                    <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-nie-gold text-white text-[10px] flex items-center justify-center font-bold">
                                        {unreadNotifCount}
                                    </span>
                                )}
                            </button>

                            {isNotifOpen && (
                                <NotificationDropdown
                                    notifications={notifications}
                                    onClose={() => setIsNotifOpen(false)}
                                    onRefresh={loadNotifications}
                                    addToast={addToast}
                                />
                            )}
                        </div>

                        {/* AI Chatbot Launcher Button */}
                        <button
                            onClick={() => setIsChatOpen(!isChatOpen)}
                            className="flex items-center gap-1.5 bg-nie-gold hover:bg-nie-goldlight text-white text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm transition"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                            </svg>
                            <span className="hidden sm:inline">AI Assistant</span>
                        </button>

                        {/* User Profile & Role Info */}
                        <div className="flex items-center gap-2 pl-2 border-l border-white/20">
                            <div className="text-right hidden md:block">
                                <div className="text-xs font-semibold text-white">{user.full_name}</div>
                                <div className="text-[10px] text-slate-300 font-mono capitalize">
                                    {user.role.replace("_", " ")} {user.identifier ? `(${user.identifier})` : ""}
                                </div>
                            </div>
                            <button
                                onClick={handleLogout}
                                className="p-1.5 rounded-lg hover:bg-white/10 text-slate-300 hover:text-white text-xs flex items-center gap-1"
                                title="Sign Out"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Navigation Tabs */}
            <nav className="bg-white border-b border-slate-200 px-4">
                <div className="max-w-7xl mx-auto flex items-center space-x-1 overflow-x-auto py-1">
                    <button
                        onClick={() => { setView("dashboard"); setSelectedComplaintId(null); }}
                        className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${
                            view === "dashboard" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"
                        }`}
                    >
                        Dashboard
                    </button>

                    {(user.role === "student" || user.role === "faculty") && (
                        <button
                            onClick={() => { setView("submit"); setSelectedComplaintId(null); }}
                            className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap flex items-center gap-1 ${
                                view === "submit" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"
                            }`}
                        >
                            <span>+ Raise Grievance</span>
                        </button>
                    )}

                    {user.role === "student" && (
                        <button
                            onClick={() => { setView("scholarships"); setSelectedComplaintId(null); }}
                            className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap flex items-center gap-1 ${
                                view === "scholarships" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"
                            }`}
                        >
                            <span>Scholarships & Aid</span>
                            <span className="bg-nie-gold text-white text-[9px] px-1.5 py-0.2 rounded-full">New</span>
                        </button>
                    )}

                    {["dept_officer", "grievance_cell", "principal", "super_admin"].includes(user.role) && (
                        <>
                            <button
                                onClick={() => { setView("escalations"); setSelectedComplaintId(null); }}
                                className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${
                                    view === "escalations" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"
                                }`}
                            >
                                15-Day Escalation Matrix
                            </button>
                            <button
                                onClick={() => { setView("analytics"); setSelectedComplaintId(null); }}
                                className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${
                                    view === "analytics" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"
                                }`}
                            >
                                Institutional Analytics
                            </button>
                        </>
                    )}

                    {user.role === "super_admin" && (
                        <button
                            onClick={() => { setView("admin"); setSelectedComplaintId(null); }}
                            className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${
                                view === "admin" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"
                            }`}
                        >
                            System Administration
                        </button>
                    )}
                </div>
            </nav>

            {/* Main Content Area */}
            <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
                {selectedComplaintId ? (
                    <ComplaintDetailPage
                        complaintId={selectedComplaintId}
                        currentUser={user}
                        onBack={() => setSelectedComplaintId(null)}
                        addToast={addToast}
                    />
                ) : view === "dashboard" ? (
                    <RoleDashboard
                        user={user}
                        onSelectComplaint={(id) => setSelectedComplaintId(id)}
                        onNewComplaint={() => setView("submit")}
                        addToast={addToast}
                    />
                ) : view === "submit" ? (
                    <SubmitComplaintPage
                        currentUser={user}
                        onSuccess={(complaintId) => {
                            setSelectedComplaintId(complaintId);
                            setView("dashboard");
                        }}
                        onCancel={() => setView("dashboard")}
                        addToast={addToast}
                    />
                ) : view === "scholarships" ? (
                    <ScholarshipPortal currentUser={user} addToast={addToast} />
                ) : view === "escalations" ? (
                    <EscalationMatrixDashboard
                        currentUser={user}
                        onSelectComplaint={(id) => setSelectedComplaintId(id)}
                        addToast={addToast}
                    />
                ) : view === "analytics" ? (
                    <AnalyticsView currentUser={user} addToast={addToast} />
                ) : view === "admin" ? (
                    <AdminPanel currentUser={user} addToast={addToast} />
                ) : null}
            </main>

            {/* Floating AI Chatbot Drawer */}
            <ChatbotDrawer
                isOpen={isChatOpen}
                onClose={() => setIsChatOpen(false)}
                currentUser={user}
            />

            {/* Toast Notifications Container */}
            <ToastContainer toasts={toasts} removeToast={removeToast} />

            {/* Footer */}
            <footer className="bg-white border-t border-slate-200 py-4 px-6 text-center text-xs text-slate-500">
                <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
                    <div>
                        <span className="font-semibold text-nie-navy">NIEresolve</span> &copy; 2026 The National Institute of Engineering, Mysuru. All rights reserved.
                    </div>
                    <div className="flex gap-4">
                        <span>Autonomous Institution Affiliated to VTU</span>
                        <span>Tier 1 &bull; Tier 2 &bull; Tier 3 Redressal</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}

// ----------------------------------------------------------------------
// LOGIN PAGE COMPONENT (Student, Faculty, Administrative with Demo Pills)
// ----------------------------------------------------------------------
function LoginPage({ onLogin, addToast }) {
    const [loginType, setLoginType] = useState("student"); // student, faculty, admin
    const [usn, setUsn] = useState("");
    const [dob, setDob] = useState("");
    const [facultyId, setFacultyId] = useState("");
    const [facultyDob, setFacultyDob] = useState("");
    const [adminUsername, setAdminUsername] = useState("");
    const [adminPassword, setAdminPassword] = useState("");
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            let endpoint = "";
            let payload = {};
            if (loginType === "student") {
                endpoint = "/api/auth/student-login";
                payload = { usn, dob };
            } else if (loginType === "faculty") {
                endpoint = "/api/auth/faculty-login";
                payload = { faculty_id: facultyId, dob: facultyDob };
            } else {
                endpoint = "/api/auth/admin-login";
                payload = { username_or_email: adminUsername, password: adminPassword };
            }

            const data = await API.request(endpoint, {
                method: "POST",
                body: JSON.stringify(payload),
            });

            onLogin(
                {
                    id: data.user_id,
                    full_name: data.full_name,
                    email: data.email,
                    role: data.role,
                    identifier: data.identifier,
                    department_name: data.department_name,
                },
                data.access_token
            );
        } catch (err) {
            addToast(err.message, "error");
        } finally {
            setSubmitting(false);
        }
    };

    // Quick fill helper for demonstration testing
    const fillDemo = (type, ident, secret) => {
        setLoginType(type);
        if (type === "student") {
            setUsn(ident);
            setDob(secret);
        } else if (type === "faculty") {
            setFacultyId(ident);
            setFacultyDob(secret);
        } else {
            setAdminUsername(ident);
            setAdminPassword(secret);
        }
    };

    return (
        <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
                <div className="w-14 h-14 bg-nie-navy text-nie-gold rounded-xl flex items-center justify-center font-bold text-2xl mx-auto shadow-md border-2 border-nie-gold">
                    N
                </div>
                <h1 className="mt-3 text-2xl font-bold tracking-tight text-nie-navy">NIEresolve</h1>
                <p className="text-xs text-nie-gold font-semibold uppercase tracking-wider">Every Concern Deserves a Response.</p>
                <p className="text-xs text-slate-500 mt-1">The National Institute of Engineering (NIE), Mysuru</p>
            </div>

            <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
                <div className="bg-white py-8 px-4 shadow-xl sm:rounded-xl sm:px-10 border border-slate-200">
                    {/* Role Selector Tabs */}
                    <div className="flex border-b border-slate-200 mb-6">
                        <button
                            type="button"
                            onClick={() => setLoginType("student")}
                            className={`flex-1 py-2 text-xs font-semibold border-b-2 text-center transition ${
                                loginType === "student"
                                    ? "border-nie-navy text-nie-navy"
                                    : "border-transparent text-slate-500 hover:text-slate-700"
                            }`}
                        >
                            Student
                        </button>
                        <button
                            type="button"
                            onClick={() => setLoginType("faculty")}
                            className={`flex-1 py-2 text-xs font-semibold border-b-2 text-center transition ${
                                loginType === "faculty"
                                    ? "border-nie-navy text-nie-navy"
                                    : "border-transparent text-slate-500 hover:text-slate-700"
                            }`}
                        >
                            Faculty
                        </button>
                        <button
                            type="button"
                            onClick={() => setLoginType("admin")}
                            className={`flex-1 py-2 text-xs font-semibold border-b-2 text-center transition ${
                                loginType === "admin"
                                    ? "border-nie-navy text-nie-navy"
                                    : "border-transparent text-slate-500 hover:text-slate-700"
                            }`}
                        >
                            Officer / Admin
                        </button>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {loginType === "student" && (
                            <>
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700">University Seat Number (USN)</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. 4NI21CS045"
                                        value={usn}
                                        onChange={(e) => setUsn(e.target.value)}
                                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm uppercase placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700">Date of Birth (DOB)</label>
                                    <input
                                        type="date"
                                        required
                                        value={dob}
                                        onChange={(e) => setDob(e.target.value)}
                                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                    />
                                    <p className="text-[11px] text-slate-400 mt-1">Verified securely against institutional registrar records.</p>
                                </div>
                            </>
                        )}

                        {loginType === "faculty" && (
                            <>
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700">Faculty Employee ID</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. NIE-FAC-102"
                                        value={facultyId}
                                        onChange={(e) => setFacultyId(e.target.value)}
                                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm uppercase placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700">Date of Birth (DOB)</label>
                                    <input
                                        type="date"
                                        required
                                        value={facultyDob}
                                        onChange={(e) => setFacultyDob(e.target.value)}
                                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                    />
                                </div>
                            </>
                        )}

                        {loginType === "admin" && (
                            <>
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700">Institutional Email or Username</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. officer.cse@nie.ac.in"
                                        value={adminUsername}
                                        onChange={(e) => setAdminUsername(e.target.value)}
                                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700">Password</label>
                                    <input
                                        type="password"
                                        required
                                        placeholder="••••••••"
                                        value={adminPassword}
                                        onChange={(e) => setAdminPassword(e.target.value)}
                                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                    />
                                </div>
                            </>
                        )}

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-nie-navy hover:bg-nie-navydark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-nie-navy transition disabled:opacity-50"
                        >
                            {submitting ? "Authenticating..." : `Sign In as ${loginType === "student" ? "Student" : loginType === "faculty" ? "Faculty" : "Authorized Officer"}`}
                        </button>
                    </form>

                    {/* Pre-configured Demo Accounts Helper */}
                    <div className="mt-6 pt-5 border-t border-slate-200">
                        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider text-center mb-2.5">
                            Quick Demo Sign-In Credentials
                        </p>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            <button
                                type="button"
                                onClick={() => fillDemo("student", "4NI21CS045", "2003-05-15")}
                                className="p-2 border border-slate-200 rounded-md hover:bg-slate-50 text-left transition"
                            >
                                <div className="font-semibold text-nie-navy">Student</div>
                                <div className="text-[10px] text-slate-500 font-mono">4NI21CS045</div>
                            </button>
                            <button
                                type="button"
                                onClick={() => fillDemo("faculty", "NIE-FAC-102", "1985-08-20")}
                                className="p-2 border border-slate-200 rounded-md hover:bg-slate-50 text-left transition"
                            >
                                <div className="font-semibold text-nie-navy">Faculty</div>
                                <div className="text-[10px] text-slate-500 font-mono">NIE-FAC-102</div>
                            </button>
                            <button
                                type="button"
                                onClick={() => fillDemo("admin", "officer.cse@nie.ac.in", "Officer@123")}
                                className="p-2 border border-slate-200 rounded-md hover:bg-slate-50 text-left transition"
                            >
                                <div className="font-semibold text-nie-navy">Tier 1: Dept Officer</div>
                                <div className="text-[10px] text-slate-500 font-mono">CSE Officer</div>
                            </button>
                            <button
                                type="button"
                                onClick={() => fillDemo("admin", "grievancecell@nie.ac.in", "Grievance@123")}
                                className="p-2 border border-slate-200 rounded-md hover:bg-slate-50 text-left transition"
                            >
                                <div className="font-semibold text-nie-navy">Tier 2: Grievance Cell</div>
                                <div className="text-[10px] text-slate-500 font-mono">Committee</div>
                            </button>
                            <button
                                type="button"
                                onClick={() => fillDemo("admin", "principal@nie.ac.in", "Principal@123")}
                                className="p-2 border border-slate-200 rounded-md hover:bg-slate-50 text-left transition"
                            >
                                <div className="font-semibold text-nie-navy">Tier 3: Principal</div>
                                <div className="text-[10px] text-slate-500 font-mono">Higher Authority</div>
                            </button>
                            <button
                                type="button"
                                onClick={() => fillDemo("admin", "admin@nie.ac.in", "Admin@123")}
                                className="p-2 border border-slate-200 rounded-md hover:bg-slate-50 text-left transition"
                            >
                                <div className="font-semibold text-nie-navy">Super Admin</div>
                                <div className="text-[10px] text-slate-500 font-mono">System Admin</div>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// ROLE-BASED DASHBOARD ROUTER
// ----------------------------------------------------------------------
function RoleDashboard({ user, onSelectComplaint, onNewComplaint, addToast }) {
    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filterCategory, setFilterCategory] = useState("");
    const [filterPriority, setFilterPriority] = useState("");
    const [filterStatus, setFilterStatus] = useState("");

    const loadComplaints = () => {
        setLoading(true);
        let url = "/api/complaints";
        const params = new URLSearchParams();
        if (filterCategory) params.append("category", filterCategory);
        if (filterPriority) params.append("priority", filterPriority);
        if (filterStatus) params.append("status", filterStatus);
        if (params.toString()) url += `?${params.toString()}`;

        API.request(url)
            .then((data) => setComplaints(data))
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadComplaints();
    }, [filterCategory, filterPriority, filterStatus]);

    // Compute Metrics
    const total = complaints.length;
    const pending = complaints.filter((c) => !["resolved", "closed"].includes(c.status)).length;
    const investigating = complaints.filter((c) => c.status === "under_investigation").length;
    const resolved = complaints.filter((c) => ["resolved", "closed"].includes(c.status)).length;
    const escalated = complaints.filter((c) => ["tier_2", "tier_3"].includes(c.current_tier)).length;

    return (
        <div className="space-y-6">
            {/* Header Banner with Welcome & Action */}
            <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-bold text-nie-navy">
                        {user.role === "student" && "Student Grievance Portal"}
                        {user.role === "faculty" && "Faculty Grievance Dashboard"}
                        {user.role === "dept_officer" && `Tier 1 Department Dashboard — ${user.department_name || "Department"}`}
                        {user.role === "grievance_cell" && "Tier 2 Institutional Grievance Redressal Cell"}
                        {user.role === "principal" && "Tier 3 Higher Authority / Principal Executive Dashboard"}
                        {user.role === "super_admin" && "Super Admin Central Operations"}
                    </h1>
                    <p className="text-xs text-slate-500 mt-0.5">
                        Logged in as <strong className="text-slate-700">{user.full_name}</strong> &bull; {user.email}
                    </p>
                </div>

                {(user.role === "student" || user.role === "faculty") && (
                    <button
                        onClick={onNewComplaint}
                        className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-sm transition flex items-center gap-1.5"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                        </svg>
                        <span>Submit New Grievance</span>
                    </button>
                )}
            </div>

            {/* Metrics Overview Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-slate-500 font-medium">Total Grievances</p>
                    <p className="text-2xl font-bold text-nie-navy mt-1">{total}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-amber-600 font-medium">Pending Review</p>
                    <p className="text-2xl font-bold text-amber-700 mt-1">{pending}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-blue-600 font-medium">Investigating</p>
                    <p className="text-2xl font-bold text-blue-700 mt-1">{investigating}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-emerald-600 font-medium">Resolved</p>
                    <p className="text-2xl font-bold text-emerald-700 mt-1">{resolved}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-purple-600 font-medium">Escalated (T2/T3)</p>
                    <p className="text-2xl font-bold text-purple-700 mt-1">{escalated}</p>
                </div>
            </div>

            {/* Filters Bar */}
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm flex flex-wrap gap-2 items-center text-xs">
                <span className="font-semibold text-slate-600">Filters:</span>
                <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="border border-slate-200 rounded px-2 py-1 text-slate-700 focus:outline-none"
                >
                    <option value="">All Statuses</option>
                    <option value="submitted">Submitted</option>
                    <option value="verified">Verified</option>
                    <option value="assigned">Assigned</option>
                    <option value="under_investigation">Under Investigation</option>
                    <option value="resolved">Resolved</option>
                </select>

                <select
                    value={filterPriority}
                    onChange={(e) => setFilterPriority(e.target.value)}
                    className="border border-slate-200 rounded px-2 py-1 text-slate-700 focus:outline-none"
                >
                    <option value="">All Priorities</option>
                    <option value="Critical">Critical</option>
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                </select>

                <button
                    onClick={() => { setFilterCategory(""); setFilterPriority(""); setFilterStatus(""); }}
                    className="text-nie-navy hover:underline text-xs ml-auto"
                >
                    Reset Filters
                </button>
            </div>

            {/* Complaints List Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
                    <h2 className="font-semibold text-sm text-slate-800">
                        {user.role === "student" ? "My Registered Grievances" : "Active Case Redressal Roster"}
                    </h2>
                    <span className="text-xs text-slate-500 font-mono">{complaints.length} Records</span>
                </div>

                {loading ? (
                    <div className="p-8 text-center text-slate-500 text-sm">
                        <div className="w-6 h-6 border-2 border-nie-navy border-t-nie-gold rounded-full animate-spin mx-auto mb-2"></div>
                        Fetching grievance records...
                    </div>
                ) : complaints.length === 0 ? (
                    <div className="p-12 text-center">
                        <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto text-slate-400 mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <p className="text-sm font-semibold text-slate-700">No complaints found</p>
                        <p className="text-xs text-slate-500 mt-1">There are no records matching your current filter criteria.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs text-slate-600">
                            <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                                <tr>
                                    <th className="px-4 py-3">Grievance ID</th>
                                    <th className="px-4 py-3">Title & Category</th>
                                    <th className="px-4 py-3">Department</th>
                                    <th className="px-4 py-3">Priority</th>
                                    <th className="px-4 py-3">Level / Authority</th>
                                    <th className="px-4 py-3">Status</th>
                                    <th className="px-4 py-3">Deadline / Pending</th>
                                    <th className="px-4 py-3 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {complaints.map((c) => (
                                    <tr key={c.id} className="hover:bg-slate-50/80 transition">
                                        <td className="px-4 py-3 font-mono font-bold text-nie-navy">
                                            {c.grievance_id}
                                            {c.is_duplicate && (
                                                <span className="block text-[9px] text-amber-600 font-sans font-normal">
                                                    Merged Duplicate
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 max-w-xs">
                                            <div className="font-semibold text-slate-900 truncate">{c.title}</div>
                                            <div className="text-[11px] text-slate-500">{c.category}</div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className="bg-slate-100 px-2 py-0.5 rounded text-[11px] font-mono">
                                                {c.department_code}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <PriorityBadge priority={c.final_priority} />
                                        </td>
                                        <td className="px-4 py-3">
                                            <TierBadge tier={c.current_tier} />
                                        </td>
                                        <td className="px-4 py-3">
                                            <StatusBadge status={c.status} />
                                        </td>
                                        <td className="px-4 py-3">
                                            <DeadlinePill
                                                deadline={c.expected_deadline}
                                                daysPending={c.days_pending}
                                            />
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <button
                                                onClick={() => onSelectComplaint(c.id)}
                                                className="bg-nie-navy/10 hover:bg-nie-navy text-nie-navy hover:text-white px-2.5 py-1 rounded font-semibold transition"
                                            >
                                                View &bull; Track
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// SUBMIT COMPLAINT PAGE (Form, Geo-tagging, Evidence Upload & Pre-check)
// ----------------------------------------------------------------------
function SubmitComplaintPage({ currentUser, onSuccess, onCancel, addToast }) {
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [category, setCategory] = useState("Infrastructure and Facilities");
    const [departmentId, setDepartmentId] = useState("");
    const [departments, setDepartments] = useState([]);
    const [locationName, setLocationName] = useState("");
    const [isAnonymous, setIsAnonymous] = useState(false);
    
    // Geolocation states
    const [lat, setLat] = useState(null);
    const [lon, setLon] = useState(null);
    const [accuracy, setAccuracy] = useState(null);
    const [geoLoading, setGeoLoading] = useState(false);
    const [geoDenied, setGeoDenied] = useState(false);
    const [exceptionReason, setExceptionReason] = useState("");

    // Evidence file
    const [file, setFile] = useState(null);
    const [isConfidentialEvidence, setIsConfidentialEvidence] = useState(false);

    // Duplicate detection draft warning
    const [duplicateMatches, setDuplicateMatches] = useState([]);
    const [checkingDuplicates, setCheckingDuplicates] = useState(false);

    const [submitting, setSubmitting] = useState(false);

    // Load departments
    useEffect(() => {
        API.request("/api/admin/departments")
            .then((data) => {
                setDepartments(data);
                if (data.length > 0) setDepartmentId(data[0].id);
            })
            .catch(() => {});
    }, []);

    // Geolocation capture
    const captureLocation = () => {
        if (!navigator.geolocation) {
            setGeoDenied(true);
            addToast("Geolocation is not supported by your browser.", "warning");
            return;
        }
        setGeoLoading(true);
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                setLat(pos.coords.latitude);
                setLon(pos.coords.longitude);
                setAccuracy(pos.coords.accuracy);
                setGeoDenied(false);
                setGeoLoading(false);
                addToast("Location coordinates captured successfully.", "success");
            },
            (err) => {
                console.warn(err);
                setGeoDenied(true);
                setGeoLoading(false);
                addToast("Location permission denied. Please state exception reason below.", "warning");
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    };

    // Pre-submission duplicate check debounce
    useEffect(() => {
        if (title.length < 5 || description.length < 15 || !departmentId) {
            setDuplicateMatches([]);
            return;
        }
        const timer = setTimeout(() => {
            setCheckingDuplicates(true);
            API.request("/api/complaints/check-duplicate", {
                method: "POST",
                body: JSON.stringify({
                    title,
                    description,
                    category,
                    department_id: parseInt(departmentId),
                }),
            })
                .then((matches) => setDuplicateMatches(matches))
                .catch(() => {})
                .finally(() => setCheckingDuplicates(false));
        }, 800);

        return () => clearTimeout(timer);
    }, [title, description, category, departmentId]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            // 1. Create Complaint
            const compPayload = {
                title,
                description,
                category,
                department_id: parseInt(departmentId),
                location_name: locationName || null,
                is_anonymous: isAnonymous,
                latitude: lat,
                longitude: lon,
                accuracy_meters: accuracy,
                exception_reason: geoDenied ? exceptionReason : null,
            };

            const compRes = await API.request("/api/complaints", {
                method: "POST",
                body: JSON.stringify(compPayload),
            });

            const complaintId = compRes.complaint_id;

            // 2. Upload Evidence if file chosen
            if (file && complaintId) {
                const formData = new FormData();
                formData.append("file", file);
                formData.append("is_confidential", isConfidentialEvidence);
                await API.request(`/api/evidence/upload/${complaintId}`, {
                    method: "POST",
                    body: formData,
                });
            }

            addToast(
                `Grievance registered with ID ${compRes.grievance_id}. Priority: ${compRes.final_priority}`,
                "success",
                "Submitted Successfully"
            );
            onSuccess(complaintId);
        } catch (err) {
            addToast(err.message, "error");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto bg-white p-6 sm:p-8 rounded-xl border border-slate-200 shadow-sm">
            <div className="border-b border-slate-200 pb-4 mb-6">
                <h1 className="text-lg font-bold text-nie-navy">Lodge a Formal Grievance</h1>
                <p className="text-xs text-slate-500 mt-1">
                    Every concern is logged with a unique institutional tracking ID, assessed by the ML Prioritizer, and monitored under the 15-day escalation matrix.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                    <label className="block text-xs font-semibold text-slate-700">Complaint Title *</label>
                    <input
                        type="text"
                        required
                        placeholder="e.g. Hazardous electrical short-circuit near North Block entrance"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nie-navy"
                    />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-slate-700">Category *</label>
                        <select
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-nie-navy"
                        >
                            <option value="Infrastructure and Facilities">Infrastructure & Facilities</option>
                            <option value="Hostel Issues">Hostel Issues</option>
                            <option value="Transportation">Transportation</option>
                            <option value="Academic Issues">Academic Issues</option>
                            <option value="Examination and Results">Examination & Results</option>
                            <option value="Faculty-related Grievances">Faculty-related Grievances</option>
                            <option value="Scholarships and Financial Aid">Scholarships & Financial Aid</option>
                            <option value="Fees and Administration">Fees & Administration</option>
                            <option value="Library">Library</option>
                            <option value="Laboratory Equipment">Laboratory Equipment</option>
                            <option value="Campus Safety">Campus Safety</option>
                            <option value="Harassment and Misconduct">Harassment & Misconduct</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-700">Concerned Department *</label>
                        <select
                            value={departmentId}
                            onChange={(e) => setDepartmentId(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-nie-navy"
                        >
                            {departments.map((d) => (
                                <option key={d.id} value={d.id}>
                                    {d.name} ({d.code})
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-xs font-semibold text-slate-700">Detailed Description *</label>
                    <textarea
                        required
                        rows="4"
                        placeholder="Please provide specific details: room numbers, dates, equipment involved, and any potential safety implications..."
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nie-navy"
                    ></textarea>
                </div>

                <div>
                    <label className="block text-xs font-semibold text-slate-700">Specific Campus Location / Room</label>
                    <input
                        type="text"
                        placeholder="e.g. Mechanical Workshop Block 2nd Floor, Room 204"
                        value={locationName}
                        onChange={(e) => setLocationName(e.target.value)}
                        className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nie-navy"
                    />
                </div>

                {/* Geo-tagging Section */}
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                    <div className="flex items-center justify-between">
                        <div>
                            <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                                <svg className="w-4 h-4 text-nie-navy" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                                Geo-Tagged Location Verification
                            </span>
                            <p className="text-[11px] text-slate-500 mt-0.5">
                                Captures device GPS to verify campus presence without exposing exact location to unauthorized parties.
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={captureLocation}
                            disabled={geoLoading}
                            className="bg-white hover:bg-slate-100 border border-slate-300 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-700 shadow-sm transition flex items-center gap-1"
                        >
                            {geoLoading ? "Acquiring GPS..." : lat ? "GPS Verified ✓" : "Capture Location"}
                        </button>
                    </div>

                    {lat && (
                        <div className="mt-2 text-xs font-mono text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200">
                            Lat: {lat.toFixed(5)}, Lon: {lon.toFixed(5)} &bull; Accuracy: &plusmn;{accuracy ? Math.round(accuracy) : 0}m
                        </div>
                    )}

                    {geoDenied && (
                        <div className="mt-3">
                            <label className="block text-xs font-semibold text-amber-800">
                                Location Exception Reason (Mandatory if GPS unavailable)
                            </label>
                            <input
                                type="text"
                                placeholder="e.g. Submitting from desktop PC without GPS sensor"
                                value={exceptionReason}
                                onChange={(e) => setExceptionReason(e.target.value)}
                                className="mt-1 block w-full px-3 py-1.5 border border-amber-300 rounded text-xs bg-amber-50"
                            />
                        </div>
                    )}
                </div>

                {/* Evidence Upload Section */}
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Supporting Photographic / Document Evidence
                    </label>
                    <input
                        type="file"
                        accept=".jpg,.jpeg,.png,.webp,.pdf"
                        onChange={(e) => setFile(e.target.files[0] || null)}
                        className="block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-nie-navy file:text-white hover:file:bg-nie-navydark"
                    />
                    <p className="text-[11px] text-slate-400 mt-1">Accepted formats: JPG, PNG, WEBP, PDF (Max 10MB)</p>

                    <div className="mt-2.5 flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="confidentialEvidence"
                            checked={isConfidentialEvidence}
                            onChange={(e) => setIsConfidentialEvidence(e.target.checked)}
                            className="rounded border-slate-300 text-nie-navy focus:ring-nie-navy"
                        />
                        <label htmlFor="confidentialEvidence" className="text-xs text-slate-600">
                            Treat evidence as strictly confidential (Restricted to Authorized Officers only)
                        </label>
                    </div>
                </div>

                {/* Anonymous Reporting Checkbox */}
                <div className="flex items-center gap-2 pt-1">
                    <input
                        type="checkbox"
                        id="anonymousCheck"
                        checked={isAnonymous}
                        onChange={(e) => setIsAnonymous(e.target.checked)}
                        className="rounded border-slate-300 text-nie-navy focus:ring-nie-navy"
                    />
                    <label htmlFor="anonymousCheck" className="text-xs font-medium text-slate-700">
                        Submit anonymously (Your identity will be masked in public and institutional rosters)
                    </label>
                </div>

                {/* Duplicate Complaint Warning Notice */}
                {duplicateMatches.length > 0 && (
                    <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 text-xs">
                        <div className="flex items-center gap-1.5 font-bold text-amber-800 mb-1">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            Possible Duplicate Complaints Detected
                        </div>
                        <p className="text-amber-700 mb-2">
                            The following active complaints match your issue description. If this is the same problem, your grievance will be automatically tracked under the existing redressal action:
                        </p>
                        <div className="space-y-1.5">
                            {duplicateMatches.map((m) => (
                                <div key={m.complaint_id} className="bg-white/80 p-2 rounded border border-amber-200 flex justify-between items-center">
                                    <div>
                                        <span className="font-mono font-bold text-nie-navy">{m.grievance_id}</span>: {m.title}
                                    </div>
                                    <span className="bg-amber-100 text-amber-800 font-mono px-2 py-0.5 rounded text-[10px]">
                                        {Math.round(m.similarity_score * 100)}% Match
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
                    <button
                        type="button"
                        onClick={onCancel}
                        className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        disabled={submitting}
                        className="px-5 py-2 bg-nie-navy hover:bg-nie-navydark text-white rounded-lg text-xs font-semibold shadow-sm transition disabled:opacity-50"
                    >
                        {submitting ? "Registering Grievance..." : "Submit Grievance"}
                    </button>
                </div>
            </form>
        </div>
    );
}

// ----------------------------------------------------------------------
// COMPLAINT DETAIL PAGE (Timeline, Evidence Verification, Merging, Confirmation)
// ----------------------------------------------------------------------
function ComplaintDetailPage({ complaintId, currentUser, onBack, addToast }) {
    const [complaint, setComplaint] = useState(null);
    const [loading, setLoading] = useState(true);

    // Modal action states
    const [showStatusModal, setShowStatusModal] = useState(false);
    const [newStatus, setNewStatus] = useState("under_investigation");
    const [statusRemarks, setStatusRemarks] = useState("");

    const [showOverrideModal, setShowOverrideModal] = useState(false);
    const [newPriority, setNewPriority] = useState("High");
    const [overrideReason, setOverrideReason] = useState("");

    const [showMergeModal, setShowMergeModal] = useState(false);
    const [targetDuplicateId, setTargetDuplicateId] = useState("");
    const [mergeReason, setMergeReason] = useState("");

    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [studentSatisfaction, setStudentSatisfaction] = useState(true);
    const [confirmRemarks, setConfirmRemarks] = useState("");

    const isOfficer = ["dept_officer", "grievance_cell", "principal", "super_admin"].includes(currentUser.role);
    const isOwner = complaint && complaint.complainant_name && currentUser.id;

    const loadDetails = () => {
        setLoading(true);
        API.request(`/api/complaints/${complaintId}`)
            .then((data) => setComplaint(data))
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadDetails();
    }, [complaintId]);

    // Handle evidence verification
    const handleVerifyEvidence = async (evidenceId, status, remarks = "") => {
        try {
            await API.request("/api/evidence/verify", {
                method: "POST",
                body: JSON.stringify({
                    evidence_id: evidenceId,
                    status,
                    officer_remarks: remarks || `Evidence marked as ${status}`,
                }),
            });
            addToast(`Evidence ${status} successfully.`, "success");
            loadDetails();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    // Update Status
    const handleUpdateStatus = async (e) => {
        e.preventDefault();
        try {
            await API.request(`/api/complaints/${complaintId}/status`, {
                method: "POST",
                body: JSON.stringify({
                    status: newStatus,
                    remarks: statusRemarks,
                }),
            });
            addToast(`Status updated to ${newStatus}.`, "success");
            setShowStatusModal(false);
            loadDetails();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    // Priority Override
    const handleOverridePriority = async (e) => {
        e.preventDefault();
        try {
            await API.request(`/api/complaints/${complaintId}/override-priority`, {
                method: "POST",
                body: JSON.stringify({
                    new_priority: newPriority,
                    reason: overrideReason,
                }),
            });
            addToast(`Priority updated to ${newPriority}.`, "success");
            setShowOverrideModal(false);
            loadDetails();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    // Pause / Resume Escalation
    const handleTogglePause = async () => {
        const action = complaint.is_escalation_paused ? "resume" : "pause";
        const reason = prompt(`Enter reason to ${action} 15-day escalation countdown:`);
        if (!reason) return;
        try {
            await API.request(`/api/complaints/${complaintId}/pause-escalation`, {
                method: "POST",
                body: JSON.stringify({
                    paused: !complaint.is_escalation_paused,
                    reason,
                }),
            });
            addToast(`Escalation ${action}d.`, "success");
            loadDetails();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    // Student Resolution Confirmation
    const handleStudentConfirm = async (e) => {
        e.preventDefault();
        try {
            await API.request(`/api/complaints/${complaintId}/confirm-resolution`, {
                method: "POST",
                body: JSON.stringify({
                    confirmed: studentSatisfaction,
                    remarks: confirmRemarks,
                }),
            });
            addToast("Confirmation recorded.", "success");
            setShowConfirmModal(false);
            loadDetails();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    if (loading) {
        return (
            <div className="p-12 text-center text-slate-500">
                <div className="w-8 h-8 border-4 border-nie-navy border-t-nie-gold rounded-full animate-spin mx-auto mb-3"></div>
                Loading complete grievance dossier...
            </div>
        );
    }

    if (!complaint) return null;

    // Timeline stages
    const stages = [
        { key: "submitted", label: "Submitted" },
        { key: "verified", label: "Verified" },
        { key: "assigned", label: "Assigned" },
        { key: "under_investigation", label: "Under Investigation" },
        { key: "action_taken", label: "Action Taken" },
        { key: "resolved", label: "Resolved" },
    ];
    const statusIdxMap = {
        submitted: 0,
        verified: 1,
        assigned: 2,
        under_investigation: 3,
        action_taken: 4,
        resolved: 5,
        closed: 5,
        reopened: 3,
    };
    const currentStageIdx = statusIdxMap[complaint.status] || 0;

    return (
        <div className="space-y-6">
            {/* Top Bar with Back & Grievance Title */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <button
                        onClick={onBack}
                        className="text-xs text-nie-navy hover:underline mb-1 flex items-center gap-1 font-semibold"
                    >
                        &larr; Back to Dashboard
                    </button>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="font-mono font-bold text-lg text-nie-navy">{complaint.grievance_id}</span>
                        <PriorityBadge priority={complaint.final_priority} size="lg" />
                        <StatusBadge status={complaint.status} />
                        <TierBadge tier={complaint.current_tier} />
                    </div>
                    <h1 className="text-base font-bold text-slate-800 mt-1">{complaint.title}</h1>
                </div>

                {isOfficer && (
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={() => setShowStatusModal(true)}
                            className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                        >
                            Update Status
                        </button>
                        <button
                            onClick={() => setShowOverrideModal(true)}
                            className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                        >
                            Override Priority
                        </button>
                        <button
                            onClick={handleTogglePause}
                            className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                        >
                            {complaint.is_escalation_paused ? "Resume 15d Timer" : "Pause 15d Timer"}
                        </button>
                    </div>
                )}
            </div>

            {/* 6-Stage Timeline Stepper */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-6">Redressal Lifecycle Timeline</h2>
                <div className="relative flex items-center justify-between">
                    <div className="absolute top-2.5 left-0 right-0 h-0.5 bg-slate-200 -z-0"></div>
                    {stages.map((stage, idx) => {
                        const isDone = idx < currentStageIdx || complaint.status === "resolved" || complaint.status === "closed";
                        const isCurrent = idx === currentStageIdx && complaint.status !== "resolved" && complaint.status !== "closed";
                        return (
                            <div key={stage.key} className="flex flex-col items-center relative z-10 text-center">
                                <div
                                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                                        isDone
                                            ? "bg-emerald-500 text-white"
                                            : isCurrent
                                            ? "bg-nie-gold text-white ring-4 ring-amber-100"
                                            : "bg-slate-300 text-slate-600"
                                    }`}
                                >
                                    {isDone ? "✓" : idx + 1}
                                </div>
                                <span className={`text-[11px] mt-1.5 ${isCurrent ? "font-bold text-nie-navy" : "text-slate-500"}`}>
                                    {stage.label}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Main Info Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Left 2 Cols: Description, Location, Evidence, Audit Timeline */}
                <div className="md:col-span-2 space-y-6">
                    {/* Complaint Overview Card */}
                    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
                        <div>
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Detailed Description</h3>
                            <p className="text-sm text-slate-800 mt-1 whitespace-pre-line leading-relaxed">
                                {complaint.description}
                            </p>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3 border-t border-slate-100 text-xs">
                            <div>
                                <span className="text-slate-500">Department:</span>
                                <p className="font-semibold text-slate-800">{complaint.department_name} ({complaint.department_code})</p>
                            </div>
                            <div>
                                <span className="text-slate-500">Reported By:</span>
                                <p className="font-semibold text-slate-800">
                                    {complaint.complainant_name} {complaint.complainant_identifier ? `(${complaint.complainant_identifier})` : ""}
                                </p>
                            </div>
                            <div>
                                <span className="text-slate-500">Submission Date:</span>
                                <p className="font-semibold text-slate-800">
                                    {new Date(complaint.submission_date).toLocaleDateString()}
                                </p>
                            </div>
                            <div>
                                <span className="text-slate-500">Days Pending:</span>
                                <p className="font-semibold text-slate-800">{complaint.days_pending} days</p>
                            </div>
                            <div>
                                <span className="text-slate-500">Responsible Authority:</span>
                                <p className="font-semibold text-slate-800 capitalize">{complaint.current_tier.replace("_", " ")}</p>
                            </div>
                            <div>
                                <span className="text-slate-500">Location:</span>
                                <p className="font-semibold text-slate-800">{complaint.location_name || "Campus Grounds"}</p>
                            </div>
                        </div>
                    </div>

                    {/* Geo-location & Evidence Card */}
                    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                Geo-Tagged Evidence & Verification
                            </h3>
                            {complaint.location_data && complaint.location_data.latitude && (
                                <span className="text-xs font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                                    GPS Verified ({complaint.location_data.latitude.toFixed(4)}, {complaint.location_data.longitude.toFixed(4)})
                                </span>
                            )}
                        </div>

                        {complaint.location_data && complaint.location_data.is_exception_granted && (
                            <div className="bg-amber-50 p-2.5 rounded border border-amber-200 text-xs text-amber-800">
                                <strong>GPS Exception Granted:</strong> {complaint.location_data.exception_reason}
                            </div>
                        )}

                        {complaint.evidence_items && complaint.evidence_items.length > 0 ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {complaint.evidence_items.map((ev) => (
                                    <div key={ev.id} className="border border-slate-200 rounded-lg p-3 bg-slate-50 space-y-2">
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="font-semibold truncate max-w-[150px]">{ev.file_name}</span>
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold capitalize ${
                                                ev.verification_status === "verified"
                                                    ? "bg-emerald-100 text-emerald-800"
                                                    : ev.verification_status === "rejected"
                                                    ? "bg-red-100 text-red-800"
                                                    : "bg-amber-100 text-amber-800"
                                            }`}>
                                                {ev.verification_status.replace("_", " ")}
                                            </span>
                                        </div>

                                        {ev.file_type && ev.file_type.startsWith("image/") ? (
                                            <a href={ev.file_url} target="_blank" rel="noopener noreferrer">
                                                <img
                                                    src={ev.file_url}
                                                    alt="Evidence photograph"
                                                    className="w-full h-36 object-cover rounded border border-slate-200 hover:opacity-90 transition"
                                                />
                                            </a>
                                        ) : (
                                            <div className="h-28 flex items-center justify-center bg-white rounded border border-slate-200">
                                                <a href={ev.file_url} target="_blank" className="text-nie-navy hover:underline text-xs font-semibold">
                                                    Download Document ({Math.round(ev.file_size_bytes / 1024)} KB)
                                                </a>
                                            </div>
                                        )}

                                        {ev.officer_remarks && (
                                            <p className="text-[11px] text-slate-600 bg-white p-1.5 rounded border border-slate-100">
                                                Officer Note: {ev.officer_remarks}
                                            </p>
                                        )}

                                        {isOfficer && ev.verification_status === "pending_verification" && (
                                            <div className="flex gap-2 pt-2">
                                                <button
                                                    onClick={() => handleVerifyEvidence(ev.id, "verified")}
                                                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold py-1 rounded transition"
                                                >
                                                    Verify
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        const r = prompt("Reason for rejection:");
                                                        if (r) handleVerifyEvidence(ev.id, "rejected", r);
                                                    }}
                                                    className="flex-1 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold py-1 rounded transition"
                                                >
                                                    Reject
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-xs text-slate-500 italic">No photographic evidence attached to this grievance.</p>
                        )}
                    </div>

                    {/* Timeline Log */}
                    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                            Investigation History & Audit Trail
                        </h3>
                        <div className="space-y-3">
                            {complaint.timeline_entries.map((t) => (
                                <div key={t.id} className="flex items-start gap-3 text-xs border-l-2 border-nie-navy pl-3 py-0.5">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-slate-800">{t.action}</span>
                                            <span className="text-[10px] text-slate-400">
                                                {new Date(t.timestamp).toLocaleString()}
                                            </span>
                                        </div>
                                        {t.remarks && <p className="text-slate-600 mt-0.5">{t.remarks}</p>}
                                        <span className="text-[10px] text-slate-400">Recorded by: {t.actor_name}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right Col: ML Insights, 15-day countdown, Duplicates, Confirmation */}
                <div className="space-y-6">
                    {/* ML Priority & Safety Analysis Card */}
                    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">ML Urgency Assessment</h3>
                            <PriorityBadge priority={complaint.final_priority} />
                        </div>

                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs space-y-1.5">
                            <div className="flex justify-between">
                                <span className="text-slate-500">Predicted Class:</span>
                                <span className="font-bold text-slate-700">{complaint.predicted_priority}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500">Confidence Score:</span>
                                <span className="font-mono text-slate-700">{Math.round((complaint.priority_confidence || 0.7) * 100)}%</span>
                            </div>
                            {complaint.is_safety_critical && (
                                <div className="text-red-700 font-semibold bg-red-50 p-1 rounded border border-red-200">
                                    Safety-Critical Hazard Flagged
                                </div>
                            )}
                            <p className="text-[11px] text-slate-500 pt-1 leading-snug border-t border-slate-200">
                                {complaint.priority_explanation || "Assessed via institutional grievance vectorizer."}
                            </p>
                        </div>
                    </div>

                    {/* 15-Day Escalation Matrix Status Card */}
                    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">15-Day Escalation Tracker</h3>
                        <div className="space-y-2 text-xs">
                            <div className="flex justify-between items-center">
                                <span className="text-slate-500">Current Level:</span>
                                <TierBadge tier={complaint.current_tier} />
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-slate-500">Action Deadline:</span>
                                <DeadlinePill
                                    deadline={complaint.expected_deadline}
                                    daysPending={complaint.days_pending}
                                    isPaused={complaint.is_escalation_paused}
                                />
                            </div>
                            {complaint.is_escalation_paused && (
                                <div className="bg-slate-100 p-2 rounded text-[11px] text-slate-600">
                                    <strong>Paused Reason:</strong> {complaint.escalation_pause_reason}
                                </div>
                            )}
                            <p className="text-[10px] text-slate-400 leading-tight pt-1">
                                Notice: Unresolved complaints automatically advance from Tier 1 to Tier 2, and Tier 2 to Tier 3 every 15 calendar days.
                            </p>
                        </div>
                    </div>

                    {/* Duplicate Complaints Section */}
                    {complaint.duplicates_list && complaint.duplicates_list.length > 0 && (
                        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                Linked Duplicate Cases ({complaint.duplicates_list.length})
                            </h3>
                            <div className="space-y-2">
                                {complaint.duplicates_list.map((dup) => (
                                    <div key={dup.id} className="p-2.5 bg-slate-50 rounded border border-slate-200 text-xs">
                                        <div className="font-mono font-bold text-nie-navy">{dup.grievance_id}</div>
                                        <div className="text-slate-700 truncate">{dup.title}</div>
                                        <div className="text-[10px] text-slate-500 mt-1">Reported by {dup.complainant_name}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Student Confirmation Banner */}
                    {complaint.status === "resolved" && (
                        <div className="bg-emerald-50 border border-emerald-300 p-4 rounded-xl shadow-sm text-xs space-y-2">
                            <div className="flex items-center gap-1.5 font-bold text-emerald-800">
                                <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Resolution Confirmation Required
                            </div>
                            <p className="text-emerald-700">
                                The department officer has marked this issue as resolved. Please confirm whether the corrective action is satisfactory.
                            </p>
                            {complaint.resolution_remarks && (
                                <div className="bg-white p-2 rounded text-slate-700 font-medium">
                                    Officer Remarks: {complaint.resolution_remarks}
                                </div>
                            )}

                            {complaint.student_confirmed === null ? (
                                <button
                                    onClick={() => setShowConfirmModal(true)}
                                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-1.5 rounded transition"
                                >
                                    Review & Confirm Resolution
                                </button>
                            ) : (
                                <div className="font-semibold text-emerald-800 pt-1">
                                    Student response: {complaint.student_confirmed ? "Confirmed Resolved ✓" : "Reopened with comments"}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* STATUS UPDATE MODAL */}
            {showStatusModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
                    <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
                        <h3 className="text-sm font-bold text-nie-navy mb-4">Transition Grievance Status</h3>
                        <form onSubmit={handleUpdateStatus} className="space-y-4 text-xs">
                            <div>
                                <label className="block font-semibold text-slate-700">Select New Status</label>
                                <select
                                    value={newStatus}
                                    onChange={(e) => setNewStatus(e.target.value)}
                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                                >
                                    <option value="assigned">Assigned</option>
                                    <option value="under_investigation">Under Investigation</option>
                                    <option value="action_taken">Action Taken</option>
                                    <option value="resolved">Resolved</option>
                                    <option value="closed">Closed</option>
                                </select>
                            </div>
                            <div>
                                <label className="block font-semibold text-slate-700">Official Remarks</label>
                                <textarea
                                    required
                                    rows="3"
                                    placeholder="Explain the inspection findings, contractor work orders, or resolution actions taken..."
                                    value={statusRemarks}
                                    onChange={(e) => setStatusRemarks(e.target.value)}
                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                                ></textarea>
                            </div>
                            <div className="flex justify-end gap-2 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowStatusModal(false)}
                                    className="px-3 py-1.5 border border-slate-300 rounded text-slate-700"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-1.5 bg-nie-navy text-white rounded font-semibold"
                                >
                                    Save Status
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* PRIORITY OVERRIDE MODAL */}
            {showOverrideModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
                    <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
                        <h3 className="text-sm font-bold text-nie-navy mb-4">Manual Priority Override</h3>
                        <form onSubmit={handleOverridePriority} className="space-y-4 text-xs">
                            <div>
                                <label className="block font-semibold text-slate-700">Select Priority</label>
                                <select
                                    value={newPriority}
                                    onChange={(e) => setNewPriority(e.target.value)}
                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                                >
                                    <option value="Critical">Critical</option>
                                    <option value="High">High</option>
                                    <option value="Medium">Medium</option>
                                    <option value="Low">Low</option>
                                </select>
                            </div>
                            <div>
                                <label className="block font-semibold text-slate-700">Mandatory Justification Reason</label>
                                <textarea
                                    required
                                    rows="3"
                                    placeholder="Provide detailed justification for overriding the ML-predicted priority..."
                                    value={overrideReason}
                                    onChange={(e) => setOverrideReason(e.target.value)}
                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                                ></textarea>
                            </div>
                            <div className="flex justify-end gap-2 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowOverrideModal(false)}
                                    className="px-3 py-1.5 border border-slate-300 rounded text-slate-700"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-1.5 bg-nie-navy text-white rounded font-semibold"
                                >
                                    Confirm Override
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* STUDENT CONFIRMATION MODAL */}
            {showConfirmModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
                    <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
                        <h3 className="text-sm font-bold text-nie-navy mb-4">Confirm Issue Resolution</h3>
                        <form onSubmit={handleStudentConfirm} className="space-y-4 text-xs">
                            <div className="flex gap-4">
                                <label className="flex items-center gap-1.5 cursor-pointer">
                                    <input
                                        type="radio"
                                        checked={studentSatisfaction === true}
                                        onChange={() => setStudentSatisfaction(true)}
                                    />
                                    <span className="font-semibold text-emerald-700">Issue is Resolved</span>
                                </label>
                                <label className="flex items-center gap-1.5 cursor-pointer">
                                    <input
                                        type="radio"
                                        checked={studentSatisfaction === false}
                                        onChange={() => setStudentSatisfaction(false)}
                                    />
                                    <span className="font-semibold text-rose-700">Unsatisfied (Reopen)</span>
                                </label>
                            </div>
                            <div>
                                <label className="block font-semibold text-slate-700">Student Remarks / Feedback</label>
                                <textarea
                                    rows="3"
                                    placeholder="Enter your feedback on the resolution..."
                                    value={confirmRemarks}
                                    onChange={(e) => setConfirmRemarks(e.target.value)}
                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
                                ></textarea>
                            </div>
                            <div className="flex justify-end gap-2 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmModal(false)}
                                    className="px-3 py-1.5 border border-slate-300 rounded text-slate-700"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-1.5 bg-nie-navy text-white rounded font-semibold"
                                >
                                    Submit Confirmation
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}

// ----------------------------------------------------------------------
// SCHOLARSHIP RECOMMENDATION PORTAL
// ----------------------------------------------------------------------
function ScholarshipPortal({ currentUser, addToast }) {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showProfileEdit, setShowProfileEdit] = useState(false);

    // Profile form
    const [branch, setBranch] = useState("Computer Science & Engineering");
    const [year, setYear] = useState(3);
    const [semester, setSemester] = useState(6);
    const [cgpa, setCgpa] = useState(8.5);
    const [annualIncome, setAnnualIncome] = useState(250000);
    const [category, setCategory] = useState("OBC");
    const [domicile, setDomicile] = useState("Karnataka");
    const [disability, setDisability] = useState(false);

    const loadRecommendations = () => {
        setLoading(true);
        API.request("/api/scholarships/recommendations")
            .then((data) => setRecommendations(data))
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadRecommendations();
    }, []);

    const handleSaveProfile = async (e) => {
        e.preventDefault();
        try {
            await API.request("/api/scholarships/profile", {
                method: "POST",
                body: JSON.stringify({
                    branch,
                    year: parseInt(year),
                    semester: parseInt(semester),
                    cgpa: parseFloat(cgpa),
                    annual_income: parseFloat(annualIncome),
                    category,
                    state_of_domicile: domicile,
                    disability_status: disability,
                }),
            });
            addToast("Scholarship profile updated successfully.", "success");
            setShowProfileEdit(false);
            loadRecommendations();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    return (
        <div className="space-y-6">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-bold text-nie-navy">Scholarship & Financial Aid Intelligence</h1>
                    <p className="text-xs text-slate-500 mt-1">
                        Rule-based eligibility engine mapping your academic credentials and domicile to verified Karnataka and National schemes.
                    </p>
                </div>
                <button
                    onClick={() => setShowProfileEdit(!showProfileEdit)}
                    className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-4 py-2 rounded-lg transition"
                >
                    {showProfileEdit ? "Close Profile" : "Edit Academic Profile"}
                </button>
            </div>

            {/* Profile Edit Drawer */}
            {showProfileEdit && (
                <div className="bg-white p-6 rounded-xl border border-nie-navy/20 shadow-md">
                    <h2 className="text-sm font-bold text-nie-navy mb-4">Student Academic & Financial Details</h2>
                    <form onSubmit={handleSaveProfile} className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                        <div>
                            <label className="block font-semibold text-slate-700">Engineering Branch</label>
                            <input
                                type="text"
                                value={branch}
                                onChange={(e) => setBranch(e.target.value)}
                                className="mt-1 w-full p-2 border rounded"
                            />
                        </div>
                        <div>
                            <label className="block font-semibold text-slate-700">Current CGPA</label>
                            <input
                                type="number"
                                step="0.01"
                                max="10"
                                min="0"
                                value={cgpa}
                                onChange={(e) => setCgpa(e.target.value)}
                                className="mt-1 w-full p-2 border rounded"
                            />
                        </div>
                        <div>
                            <label className="block font-semibold text-slate-700">Annual Family Income (INR)</label>
                            <input
                                type="number"
                                step="1000"
                                value={annualIncome}
                                onChange={(e) => setAnnualIncome(e.target.value)}
                                className="mt-1 w-full p-2 border rounded"
                            />
                        </div>
                        <div>
                            <label className="block font-semibold text-slate-700">Category</label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className="mt-1 w-full p-2 border rounded bg-white"
                            >
                                <option value="General">General</option>
                                <option value="OBC">OBC</option>
                                <option value="SC">SC</option>
                                <option value="ST">ST</option>
                                <option value="Cat-1">Cat-1</option>
                                <option value="2A">2A</option>
                                <option value="2B">2B</option>
                                <option value="3A">3A</option>
                                <option value="3B">3B</option>
                            </select>
                        </div>
                        <div>
                            <label className="block font-semibold text-slate-700">State of Domicile</label>
                            <input
                                type="text"
                                value={domicile}
                                onChange={(e) => setDomicile(e.target.value)}
                                className="mt-1 w-full p-2 border rounded"
                            />
                        </div>
                        <div className="flex items-center gap-2 pt-5">
                            <input
                                type="checkbox"
                                id="disabilityCheck"
                                checked={disability}
                                onChange={(e) => setDisability(e.target.checked)}
                            />
                            <label htmlFor="disabilityCheck" className="text-slate-700 font-semibold">
                                Specially-Abled (Benchmark &ge; 40%)
                            </label>
                        </div>
                        <div className="sm:col-span-3 flex justify-end gap-2 pt-2">
                            <button
                                type="submit"
                                className="bg-nie-navy text-white px-5 py-2 rounded font-semibold"
                            >
                                Re-Calculate Eligibility
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Recommendations List */}
            {loading ? (
                <div className="p-12 text-center text-slate-500 text-sm">
                    <div className="w-6 h-6 border-2 border-nie-navy border-t-nie-gold rounded-full animate-spin mx-auto mb-2"></div>
                    Evaluating genuine scholarships against student profile...
                </div>
            ) : recommendations.length === 0 ? (
                <div className="bg-white p-8 rounded-xl border text-center text-slate-500">
                    No active scholarships found.
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {recommendations.map((rec) => {
                        const sch = rec.scholarship;
                        const isEligible = rec.status === "Eligible";
                        const isPot = rec.status === "Potentially Eligible";
                        return (
                            <div
                                key={sch.id}
                                className={`bg-white rounded-xl border p-5 shadow-sm space-y-3 transition-all ${
                                    isEligible
                                        ? "border-emerald-300 ring-1 ring-emerald-200"
                                        : isPot
                                        ? "border-amber-300"
                                        : "border-slate-200 opacity-75"
                                }`}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div>
                                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                                            {sch.provider}
                                        </span>
                                        <h3 className="font-bold text-sm text-nie-navy">{sch.name}</h3>
                                    </div>
                                    <span
                                        className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                                            isEligible
                                                ? "bg-emerald-100 text-emerald-800"
                                                : isPot
                                                ? "bg-amber-100 text-amber-800"
                                                : "bg-slate-100 text-slate-600"
                                        }`}
                                    >
                                        {rec.status} ({Math.round(rec.match_score)}%)
                                    </span>
                                </div>

                                <p className="text-xs text-slate-600">{sch.description}</p>

                                <div className="bg-slate-50 p-3 rounded-lg text-xs space-y-1">
                                    <div className="font-semibold text-nie-navy flex items-center gap-1">
                                        <span>Benefits:</span>
                                        <span className="text-slate-800 font-normal">{sch.financial_benefits}</span>
                                    </div>
                                    <div className="text-slate-600">
                                        <strong>Deadline:</strong> {new Date(sch.application_deadline).toLocaleDateString()} &bull;{" "}
                                        <span className="text-nie-gold font-semibold">{rec.deadline_days_left} days remaining</span>
                                    </div>
                                    <div className="text-[11px] text-slate-500 pt-1">
                                        <strong>Required Documents:</strong> {sch.required_documents}
                                    </div>
                                </div>

                                {rec.match_reasons.length > 0 && (
                                    <div className="text-[11px] text-emerald-700 space-y-0.5">
                                        {rec.match_reasons.map((r, i) => (
                                            <div key={i}>✓ {r}</div>
                                        ))}
                                    </div>
                                )}

                                {rec.missing_criteria.length > 0 && (
                                    <div className="text-[11px] text-rose-600 space-y-0.5">
                                        {rec.missing_criteria.map((m, i) => (
                                            <div key={i}>✗ {m}</div>
                                        ))}
                                    </div>
                                )}

                                <div className="pt-2 flex justify-end">
                                    <a
                                        href={sch.official_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-4 py-1.5 rounded-lg transition inline-flex items-center gap-1"
                                    >
                                        <span>Official Portal</span> &rarr;
                                    </a>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

// ----------------------------------------------------------------------
// 15-DAY ESCALATION MATRIX DASHBOARD (Tier 1, Tier 2, Tier 3 Monitor)
// ----------------------------------------------------------------------
function EscalationMatrixDashboard({ currentUser, onSelectComplaint, addToast }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    const loadEscalationData = () => {
        setLoading(true);
        API.request("/api/escalations/dashboard")
            .then((res) => setData(res))
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadEscalationData();
    }, []);

    const handleRunCheck = async () => {
        try {
            const res = await API.request("/api/escalations/run-check", { method: "POST" });
            addToast("15-day escalation boundaries evaluated.", "success");
            loadEscalationData();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    if (loading) {
        return <div className="p-12 text-center text-slate-500">Loading escalation matrix...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-bold text-nie-navy">Three-Tier Escalation Matrix Monitor</h1>
                    <p className="text-xs text-slate-500 mt-1">
                        Automated backend supervisor enforcing strict 15 calendar day resolution ceilings across Department (Tier 1), Grievance Cell (Tier 2), and Principal (Tier 3).
                    </p>
                </div>
                <button
                    onClick={handleRunCheck}
                    className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-4 py-2 rounded-lg transition"
                >
                    Evaluate Escalation Check
                </button>
            </div>

            {/* Matrix Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-slate-500 font-semibold">Tier 1: Department Level</p>
                    <p className="text-2xl font-bold text-sky-700 mt-1">{data.tier1_count}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">15-day window</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-slate-500 font-semibold">Tier 2: Grievance Cell</p>
                    <p className="text-2xl font-bold text-purple-700 mt-1">{data.tier2_count}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">Escalated from T1</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-slate-500 font-semibold">Tier 3: Principal Authority</p>
                    <p className="text-2xl font-bold text-rose-700 mt-1">{data.tier3_count}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">Executive Review</p>
                </div>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-slate-500 font-semibold">Approaching Deadline (&le; 3d)</p>
                    <p className="text-2xl font-bold text-amber-600 mt-1">{data.approaching_deadline_count}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">Overdue: {data.overdue_count}</p>
                </div>
            </div>

            {/* Approaching / Overdue Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-200 bg-amber-50/50">
                    <h2 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                        Cases Requiring Immediate Departmental Intervention (&le; 3 Days or Overdue)
                    </h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-600">
                        <thead className="bg-slate-50 text-[10px] uppercase font-semibold text-slate-700 border-b">
                            <tr>
                                <th className="px-4 py-2.5">Grievance ID</th>
                                <th className="px-4 py-2.5">Title</th>
                                <th className="px-4 py-2.5">Department</th>
                                <th className="px-4 py-2.5">Current Tier</th>
                                <th className="px-4 py-2.5">Time Remaining</th>
                                <th className="px-4 py-2.5 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {[...(data.overdue_items || []), ...(data.approaching_deadline_items || [])].map((item) => (
                                <tr key={item.id} className="hover:bg-slate-50">
                                    <td className="px-4 py-2.5 font-mono font-bold text-nie-navy">{item.grievance_id}</td>
                                    <td className="px-4 py-2.5 font-semibold text-slate-800">{item.title}</td>
                                    <td className="px-4 py-2.5 font-mono">{item.department_code}</td>
                                    <td className="px-4 py-2.5"><TierBadge tier={item.current_tier} /></td>
                                    <td className="px-4 py-2.5 font-mono font-bold text-amber-700">
                                        {item.days_remaining < 0 ? `Overdue by ${Math.abs(item.days_remaining)}d` : `${item.days_remaining}d left`}
                                    </td>
                                    <td className="px-4 py-2.5 text-right">
                                        <button
                                            onClick={() => onSelectComplaint(item.id)}
                                            className="text-nie-navy hover:underline font-semibold"
                                        >
                                            Inspect &rarr;
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Department-wise Escalation Breakdown */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
                <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Department Accountability & Resolution Performance
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {data.department_escalations.map((d) => (
                        <div key={d.department_id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                            <div className="font-bold text-slate-800">{d.department_name} ({d.department_code})</div>
                            <div className="mt-2 grid grid-cols-3 gap-1 text-center font-mono">
                                <div className="bg-sky-100 text-sky-800 p-1 rounded">
                                    <div className="font-bold">{d.tier1_count}</div>
                                    <div className="text-[9px]">Tier 1</div>
                                </div>
                                <div className="bg-purple-100 text-purple-800 p-1 rounded">
                                    <div className="font-bold">{d.tier2_count}</div>
                                    <div className="text-[9px]">Tier 2</div>
                                </div>
                                <div className="bg-rose-100 text-rose-800 p-1 rounded">
                                    <div className="font-bold">{d.tier3_count}</div>
                                    <div className="text-[9px]">Tier 3</div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// INSTITUTIONAL ANALYTICS & REPORTING
// ----------------------------------------------------------------------
function AnalyticsView({ currentUser, addToast }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        API.request("/api/analytics/overview")
            .then((data) => setStats(data))
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="p-12 text-center text-slate-500">Loading analytics engine...</div>;
    if (!stats) return null;

    return (
        <div className="space-y-6">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <h1 className="text-xl font-bold text-nie-navy">Institutional Analytics & Redressal Metrics</h1>
                <p className="text-xs text-slate-500 mt-1">
                    Live grievance indicators and resolution trends across NIE departments.
                </p>
            </div>

            {/* Overview Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                <div className="bg-white p-4 rounded-xl border shadow-sm">
                    <p className="text-xs text-slate-500">Total Volume</p>
                    <p className="text-2xl font-bold text-nie-navy">{stats.overview.total_complaints}</p>
                </div>
                <div className="bg-white p-4 rounded-xl border shadow-sm">
                    <p className="text-xs text-emerald-600">Resolution Rate</p>
                    <p className="text-2xl font-bold text-emerald-700">
                        {stats.overview.total_complaints > 0
                            ? Math.round((stats.overview.resolved_complaints / stats.overview.total_complaints) * 100)
                            : 0}%
                    </p>
                </div>
                <div className="bg-white p-4 rounded-xl border shadow-sm">
                    <p className="text-xs text-slate-500">Avg Resolution Time</p>
                    <p className="text-2xl font-bold text-slate-700">{stats.overview.average_resolution_days} days</p>
                </div>
                <div className="bg-white p-4 rounded-xl border shadow-sm">
                    <p className="text-xs text-purple-600">Duplicate Cases Merged</p>
                    <p className="text-2xl font-bold text-purple-700">{stats.overview.duplicates_detected}</p>
                </div>
            </div>

            {/* Category Breakdown & Priority Distribution */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white p-5 rounded-xl border shadow-sm space-y-3">
                    <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Category Breakdown</h2>
                    <div className="space-y-2">
                        {stats.by_category.slice(0, 6).map((cat) => (
                            <div key={cat.label} className="text-xs">
                                <div className="flex justify-between font-semibold mb-1">
                                    <span>{cat.label}</span>
                                    <span>{cat.count} ({cat.percentage}%)</span>
                                </div>
                                <div className="w-full bg-slate-100 rounded-full h-2">
                                    <div
                                        className="bg-nie-navy h-2 rounded-full"
                                        style={{ width: `${cat.percentage}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-white p-5 rounded-xl border shadow-sm space-y-3">
                    <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Priority Distribution</h2>
                    <div className="space-y-2">
                        {stats.by_priority.map((prio) => (
                            <div key={prio.label} className="text-xs">
                                <div className="flex justify-between font-semibold mb-1">
                                    <span className="flex items-center gap-1.5">
                                        <PriorityBadge priority={prio.label} />
                                    </span>
                                    <span>{prio.count} ({prio.percentage}%)</span>
                                </div>
                                <div className="w-full bg-slate-100 rounded-full h-2">
                                    <div
                                        className={`h-2 rounded-full ${
                                            prio.label === "Critical"
                                                ? "bg-red-500"
                                                : prio.label === "High"
                                                ? "bg-amber-500"
                                                : "bg-blue-500"
                                        }`}
                                        style={{ width: `${prio.percentage}%` }}
                                    ></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// SUPER ADMIN PANEL (User Provisioning, Departments, Audit Logs)
// ----------------------------------------------------------------------
function AdminPanel({ currentUser, addToast }) {
    const [users, setUsers] = useState([]);
    const [auditLogs, setAuditLogs] = useState([]);
    const [departments, setDepartments] = useState([]);

    useEffect(() => {
        API.request("/api/admin/users").then(setUsers).catch(() => {});
        API.request("/api/admin/departments").then(setDepartments).catch(() => {});
        API.request("/api/admin/audit-logs").then(setAuditLogs).catch(() => {});
    }, []);

    return (
        <div className="space-y-6">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <h1 className="text-xl font-bold text-nie-navy">Super Admin Operations & Audit Logs</h1>
                <p className="text-xs text-slate-500 mt-1">
                    System configuration, user provisioning, and full institutional audit trail.
                </p>
            </div>

            {/* Users Directory */}
            <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b flex justify-between items-center">
                    <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Registered Users</h2>
                    <span className="text-xs text-slate-500 font-mono">{users.length} Users</span>
                </div>
                <div className="overflow-x-auto max-h-72">
                    <table className="w-full text-left text-xs text-slate-600">
                        <thead className="bg-slate-50 text-[10px] uppercase font-semibold text-slate-700 sticky top-0">
                            <tr>
                                <th className="px-4 py-2">Name</th>
                                <th className="px-4 py-2">Role</th>
                                <th className="px-4 py-2">Identifier / Email</th>
                                <th className="px-4 py-2">Department</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {users.map((u) => (
                                <tr key={u.id} className="hover:bg-slate-50">
                                    <td className="px-4 py-2 font-semibold text-slate-800">{u.full_name}</td>
                                    <td className="px-4 py-2 capitalize font-mono text-[11px]">{u.role.replace("_", " ")}</td>
                                    <td className="px-4 py-2 font-mono text-slate-500">{u.identifier || u.email}</td>
                                    <td className="px-4 py-2">{u.department_name || "Campus-wide"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Audit Logs */}
            <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b">
                    <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Security & Activity Audit Logs</h2>
                </div>
                <div className="overflow-x-auto max-h-72">
                    <table className="w-full text-left text-xs text-slate-600">
                        <thead className="bg-slate-50 text-[10px] uppercase font-semibold text-slate-700 sticky top-0">
                            <tr>
                                <th className="px-4 py-2">Timestamp</th>
                                <th className="px-4 py-2">Action</th>
                                <th className="px-4 py-2">Actor</th>
                                <th className="px-4 py-2">Details</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {auditLogs.map((log) => (
                                <tr key={log.id} className="hover:bg-slate-50">
                                    <td className="px-4 py-2 font-mono text-[11px] text-slate-400">
                                        {new Date(log.created_at).toLocaleString()}
                                    </td>
                                    <td className="px-4 py-2 font-bold text-nie-navy font-mono">{log.action}</td>
                                    <td className="px-4 py-2">{log.actor_name}</td>
                                    <td className="px-4 py-2 text-slate-600">{log.details}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// INSTITUTIONAL AI CHATBOT DRAWER COMPONENT
// ----------------------------------------------------------------------
function ChatbotDrawer({ isOpen, onClose, currentUser }) {
    const [messages, setMessages] = useState([
        {
            sender: "bot",
            message: `Hello ${currentUser ? currentUser.full_name.split(" ")[0] : "there"}! I am **NIEresolve AI**, your official NIE Mysuru institutional assistant.\n\nAsk me about grievance status, 15-day escalation policies, departments, or scholarships!`,
            sources: ["NIE Institutional Handbook"],
        },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        if (isOpen) scrollToBottom();
    }, [messages, isOpen]);

    const handleSend = async (queryText = null) => {
        const textToSend = queryText || input;
        if (!textToSend.trim()) return;

        const userMsg = { sender: "user", message: textToSend };
        setMessages((prev) => [...prev, userMsg]);
        if (!queryText) setInput("");
        setLoading(true);

        try {
            const data = await API.request("/api/chatbot/query", {
                method: "POST",
                body: JSON.stringify({ query: textToSend }),
            });

            setMessages((prev) => [
                ...prev,
                {
                    sender: "bot",
                    message: data.response,
                    sources: data.sources || [],
                    is_live_data: data.is_live_data,
                },
            ]);
        } catch (err) {
            setMessages((prev) => [
                ...prev,
                {
                    sender: "bot",
                    message: "Sorry, I encountered an issue querying institutional records. Please try again or email grievancecell@nie.ac.in.",
                    sources: ["System Error"],
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-y-0 right-0 max-w-sm sm:max-w-md w-full bg-white shadow-2xl z-50 flex flex-col border-l border-slate-200 chat-drawer">
            {/* Header */}
            <div className="p-4 institutional-banner text-white flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-nie-gold text-white flex items-center justify-center font-bold text-sm shadow">
                        AI
                    </div>
                    <div>
                        <h2 className="font-bold text-sm">NIEresolve Assistant</h2>
                        <span className="text-[10px] text-slate-300">NIE Mysuru Verified Knowledge Base</span>
                    </div>
                </div>
                <button
                    onClick={onClose}
                    className="p-1 rounded-md hover:bg-white/10 text-slate-300 hover:text-white"
                >
                    &times;
                </button>
            </div>

            {/* Quick Prompts */}
            <div className="bg-slate-50 p-2 border-b flex gap-1.5 overflow-x-auto text-[11px]">
                <button
                    onClick={() => handleSend("What is the status of my complaints?")}
                    className="bg-white hover:bg-slate-100 border rounded-full px-2.5 py-1 whitespace-nowrap text-slate-700 shadow-xs"
                >
                    My Grievance Status
                </button>
                <button
                    onClick={() => handleSend("How does the 15-day escalation matrix work?")}
                    className="bg-white hover:bg-slate-100 border rounded-full px-2.5 py-1 whitespace-nowrap text-slate-700 shadow-xs"
                >
                    15-Day Escalation Policy
                </button>
                <button
                    onClick={() => handleSend("What scholarships am I eligible for?")}
                    className="bg-white hover:bg-slate-100 border rounded-full px-2.5 py-1 whitespace-nowrap text-slate-700 shadow-xs"
                >
                    Scholarships For Me
                </button>
                <button
                    onClick={() => handleSend("Which department handles hostel water issues?")}
                    className="bg-white hover:bg-slate-100 border rounded-full px-2.5 py-1 whitespace-nowrap text-slate-700 shadow-xs"
                >
                    Hostel Department
                </button>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 text-xs">
                {messages.map((m, i) => (
                    <div
                        key={i}
                        className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
                    >
                        <div
                            className={`p-3 rounded-xl max-w-[85%] whitespace-pre-line leading-relaxed ${
                                m.sender === "user"
                                    ? "bg-nie-navy text-white rounded-br-none"
                                    : "bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200"
                            }`}
                        >
                            {m.message}
                        </div>
                        {m.sources && m.sources.length > 0 && (
                            <span className="text-[9px] text-slate-400 mt-1 font-mono">
                                Sources: {m.sources.join(", ")}
                            </span>
                        )}
                    </div>
                ))}
                {loading && (
                    <div className="flex items-center gap-2 text-slate-400 text-xs italic">
                        <div className="w-4 h-4 border-2 border-nie-navy border-t-nie-gold rounded-full animate-spin"></div>
                        Searching institutional records...
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="p-3 border-t bg-slate-50 flex gap-2">
                <input
                    type="text"
                    placeholder="Ask about complaints, departments, policies..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    className="flex-1 px-3 py-2 border rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-nie-navy bg-white"
                />
                <button
                    onClick={() => handleSend()}
                    disabled={!input.trim()}
                    className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-3 py-2 rounded-lg transition disabled:opacity-50"
                >
                    Send
                </button>
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// NOTIFICATION DROPDOWN COMPONENT
// ----------------------------------------------------------------------
function NotificationDropdown({ notifications, onClose, onRefresh, addToast }) {
    const handleMarkAllRead = async () => {
        try {
            await API.request("/api/notifications/read-all", { method: "POST" });
            onRefresh();
            addToast("All notifications marked as read.", "success");
        } catch (err) {}
    };

    return (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-2xl border border-slate-200 z-50 text-xs overflow-hidden">
            <div className="p-3 border-b flex justify-between items-center bg-slate-50">
                <span className="font-bold text-nie-navy">Notifications</span>
                <button
                    onClick={handleMarkAllRead}
                    className="text-[11px] text-nie-navy hover:underline"
                >
                    Mark All Read
                </button>
            </div>
            <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                {notifications.length === 0 ? (
                    <div className="p-6 text-center text-slate-400">No new notifications</div>
                ) : (
                    notifications.map((n) => (
                        <div
                            key={n.id}
                            className={`p-3 space-y-0.5 hover:bg-slate-50 transition ${
                                !n.is_read ? "bg-amber-50/50" : ""
                            }`}
                        >
                            <div className="flex justify-between font-semibold text-slate-800">
                                <span>{n.title}</span>
                                {!n.is_read && <span className="w-1.5 h-1.5 rounded-full bg-nie-gold"></span>}
                            </div>
                            <p className="text-slate-600 leading-snug">{n.message}</p>
                            <span className="text-[10px] text-slate-400 block pt-0.5">
                                {new Date(n.created_at).toLocaleString()}
                            </span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

// Mount React Root
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);

