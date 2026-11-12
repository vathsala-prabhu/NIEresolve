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
            if (res.status === 401 && !url.includes("/api/auth/")) {
                // Token expired on an authenticated route
                const hadToken = !!localStorage.getItem("nieresolve_token");
                localStorage.removeItem("nieresolve_token");
                localStorage.removeItem("nieresolve_user");
                if (hadToken) {
                    window.location.reload();
                }
                throw new Error("Session expired. Please log in again.");
            }
            const data = await res.json().catch(() => ({}));
            if (!res.ok) {
                let msg = "An error occurred";
                if (typeof data.detail === "string") {
                    msg = data.detail;
                } else if (Array.isArray(data.detail)) {
                    // FastAPI 422 validation errors are arrays of {loc, msg, type}
                    msg = data.detail.map((d) => {
                        const field = Array.isArray(d.loc) ? d.loc.filter(x => x !== 'body').join('.') : '';
                        return field ? `${field}: ${d.msg}` : d.msg;
                    }).join("; ");
                } else if (data.message) {
                    msg = data.message;
                }
                throw new Error(msg);
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
        resolved_awaiting_confirmation: { label: "Resolved (Awaiting Confirmation)", color: "bg-amber-50 text-amber-800 border-amber-300 font-medium" },
        confirmed_resolved: { label: "Confirmed Resolved ✓", color: "bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold" },
        auto_confirmed_resolved: { label: "Auto-Confirmed (5-Day)", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
        resolved: { label: "Resolved", color: "bg-emerald-50 text-emerald-700 border-emerald-200 font-medium" },
        closed: { label: "Closed", color: "bg-slate-100 text-slate-700 border-slate-300" },
        reopened: { label: "Reopened ⚠️", color: "bg-rose-50 text-rose-700 border-rose-300 font-medium" },
    };
    const conf = labels[s] || { label: s, color: "bg-slate-100 text-slate-700 border-slate-200" };
    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs border ${conf.color}`}>
            {conf.label}
        </span>
    );
}

// Campus Badge Component
function CampusBadge({ campus }) {
    const isNorth = (campus || "").includes("North");
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border font-medium ${isNorth ? "bg-blue-50 text-blue-700 border-blue-200" : "bg-emerald-50 text-emerald-700 border-emerald-200"}`}>
            <span>{isNorth ? "🏢" : "🏛️"}</span>
            <span>{campus || "North Campus"}</span>
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
    } else if (diffDays === 0) {
        color = "bg-amber-50 text-amber-800 border-amber-300 font-medium";
        text = "Due today";
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
                    className={`pointer-events-auto p-4 rounded-lg shadow-lg border text-sm flex items-start gap-3 transition-all transform translate-y-0 ${t.type === "error"
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

// ALL UPDATES MODAL COMPONENT
function AllUpdatesModal({ isOpen, onClose, onSelectRoute }) {
    const [announcements, setAnnouncements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filterCategory, setFilterCategory] = useState("All");
    const [searchQuery, setSearchQuery] = useState("");

    useEffect(() => {
        if (!isOpen) return;
        const fetchAll = async () => {
            setLoading(true);
            try {
                const data = await API.request("/api/announcements/all");
                setAnnouncements(Array.isArray(data) ? data : []);
            } catch (err) {
                console.error("Failed to load all announcements:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAll();
    }, [isOpen]);

    if (!isOpen) return null;

    const categories = ["All", "Scholarship", "Academic", "Infrastructure", "Career / Placement", "General Notice"];

    // Keyword matchers so filters work with whatever category names the backend uses
    const categoryKeywords = {
        "Scholarship": ["scholarship"],
        "Academic": ["academic", "exam"],
        "Infrastructure": ["infra", "substation"],
        "Career / Placement": ["placement", "career"],
        "General Notice": ["general", "notice"],
    };

    const filtered = announcements.filter((item) => {
        const cat = (item.category || "").toLowerCase();
        const keywords = categoryKeywords[filterCategory] || [];
        const matchesCat = filterCategory === "All" || keywords.some((k) => cat.includes(k));
        const q = (searchQuery || "").trim().toLowerCase();
        const matchesQuery = !q || (item.title || "").toLowerCase().includes(q) || (item.message || "").toLowerCase().includes(q);
        return matchesCat && matchesQuery;
    });

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-slate-200">
                {/* Header */}
                <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
                    <div className="flex items-center gap-3">
                        <span className="bg-red-600 text-white text-xs font-extrabold px-2.5 py-1 rounded uppercase tracking-wider">
                            UPDATES
                        </span>
                        <div>
                            <h2 className="text-lg font-bold">Official Campus Notices & Bulletins</h2>
                            <p className="text-xs text-slate-400">The National Institute of Engineering (NIE), Mysuru</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 text-2xl font-bold leading-none"
                        title="Close modal"
                    >
                        &times;
                    </button>
                </div>

                {/* Filters & Search */}
                <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap gap-1.5">
                        {categories.map((c) => (
                            <button
                                key={c}
                                onClick={() => setFilterCategory(c)}
                                className={`text-xs px-3 py-1.5 rounded-full font-medium transition ${filterCategory === c
                                    ? "bg-slate-900 text-white shadow-sm"
                                    : "bg-white text-slate-700 border border-slate-300 hover:bg-slate-100"
                                    }`}
                            >
                                {c}
                            </button>
                        ))}
                    </div>
                    <div className="w-full sm:w-64">
                        <input
                            type="text"
                            placeholder="Search notices..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full text-xs px-3 py-1.5 border border-slate-300 rounded-lg focus:ring-1 focus:ring-nie-navy focus:outline-none"
                        />
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto space-y-4 flex-1">
                    {loading ? (
                        <div className="py-12 text-center text-slate-500 text-sm">
                            <div className="w-8 h-8 border-2 border-nie-navy border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                            Loading bulletins...
                        </div>
                    ) : filtered.length === 0 ? (
                        <div className="py-12 text-center text-slate-500 text-sm">
                            No announcements match the selected filter.
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {filtered.map((item, idx) => (
                                <div
                                    key={item.id || idx}
                                    className="p-4 rounded-lg border border-slate-200 bg-white hover:border-amber-400 hover:shadow-md transition flex flex-col justify-between"
                                >
                                    <div>
                                        <div className="flex items-center justify-between gap-2 mb-2">
                                            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                                                {item.category}
                                            </span>
                                            <span className="text-[11px] text-slate-400 font-mono">
                                                {item.publication_date} {item.publication_time}
                                            </span>
                                        </div>
                                        <h3 className="font-semibold text-slate-900 text-sm mb-1.5 flex items-center gap-1.5">
                                            {item.is_urgent && (
                                                <span className="bg-red-600 text-white text-[9px] font-bold px-1.5 py-0.5 rounded uppercase">
                                                    Urgent
                                                </span>
                                            )}
                                            {item.title}
                                        </h3>
                                        <p className="text-xs text-slate-600 mb-3 leading-relaxed">
                                            {item.message}
                                        </p>
                                    </div>
                                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                                        <span className="text-[10px] text-slate-400">
                                            Priority: <strong className="text-slate-700">{item.priority}</strong>
                                        </span>
                                        {item.destination_route && (
                                            <button
                                                onClick={() => {
                                                    onClose();
                                                    if (onSelectRoute) onSelectRoute(item.destination_route);
                                                }}
                                                className="text-xs text-amber-700 hover:text-amber-800 font-semibold flex items-center gap-1"
                                            >
                                                <span>Go to {item.destination_route.charAt(0).toUpperCase() + item.destination_route.slice(1)}</span>
                                                <span>&rarr;</span>
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-between items-center text-xs text-slate-500">
                    <span>Displaying {filtered.length} active institutional announcements</span>
                    <button
                        onClick={onClose}
                        className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 text-white font-medium"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}

// DYNAMIC NEWS TICKER COMPONENT
function NewsTicker({ user, setView }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isAllUpdatesOpen, setIsAllUpdatesOpen] = useState(false);
    const [activeDetailItem, setActiveDetailItem] = useState(null);

    const loadTicker = async () => {
        try {
            const data = await API.request("/api/announcements/ticker?limit=15");
            if (Array.isArray(data) && data.length > 0) {
                setItems(data);
            }
        } catch (err) {
            console.error("Failed to load ticker announcements:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadTicker();
        // Periodically refresh ticker announcements every 60s
        const timer = setInterval(loadTicker, 60000);
        return () => clearInterval(timer);
    }, []);

    const handleItemClick = (item) => {
        if (item.destination_route && setView) {
            setView(item.destination_route);
        } else {
            setActiveDetailItem(item);
        }
    };

    const getCategoryClass = (cat) => {
        const c = (cat || "").toLowerCase();
        if (c.includes("scholarship")) return "ticker-category-scholarship";
        if (c.includes("academic") || c.includes("exam")) return "ticker-category-academic";
        if (c.includes("infra") || c.includes("substation")) return "ticker-category-infrastructure";
        if (c.includes("placement") || c.includes("career")) return "ticker-category-career";
        return "ticker-category-general";
    };

    const renderTickerItems = (list, keyPrefix) => {
        return list.map((item, idx) => (
            <div
                key={`${keyPrefix}-${item.id || idx}`}
                className="ticker-item"
                onClick={() => handleItemClick(item)}
                title="Click to view full details or navigate"
            >
                {item.is_urgent && (
                    <span className="ticker-urgent-pill">URGENT</span>
                )}
                <span className={`ticker-category-tag ${getCategoryClass(item.category)}`}>
                    {item.category}
                </span>
                <span className="ticker-time">
                    [{item.publication_date} {item.publication_time}]
                </span>
                <span className="ticker-title">{item.title}</span>
                <span className="ticker-msg"> &bull; {item.message}</span>
                <span className="ticker-separator">&bull;</span>
            </div>
        ));
    };

    if (items.length === 0 && !loading) {
        return null;
    }

    return (
        <React.Fragment>
            <div className="news-ticker-bar" role="region" aria-label="Campus Updates & Announcements">
                {/* Left Badge: UPDATES */}
                <div className="ticker-badge-left">
                    <span className="ticker-badge-label">
                        <span className="pulse-dot"></span>
                        UPDATES
                    </span>
                </div>

                {/* Central Continuously Moving Viewport */}
                <div className="ticker-scroll-viewport">
                    <div className="ticker-track">
                        {renderTickerItems(items, "trackA")}
                        {/* Identical sibling copy for seamless 0-gap infinite loop */}
                        {renderTickerItems(items, "trackB")}
                    </div>
                </div>

                {/* Right Button: ALL UPDATES */}
                <div className="ticker-view-all-right">
                    <button
                        onClick={() => setIsAllUpdatesOpen(true)}
                        className="ticker-view-all-btn"
                        title="Open all announcements"
                    >
                        <span>ALL UPDATES</span>
                        <span>&rarr;</span>
                    </button>
                </div>
            </div>

            {/* Modal for All Updates */}
            <AllUpdatesModal
                isOpen={isAllUpdatesOpen}
                onClose={() => setIsAllUpdatesOpen(false)}
                onSelectRoute={(route) => {
                    if (setView) setView(route);
                }}
            />

            {/* Quick Detail Modal for clicked announcement */}
            {activeDetailItem && (
                <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 border border-slate-200">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                                {activeDetailItem.category}
                            </span>
                            <span className="text-xs text-slate-400 font-mono">
                                {activeDetailItem.publication_date} {activeDetailItem.publication_time}
                            </span>
                        </div>
                        <h3 className="text-base font-bold text-slate-900 mb-2">
                            {activeDetailItem.title}
                        </h3>
                        <p className="text-sm text-slate-600 mb-4 leading-relaxed">
                            {activeDetailItem.message}
                        </p>
                        <div className="flex justify-between items-center pt-3 border-t border-slate-100">
                            {activeDetailItem.destination_route && setView ? (
                                <button
                                    onClick={() => {
                                        const route = activeDetailItem.destination_route;
                                        setActiveDetailItem(null);
                                        setView(route);
                                    }}
                                    className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-semibold"
                                >
                                    Go to {activeDetailItem.destination_route.charAt(0).toUpperCase() + activeDetailItem.destination_route.slice(1)} &rarr;
                                </button>
                            ) : <div></div>}
                            <button
                                onClick={() => setActiveDetailItem(null)}
                                className="px-4 py-1.5 rounded-lg bg-slate-800 text-white text-xs font-semibold hover:bg-slate-900"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </React.Fragment>
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

    const removeToast = (id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    };

    // Add toast
    const addToast = (message, type = "success", title = null) => {
        const id = Date.now() + Math.random();
        setToasts((prev) => [...prev, { id, message, type, title }]);
        setTimeout(() => removeToast(id), 5000);
    };

    // Load notifications
    const loadNotifications = () => {
        API.request("/api/notifications")
            .then((data) => {
                setNotifications(data.notifications || []);
                setUnreadNotifCount(data.unread_count || 0);
            })
            .catch(() => { });
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

    // Refresh notifications periodically while logged in
    useEffect(() => {
        if (!user) return;
        const timer = setInterval(loadNotifications, 60000);
        return () => clearInterval(timer);
    }, [user]);

    const handleLogout = () => {
        localStorage.removeItem("nieresolve_token");
        localStorage.removeItem("nieresolve_user");
        setUser(null);
        setView("dashboard");
        setSelectedComplaintId(null);
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
            <React.Fragment>
                <LoginPage
                    onLogin={(userData, token) => {
                        localStorage.setItem("nieresolve_token", token);
                        setUser(userData);
                        addToast(`Welcome back, ${userData.full_name}!`, "success");
                        loadNotifications();
                    }}
                    addToast={addToast}
                />
                <ToastContainer toasts={toasts} removeToast={removeToast} />
            </React.Fragment>
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
                    {user.role === "scholarship_coordinator" ? (
                        <button
                            onClick={() => { setView("scholarships"); setSelectedComplaintId(null); }}
                            className="px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap flex items-center gap-1.5 bg-nie-navy text-white"
                        >
                            <span>🎓 Scholarship Management & Portal</span>
                            <span className="bg-nie-gold text-white text-[9px] font-bold px-1.5 py-px rounded-full">Active</span>
                        </button>
                    ) : (
                        <React.Fragment>
                            <button
                                onClick={() => { setView("dashboard"); setSelectedComplaintId(null); }}
                                className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${view === "dashboard" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"}`}
                            >
                                Dashboard
                            </button>

                            <button
                                onClick={() => { setView("community"); setSelectedComplaintId(null); }}
                                className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap flex items-center gap-1.5 ${view === "community" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"}`}
                            >
                                <span>🏛️ Community Grievances</span>
                                <span className={`text-[9px] px-1.5 py-px rounded-full font-bold ${view === "community" ? "bg-nie-gold text-white" : "bg-blue-100 text-blue-800"}`}>
                                    14 Categories
                                </span>
                            </button>

                            {(user.role === "student" || user.role === "faculty") && (
                                <button
                                    onClick={() => { setView("submit"); setSelectedComplaintId(null); }}
                                    className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap flex items-center gap-1 ${view === "submit" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"}`}
                                >
                                    <span>+ Raise Grievance</span>
                                </button>
                            )}

                            {(user.role === "student" || user.can_publish_scholarships || user.role === "super_admin") && (
                                <button
                                    onClick={() => { setView("scholarships"); setSelectedComplaintId(null); }}
                                    className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap flex items-center gap-1.5 ${view === "scholarships" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"}`}
                                >
                                    <span>🎓 Scholarships & Aid</span>
                                    <span className="bg-nie-gold text-white text-[9px] font-bold px-1.5 py-px rounded-full">Active</span>
                                </button>
                            )}

                            {["dept_officer", "grievance_cell", "principal", "super_admin"].includes(user.role) && (
                                <React.Fragment>
                                    <button
                                        onClick={() => { setView("escalations"); setSelectedComplaintId(null); }}
                                        className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${view === "escalations" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"}`}
                                    >
                                        15-Day Escalation Matrix
                                    </button>
                                    <button
                                        onClick={() => { setView("analytics"); setSelectedComplaintId(null); }}
                                        className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${view === "analytics" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"}`}
                                    >
                                        Institutional Analytics
                                    </button>
                                </React.Fragment>
                            )}

                            {user.role === "super_admin" && (
                                <button
                                    onClick={() => { setView("admin"); setSelectedComplaintId(null); }}
                                    className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${view === "admin" ? "bg-nie-navy text-white" : "text-slate-600 hover:bg-slate-100"}`}
                                >
                                    System Administration
                                </button>
                            )}
                        </React.Fragment>
                    )}
                </div>
            </nav>

            {/* Main Content Area */}
            <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
                {user.role === "scholarship_coordinator" ? (
                    <ScholarshipPortal currentUser={user} addToast={addToast} />
                ) : selectedComplaintId ? (
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
                        setView={setView}
                    />
                ) : view === "community" ? (
                    <CommunityGrievancesView
                        currentUser={user}
                        onSelectComplaint={(id) => setSelectedComplaintId(id)}
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
    const [loginType, setLoginType] = useState("student"); // student, faculty, admin, register
    const [studentAuthMode, setStudentAuthMode] = useState("password"); // "password", "setup", "mfa"
    const [usn, setUsn] = useState("");
    const [studentPassword, setStudentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [fullName, setFullName] = useState("");
    const [dob, setDob] = useState("");
    const [parentPhoneLast4, setParentPhoneLast4] = useState("");
    const [facultyId, setFacultyId] = useState("");
    const [facultyDob, setFacultyDob] = useState("");
    const [adminUsername, setAdminUsername] = useState("");
    const [adminPassword, setAdminPassword] = useState("");
    const [submitting, setSubmitting] = useState(false);

    // Registration state
    const [regFullName, setRegFullName] = useState("");
    const [regEmail, setRegEmail] = useState("");
    const [regUsn, setRegUsn] = useState("");
    const [regBranch, setRegBranch] = useState("Computer Science & Engineering");
    const [regPhone, setRegPhone] = useState("");
    const [regDob, setRegDob] = useState("");
    const [regPassword, setRegPassword] = useState("");
    const [regConfirmPassword, setRegConfirmPassword] = useState("");

    const buildUser = (data) => ({
        id: data.user_id,
        full_name: data.full_name,
        email: data.email,
        role: data.role,
        identifier: data.identifier,
        department_name: data.department_name,
        can_publish_scholarships: data.can_publish_scholarships || false,
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            if (loginType === "register") {
                if (regPassword !== regConfirmPassword) {
                    addToast("Passwords do not match. Please verify your password confirmation.", "error");
                    setSubmitting(false);
                    return;
                }
                if (regPassword.length < 6) {
                    addToast("Password must be at least 6 characters long.", "error");
                    setSubmitting(false);
                    return;
                }
                const regPayload = {
                    full_name: regFullName.trim(),
                    email: regEmail.trim(),
                    usn: regUsn.trim().toUpperCase(),
                    branch: regBranch,
                    password: regPassword,
                    phone: regPhone.trim() || null,
                    dob: regDob || null,
                    role: "student",
                };
                const regRes = await API.request("/api/auth/register", {
                    method: "POST",
                    body: JSON.stringify(regPayload),
                });
                addToast(regRes.message || "Account created successfully!", "success");
                if (regRes.access_token) {
                    onLogin(buildUser(regRes), regRes.access_token);
                } else {
                    setUsn(regUsn.trim().toUpperCase());
                    setStudentPassword(regPassword);
                    setLoginType("student");
                    setStudentAuthMode("password");
                }
                return;
            } else if (loginType === "student") {
                if (studentAuthMode === "setup") {
                    const res = await API.request("/api/auth/student-setup-password", {
                        method: "POST",
                        body: JSON.stringify({
                            usn: usn.trim(),
                            full_name: fullName.trim(),
                            dob: dob.trim(),
                            parent_phone_last4: parentPhoneLast4.trim(),
                            new_password: newPassword,
                        }),
                    });
                    addToast(res.message || "Password successfully created! You can now sign in.", "success");
                    setStudentPassword(newPassword);
                    setStudentAuthMode("password");
                    return;
                }

                let payload = { usn: usn.trim() };
                if (studentAuthMode === "password") {
                    payload.password = studentPassword;
                } else {
                    payload.full_name = fullName.trim();
                    payload.dob = dob.trim();
                    payload.parent_phone_last4 = parentPhoneLast4.trim();
                }

                const data = await API.request("/api/auth/student-login", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });

                onLogin(buildUser(data), data.access_token);
            } else if (loginType === "faculty") {
                const data = await API.request("/api/auth/faculty-login", {
                    method: "POST",
                    body: JSON.stringify({ faculty_id: facultyId.trim(), dob: facultyDob.trim() }),
                });
                onLogin(buildUser(data), data.access_token);
            } else {
                const data = await API.request("/api/auth/admin-login", {
                    method: "POST",
                    body: JSON.stringify({ username_or_email: adminUsername.trim(), password: adminPassword }),
                });
                onLogin(buildUser(data), data.access_token);
            }
        } catch (err) {
            addToast(err.message, "error");
        } finally {
            setSubmitting(false);
        }
    };

    // Quick fill helper for demonstration testing
    const fillDemo = (type, ident, secret, extraName = "", extraLast4 = "") => {
        setLoginType(type);
        if (type === "student") {
            setUsn(ident);
            setStudentPassword(secret);
            setDob(secret);
            setFullName(extraName);
            setParentPhoneLast4(extraLast4);
            setStudentAuthMode("password");
        } else if (type === "faculty") {
            setFacultyId(ident);
            setFacultyDob(secret);
        } else {
            setAdminUsername(ident);
            setAdminPassword(secret);
        }
    };

    return (
        <div className="min-h-screen bg-slate-100 flex flex-col justify-between">
            <div className="flex-1 flex flex-col justify-center py-10 sm:px-6 lg:px-8">
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
                            {[
                                { key: "student", label: "Student" },
                                { key: "faculty", label: "Faculty" },
                                { key: "admin", label: "Officer / Admin" },
                                { key: "register", label: "Register" },
                            ].map((t) => (
                                <button
                                    key={t.key}
                                    type="button"
                                    onClick={() => setLoginType(t.key)}
                                    className={`flex-1 py-2 text-xs font-semibold border-b-2 text-center transition ${loginType === t.key
                                        ? (t.key === "register" ? "border-nie-gold text-nie-gold font-bold" : "border-nie-navy text-nie-navy font-bold")
                                        : "border-transparent text-slate-500 hover:text-slate-700"
                                        }`}
                                >
                                    {t.label}
                                </button>
                            ))}
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            {loginType === "register" && (
                                <div className="space-y-3">
                                    <div className="bg-amber-50 border border-amber-200 p-2.5 rounded-lg text-xs text-amber-900 flex items-center justify-between">
                                        <span><strong>Student Registration Portal:</strong> Create your institutional account to register grievances and track redressal.</span>
                                        <button
                                            type="button"
                                            onClick={() => setLoginType("student")}
                                            className="text-[11px] text-amber-800 underline font-semibold ml-2 whitespace-nowrap"
                                        >
                                            Sign In
                                        </button>
                                    </div>

                                    <div>
                                        <label className="block text-xs font-semibold text-slate-700">Full Name *</label>
                                        <input
                                            type="text"
                                            required
                                            placeholder="e.g. Vikram Gowda"
                                            value={regFullName}
                                            onChange={(e) => setRegFullName(e.target.value)}
                                            className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-xs font-semibold text-slate-700">Institutional Email Address *</label>
                                        <input
                                            type="email"
                                            required
                                            placeholder="e.g. 4ni22cs101@nie.ac.in"
                                            value={regEmail}
                                            onChange={(e) => setRegEmail(e.target.value)}
                                            className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div>
                                            <label className="block text-xs font-semibold text-slate-700">University Seat Number (USN) *</label>
                                            <input
                                                type="text"
                                                required
                                                placeholder="e.g. 4NI22CS101"
                                                value={regUsn}
                                                onChange={(e) => setRegUsn(e.target.value.toUpperCase())}
                                                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm uppercase placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy font-mono"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-xs font-semibold text-slate-700">Department / Branch *</label>
                                            <select
                                                value={regBranch}
                                                onChange={(e) => setRegBranch(e.target.value)}
                                                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                            >
                                                <option value="Computer Science & Engineering">Computer Science & Engineering</option>
                                                <option value="Information Science & Engineering">Information Science & Engineering</option>
                                                <option value="Electronics & Communication Engineering">Electronics & Communication</option>
                                                <option value="Electrical & Electronics Engineering">Electrical & Electronics</option>
                                                <option value="Mechanical Engineering">Mechanical Engineering</option>
                                                <option value="Civil Engineering">Civil Engineering</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div>
                                            <label className="block text-xs font-semibold text-slate-700">Mobile Phone</label>
                                            <input
                                                type="tel"
                                                placeholder="e.g. 9876543210"
                                                value={regPhone}
                                                onChange={(e) => setRegPhone(e.target.value)}
                                                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-xs font-semibold text-slate-700">Date of Birth (DOB)</label>
                                            <input
                                                type="date"
                                                value={regDob}
                                                onChange={(e) => setRegDob(e.target.value)}
                                                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div>
                                            <label className="block text-xs font-semibold text-slate-700">Create Password (min 6 chars) *</label>
                                            <input
                                                type="password"
                                                required
                                                minLength="6"
                                                placeholder="••••••••"
                                                value={regPassword}
                                                onChange={(e) => setRegPassword(e.target.value)}
                                                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                            />
                                        </div>

                                        <div>
                                            <label className="block text-xs font-semibold text-slate-700">Confirm Password *</label>
                                            <input
                                                type="password"
                                                required
                                                minLength="6"
                                                placeholder="••••••••"
                                                value={regConfirmPassword}
                                                onChange={(e) => setRegConfirmPassword(e.target.value)}
                                                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}
                            {loginType === "student" && (
                                <>
                                    {studentAuthMode === "password" && (
                                        <>
                                            <div>
                                                <label className="block text-xs font-semibold text-slate-700">University Seat Number (USN) *</label>
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
                                                <label className="block text-xs font-semibold text-slate-700">Password *</label>
                                                <input
                                                    type="password"
                                                    required
                                                    placeholder="Enter your student password"
                                                    value={studentPassword}
                                                    onChange={(e) => setStudentPassword(e.target.value)}
                                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                                />
                                            </div>
                                            <div className="flex justify-between items-center text-[11px] pt-1">
                                                <button
                                                    type="button"
                                                    onClick={() => setStudentAuthMode("setup")}
                                                    className="text-nie-navy font-semibold hover:underline"
                                                >
                                                    First-Time Setup / Reset Password
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => setStudentAuthMode("mfa")}
                                                    className="text-slate-500 hover:text-slate-700"
                                                >
                                                    Use 4-Factor Identity
                                                </button>
                                            </div>
                                        </>
                                    )}

                                    {studentAuthMode === "setup" && (
                                        <div className="space-y-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                                            <div className="flex justify-between items-center border-b pb-2">
                                                <h3 className="text-xs font-bold text-nie-navy">First-Time Student Password Setup</h3>
                                                <button
                                                    type="button"
                                                    onClick={() => setStudentAuthMode("password")}
                                                    className="text-[11px] text-slate-500 hover:underline"
                                                >
                                                    Back to Sign In
                                                </button>
                                            </div>
                                            <div>
                                                <label className="block text-[11px] font-semibold text-slate-700">University Seat Number (USN) *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    placeholder="e.g. 4NI21CS045"
                                                    value={usn}
                                                    onChange={(e) => setUsn(e.target.value)}
                                                    className="mt-0.5 block w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs uppercase"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-[11px] font-semibold text-slate-700">Full Name (as registered) *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    placeholder="e.g. Ananya Sharma"
                                                    value={fullName}
                                                    onChange={(e) => setFullName(e.target.value)}
                                                    className="mt-0.5 block w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-[11px] font-semibold text-slate-700">Date of Birth (DOB) *</label>
                                                <input
                                                    type="date"
                                                    required
                                                    value={dob}
                                                    onChange={(e) => setDob(e.target.value)}
                                                    className="mt-0.5 block w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-[11px] font-semibold text-slate-700">Guardian Mobile (Last 4 Digits) *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    maxLength="4"
                                                    placeholder="e.g. 3456"
                                                    value={parentPhoneLast4}
                                                    onChange={(e) => setParentPhoneLast4(e.target.value.replace(/\D/g, ''))}
                                                    className="mt-0.5 block w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-mono"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-[11px] font-semibold text-slate-700">Create New Personal Password (min 6 chars) *</label>
                                                <input
                                                    type="password"
                                                    required
                                                    minLength="6"
                                                    placeholder="Choose a strong password"
                                                    value={newPassword}
                                                    onChange={(e) => setNewPassword(e.target.value)}
                                                    className="mt-0.5 block w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {studentAuthMode === "mfa" && (
                                        <>
                                            <div>
                                                <label className="block text-xs font-semibold text-slate-700">University Seat Number (USN) *</label>
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
                                                <label className="block text-xs font-semibold text-slate-700">Full Name (as per NIE Records) *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    placeholder="e.g. Ananya Sharma"
                                                    value={fullName}
                                                    onChange={(e) => setFullName(e.target.value)}
                                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-semibold text-slate-700">Date of Birth (DOB) *</label>
                                                <input
                                                    type="date"
                                                    required
                                                    value={dob}
                                                    onChange={(e) => setDob(e.target.value)}
                                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-semibold text-slate-700">Parent / Guardian Mobile (Last 4 Digits) *</label>
                                                <input
                                                    type="text"
                                                    required
                                                    maxLength="4"
                                                    placeholder="e.g. 3456"
                                                    value={parentPhoneLast4}
                                                    onChange={(e) => setParentPhoneLast4(e.target.value.replace(/\D/g, ''))}
                                                    className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-nie-navy"
                                                />
                                            </div>
                                            <div className="pt-1">
                                                <button
                                                    type="button"
                                                    onClick={() => setStudentAuthMode("password")}
                                                    className="text-[11px] text-nie-navy font-semibold hover:underline"
                                                >
                                                    &larr; Return to Standard Password Login
                                                </button>
                                            </div>
                                        </>
                                    )}
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
                                {submitting
                                    ? (loginType === "register" ? "Registering Account..." : "Authenticating...")
                                    : (loginType === "register"
                                        ? "Register & Sign In to NIEresolve"
                                        : `Sign In as ${loginType === "student" ? "Student" : loginType === "faculty" ? "Faculty" : "Authorized Officer"}`)
                                }
                            </button>
                            {loginType !== "register" ? (
                                <div className="mt-3 text-center">
                                    <p className="text-xs text-slate-600">
                                        First-time student without an account?{" "}
                                        <button
                                            type="button"
                                            onClick={() => setLoginType("register")}
                                            className="text-nie-gold font-bold hover:underline"
                                        >
                                            Register New Account &rarr;
                                        </button>
                                    </p>
                                </div>
                            ) : (
                                <div className="mt-3 text-center">
                                    <p className="text-xs text-slate-600">
                                        Already registered?{" "}
                                        <button
                                            type="button"
                                            onClick={() => setLoginType("student")}
                                            className="text-nie-navy font-bold hover:underline"
                                        >
                                            &larr; Return to Sign In
                                        </button>
                                    </p>
                                </div>
                            )}
                        </form>

                        {/* Pre-configured Demo Accounts Helper (REMOVE before real deployment) */}
                        <div className="mt-6 pt-5 border-t border-slate-200">
                            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider text-center mb-2.5">
                                Quick Demo Sign-In Credentials
                            </p>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                                <button
                                    type="button"
                                    onClick={() => fillDemo("student", "4NI21CS045", "NewStudentPassword@2026", "Ananya Sharma", "3456")}
                                    className="p-2 border border-slate-200 rounded-md hover:bg-slate-50 text-left transition"
                                >
                                    <div className="font-semibold text-nie-navy">Student: Ananya</div>
                                    <div className="text-[10px] text-slate-500 font-mono">USN: 4NI21CS045</div>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => fillDemo("student", "4NI21CS088", "2003-11-22", "Rahul Verma", "7654")}
                                    className="p-2 border border-slate-200 rounded-md hover:bg-slate-50 text-left transition"
                                >
                                    <div className="font-semibold text-nie-navy">Student: Rahul</div>
                                    <div className="text-[10px] text-slate-500 font-mono">4NI21CS088 &bull; 7654</div>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => fillDemo("admin", "coordinator.scholarships@nie.ac.in", "Scholarship@123")}
                                    className="p-2 border border-amber-200 bg-amber-50/60 rounded-md hover:bg-amber-100 text-left transition"
                                >
                                    <div className="font-semibold text-nie-navy flex items-center justify-between">
                                        <span>Coordinator</span>
                                        <span className="text-[8px] bg-amber-600 text-white px-1 rounded">Aid</span>
                                    </div>
                                    <div className="text-[10px] text-slate-600 font-mono">Scholarship Dept</div>
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

                {/* Institutional Pre-login Footer */}
                <div className="py-3 text-center text-[11px] text-slate-400">
                    &copy; {new Date().getFullYear()} The National Institute of Engineering, Mysuru &bull; Grievance Redressal Cell
                </div>
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// ROLE-BASED DASHBOARD ROUTER
// ----------------------------------------------------------------------
function RoleDashboard({ user, onSelectComplaint, onNewComplaint, addToast, setView }) {
    if (user.role === "scholarship_coordinator") {
        return (
            <div className="space-y-6">
                <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-xl font-bold text-nie-navy">
                            Scholarship Coordinator Portal
                        </h1>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Logged in as <strong className="text-slate-700">{user.full_name}</strong> &bull; {user.email} &bull; Institutional Scholarships & Financial Aid
                        </p>
                    </div>
                </div>
                <ScholarshipPortal currentUser={user} addToast={addToast} />
            </div>
        );
    }

    const [complaints, setComplaints] = useState([]);
    const [groupedComplaints, setGroupedComplaints] = useState([]);
    const [viewMode, setViewMode] = useState("grouped"); // "grouped" or "flat"
    const [collapsedGroups, setCollapsedGroups] = useState({});
    const [loading, setLoading] = useState(true);
    const [filterCategory, setFilterCategory] = useState("");
    const [filterPriority, setFilterPriority] = useState("");
    const [filterStatus, setFilterStatus] = useState("");
    const [filterCampus, setFilterCampus] = useState("");

    const toggleGroup = (groupId) => {
        setCollapsedGroups((prev) => ({ ...prev, [groupId]: !prev[groupId] }));
    };

    const loadComplaints = () => {
        setLoading(true);
        const params = new URLSearchParams();
        if (filterCategory) params.append("category", filterCategory);
        if (filterPriority) params.append("priority", filterPriority);
        if (filterStatus) params.append("status", filterStatus);
        if (filterCampus) params.append("campus", filterCampus);
        const queryStr = params.toString() ? `?${params.toString()}` : "";

        Promise.all([
            API.request(`/api/complaints${queryStr}`),
            API.request(`/api/complaints/grouped${queryStr}`).catch(() => []),
        ])
            .then(([flatData, groupedData]) => {
                setComplaints(flatData);
                setGroupedComplaints(groupedData);
            })
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadComplaints();
    }, [filterCategory, filterPriority, filterStatus, filterCampus]);

    // Compute Metrics
    const total = complaints.length;
    const pending = complaints.filter((c) => !["resolved", "closed", "confirmed_resolved", "auto_confirmed_resolved"].includes(c.status)).length;
    const investigating = complaints.filter((c) => c.status === "under_investigation").length;
    const resolved = complaints.filter((c) => ["resolved", "closed", "confirmed_resolved", "auto_confirmed_resolved"].includes(c.status)).length;
    const escalated = complaints.filter((c) => ["tier_2", "tier_3"].includes(c.current_tier)).length;
    const totalAffected = complaints.reduce((sum, c) => sum + (c.affected_students_count || 1), 0);

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

            {/* Dynamic News Ticker — Exclusively on Student Dashboard, Placed Cleanly Below Welcome Banner */}
            {user.role === "student" && (
                <div className="rounded-xl overflow-hidden shadow-sm border border-slate-800">
                    <NewsTicker user={user} setView={setView} />
                </div>
            )}

            {/* Metrics Overview Cards */}
            <div className={`grid grid-cols-2 ${user.role !== "student" && user.role !== "faculty" ? "sm:grid-cols-6" : "sm:grid-cols-5"} gap-3`}>
                <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs text-slate-500 font-medium">Total Grievances</p>
                    <p className="text-2xl font-bold text-nie-navy mt-1">{total}</p>
                </div>
                {user.role !== "student" && user.role !== "faculty" && (
                    <div className="bg-white p-4 rounded-xl border border-blue-200 shadow-sm">
                        <p className="text-xs text-blue-700 font-medium">Affected Students</p>
                        <p className="text-2xl font-bold text-blue-800 mt-1">{totalAffected}</p>
                    </div>
                )}
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
                    value={filterCategory}
                    onChange={(e) => setFilterCategory(e.target.value)}
                    className="border border-slate-200 rounded px-2 py-1 text-slate-700 focus:outline-none"
                >
                    <option value="">All Categories</option>
                    <option value="Placement and Career Services">💼 Placement & Career</option>
                    <option value="Infrastructure and Maintenance">🔧 Infrastructure & Maintenance</option>
                    <option value="Hostel and Accommodation">🛏️ Hostel & Accommodation</option>
                    <option value="Transportation">🚌 Transportation</option>
                    <option value="Academic and Curriculum">📚 Academic & Curriculum</option>
                    <option value="Examination and Results">📝 Examination & Results</option>
                    <option value="Faculty-related Issues">👨‍🏫 Faculty-related Issues</option>
                    <option value="Library and Information Resources">📖 Library & Information</option>
                    <option value="Laboratory and Equipment">🔬 Laboratory & Equipment</option>
                    <option value="Scholarship and Financial Aid">🎓 Scholarship & Aid</option>
                    <option value="Fees and Finance">💳 Fees & Finance</option>
                    <option value="Campus Safety and Security">🛡️ Safety & Security</option>
                    <option value="IT and Network Services">🌐 IT & Network</option>
                    <option value="Other Institutional Concerns">🏛️ Other Concerns</option>
                </select>

                <select
                    value={filterCampus}
                    onChange={(e) => setFilterCampus(e.target.value)}
                    className="border border-slate-200 rounded px-2 py-1 text-slate-700 focus:outline-none font-medium"
                >
                    <option value="">All Campuses</option>
                    <option value="North Campus">🏢 North Campus</option>
                    <option value="South Campus">🏛️ South Campus</option>
                </select>

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
                    <option value="resolved_awaiting_confirmation">Awaiting Student Confirmation</option>
                    <option value="confirmed_resolved">Confirmed Resolved</option>
                    <option value="reopened">Reopened</option>
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
                    onClick={() => { setFilterCategory(""); setFilterPriority(""); setFilterStatus(""); setFilterCampus(""); }}
                    className="text-nie-navy hover:underline text-xs ml-auto"
                >
                    Reset Filters
                </button>
            </div>

            {/* Complaints List Container with View Mode Toggle */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                        <h2 className="font-semibold text-sm text-slate-800">
                            {user.role === "student" ? "My Registered Grievances" : "Active Case Redressal Roster"}
                        </h2>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                            {viewMode === "grouped" ? "Organized into normalized smart issue clusters" : "Linear case roster with full audit metadata"}
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-0.5 text-xs font-semibold">
                            <button
                                type="button"
                                onClick={() => setViewMode("grouped")}
                                className={`px-2.5 py-1 rounded-md transition flex items-center gap-1.5 ${viewMode === "grouped" ? "bg-white text-nie-navy shadow-sm font-bold" : "text-slate-600 hover:text-slate-900"}`}
                            >
                                <span>🗂️ Smart Groups</span>
                                <span className="bg-nie-gold/20 text-nie-navydark text-[9px] px-1 rounded-full font-mono">{groupedComplaints.length}</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setViewMode("flat")}
                                className={`px-2.5 py-1 rounded-md transition flex items-center gap-1.5 ${viewMode === "flat" ? "bg-white text-nie-navy shadow-sm font-bold" : "text-slate-600 hover:text-slate-900"}`}
                            >
                                <span>📋 Flat Table</span>
                                <span className="text-slate-400 text-[9px] font-mono">({complaints.length})</span>
                            </button>
                        </div>
                    </div>
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
                ) : viewMode === "grouped" ? (
                    /* SMART GROUPED ACCORDION VIEW */
                    <div className="divide-y divide-slate-200">
                        {groupedComplaints.map((group) => {
                            const isCollapsed = collapsedGroups[group.group_id];
                            return (
                                <div key={group.group_id} className="transition">
                                    <div
                                        onClick={() => toggleGroup(group.group_id)}
                                        className="px-5 py-3.5 bg-slate-50/80 hover:bg-slate-100/90 cursor-pointer flex items-center justify-between transition select-none"
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className="text-2xl p-1 bg-white rounded-lg border border-slate-200 shadow-sm">{group.icon}</span>
                                            <div>
                                                <div className="font-bold text-sm text-slate-900 flex items-center gap-2">
                                                    <span>{group.group_name}</span>
                                                    <span className="text-xs font-semibold bg-nie-navy text-white px-2 py-0.5 rounded-full">
                                                        {group.total_count} {group.total_count === 1 ? "grievance" : "grievances"}
                                                    </span>
                                                </div>
                                                <div className="text-[11px] text-slate-500">{group.category}</div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-3">
                                            <div className="flex items-center gap-1.5 text-xs">
                                                <span className="bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded text-[11px]">
                                                    {group.pending_count} Pending
                                                </span>
                                                <span className="bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded text-[11px]">
                                                    {group.resolved_count} Resolved
                                                </span>
                                            </div>
                                            <span className="text-slate-400 font-bold text-xs p-1 bg-white rounded border border-slate-200">
                                                {isCollapsed ? "Expand ▼" : "Collapse ▲"}
                                            </span>
                                        </div>
                                    </div>

                                    {!isCollapsed && (
                                        <div className="p-3 bg-slate-50/30 overflow-x-auto">
                                            <table className="w-full text-left text-xs text-slate-600 bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
                                                <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                                                    <tr>
                                                        <th className="px-4 py-2.5">Grievance ID</th>
                                                        <th className="px-4 py-2.5">Title</th>
                                                        <th className="px-4 py-2.5">Campus</th>
                                                        <th className="px-4 py-2.5">Priority</th>
                                                        <th className="px-4 py-2.5">Level</th>
                                                        <th className="px-4 py-2.5">Status</th>
                                                        <th className="px-4 py-2.5 text-right">Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-100">
                                                    {group.complaints.map((c) => (
                                                        <tr key={c.id} className="hover:bg-slate-50/80 transition">
                                                            <td className="px-4 py-2.5 font-mono font-bold text-nie-navy">
                                                                {c.grievance_id}
                                                                {c.is_duplicate && (
                                                                    <span className="block text-[9px] text-amber-600 font-sans font-normal">
                                                                        Merged Duplicate
                                                                    </span>
                                                                )}
                                                                {c.affected_students_count > 1 && (
                                                                    <span className="inline-block mt-0.5 text-[9px] bg-blue-100 text-blue-800 font-sans font-bold px-1.5 py-0.5 rounded">
                                                                        👥 {c.affected_students_count} Affected
                                                                    </span>
                                                                )}
                                                            </td>
                                                            <td className="px-4 py-2.5 max-w-sm">
                                                                <div className="font-semibold text-slate-900 truncate">{c.title}</div>
                                                                <div className="text-[10px] text-slate-400">
                                                                    Submitted: {new Date(c.submission_date).toLocaleDateString()}
                                                                </div>
                                                            </td>
                                                            <td className="px-4 py-2.5">
                                                                <CampusBadge campus={c.campus} />
                                                            </td>
                                                            <td className="px-4 py-2.5">
                                                                <PriorityBadge priority={c.final_priority} />
                                                            </td>
                                                            <td className="px-4 py-2.5">
                                                                <TierBadge tier={c.current_tier} />
                                                            </td>
                                                            <td className="px-4 py-2.5">
                                                                <StatusBadge status={c.status} />
                                                            </td>
                                                            <td className="px-4 py-2.5 text-right">
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
                            );
                        })}
                    </div>
                ) : (
                    /* FLAT TABLE VIEW */
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs text-slate-600">
                            <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 uppercase tracking-wider text-[10px]">
                                <tr>
                                    <th className="px-4 py-3">Grievance ID</th>
                                    <th className="px-4 py-3">Title & Category</th>
                                    <th className="px-4 py-3">Campus</th>
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
                                            {c.affected_students_count > 1 && (
                                                <span className="inline-block mt-0.5 text-[9px] bg-blue-100 text-blue-800 font-sans font-bold px-1.5 py-0.5 rounded">
                                                    👥 {c.affected_students_count} Affected
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 max-w-xs">
                                            <div className="font-semibold text-slate-900 truncate">{c.title}</div>
                                            <div className="text-[11px] text-slate-500">{c.category}</div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <CampusBadge campus={c.campus} />
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
// SUBMIT COMPLAINT PAGE (Form, Evidence Upload & Duplicate Pre-check)
// ----------------------------------------------------------------------
function SubmitComplaintPage({ currentUser, onSuccess, onCancel, addToast }) {
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [category, setCategory] = useState("Infrastructure and Maintenance");
    const [campus, setCampus] = useState("North Campus");
    const [departmentId, setDepartmentId] = useState(""); // "" = Auto-Route by Category
    const [departments, setDepartments] = useState([]);
    const [locationName, setLocationName] = useState("");

    // Evidence file & confidentiality
    const [file, setFile] = useState(null);
    const [isConfidentialEvidence, setIsConfidentialEvidence] = useState(false);

    // Duplicate detection draft warning
    const [duplicateMatches, setDuplicateMatches] = useState([]);
    const [checkingDuplicates, setCheckingDuplicates] = useState(false);

    const [submitting, setSubmitting] = useState(false);

    // Load departments (default stays on "Auto-Route by Category")
    useEffect(() => {
        API.request("/api/admin/departments")
            .then((data) => setDepartments(data))
            .catch(() => { });
    }, []);

    // Pre-submission duplicate check debounce
    useEffect(() => {
        if (title.length < 5 || description.length < 15) {
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
                    department_id: departmentId ? parseInt(departmentId) : null,
                }),
            })
                .then((matches) => setDuplicateMatches(matches))
                .catch(() => { })
                .finally(() => setCheckingDuplicates(false));
        }, 800);

        return () => clearTimeout(timer);
    }, [title, description, category, departmentId]);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0] || null;
        if (selectedFile && selectedFile.size > 10 * 1024 * 1024) {
            addToast("Evidence file exceeds maximum permitted size of 10MB.", "warning");
            e.target.value = "";
            setFile(null);
            return;
        }
        setFile(selectedFile);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);

        let compRes;
        try {
            // 1. Create Complaint
            const compPayload = {
                title: title.trim(),
                description: description.trim(),
                category,
                campus,
                department_id: departmentId ? parseInt(departmentId) : null,
                location_name: locationName.trim() || null,
                is_confidential_evidence: isConfidentialEvidence,
            };

            compRes = await API.request("/api/complaints", {
                method: "POST",
                body: JSON.stringify(compPayload),
            });
        } catch (err) {
            addToast(err.message, "error");
            setSubmitting(false);
            return;
        }

        const complaintId = compRes.complaint_id;

        // 2. Upload Supporting Evidence if attached (failure must NOT cause a duplicate resubmission)
        if (file && complaintId) {
            try {
                const formData = new FormData();
                formData.append("file", file);
                formData.append("is_confidential", isConfidentialEvidence);
                await API.request(`/api/evidence/upload/${complaintId}`, {
                    method: "POST",
                    body: formData,
                });
            } catch (uploadErr) {
                addToast(
                    `Grievance was registered, but the evidence upload failed: ${uploadErr.message}. You can retry from the grievance page.`,
                    "warning",
                    "Evidence Upload Failed"
                );
            }
        }

        addToast(
            `Grievance registered with ID ${compRes.grievance_id}. Priority: ${compRes.final_priority}. SMS alert dispatched.`,
            "success",
            "Submitted Successfully"
        );
        setSubmitting(false);
        onSuccess(complaintId);
    };

    const officialCategories = [
        "Placement and Career Services",
        "Infrastructure and Maintenance",
        "Hostel and Accommodation",
        "Transportation",
        "Academic and Curriculum",
        "Examination and Results",
        "Faculty-related Issues",
        "Library",
        "Laboratory",
        "Scholarship and Financial Aid",
        "Fees and Administration",
        "Campus Safety",
        "IT and Network Issues",
        "Other",
    ];

    return (
        <div className="max-w-3xl mx-auto bg-white p-6 sm:p-8 rounded-xl border border-slate-200 shadow-sm">
            <div className="border-b border-slate-200 pb-4 mb-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-lg font-bold text-nie-navy">Lodge a Formal Grievance</h1>
                        <p className="text-xs text-slate-500 mt-1">
                            Logged under your verified institutional credential: <strong className="text-slate-700">{currentUser.full_name} ({currentUser.identifier || currentUser.email})</strong>
                        </p>
                    </div>
                    <span className="text-[11px] bg-nie-navy/10 text-nie-navy px-2.5 py-1 rounded-full font-semibold">
                        Automated 15-Day Escalation
                    </span>
                </div>
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

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-slate-700">Campus *</label>
                        <select
                            value={campus}
                            onChange={(e) => setCampus(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white font-semibold text-nie-navy focus:outline-none focus:ring-2 focus:ring-nie-navy"
                        >
                            <option value="North Campus">🏢 North Campus</option>
                            <option value="South Campus">🏛️ South Campus</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-700">Category *</label>
                        <select
                            value={category}
                            onChange={(e) => setCategory(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-nie-navy"
                        >
                            {officialCategories.map((cat) => (
                                <option key={cat} value={cat}>
                                    {cat}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-slate-700">Concerned Department</label>
                        <select
                            value={departmentId}
                            onChange={(e) => setDepartmentId(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-nie-navy"
                        >
                            <option value="">Auto-Route by Category</option>
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
                        placeholder="Please provide specific details: room numbers, dates, equipment involved, and any potential safety or academic implications..."
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

                {/* Supporting Photographic / Document Evidence Upload */}
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Supporting Photographic / Document Evidence (Optional)
                    </label>
                    <div className="mt-1 flex items-center gap-3">
                        <input
                            type="file"
                            accept=".jpg,.jpeg,.png,.webp,.pdf"
                            onChange={handleFileChange}
                            className="block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-nie-navy file:text-white hover:file:bg-nie-navydark"
                        />
                        {file && (
                            <button
                                type="button"
                                onClick={() => setFile(null)}
                                className="text-xs text-rose-600 hover:underline font-semibold whitespace-nowrap"
                            >
                                Remove
                            </button>
                        )}
                    </div>
                    {file && (
                        <div className="mt-2 text-xs text-slate-600 bg-white p-2 rounded border border-slate-200 flex items-center justify-between">
                            <span>📎 {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                            <span className="text-emerald-600 font-semibold text-[11px]">Ready to upload</span>
                        </div>
                    )}
                    <p className="text-[11px] text-slate-400 mt-1.5">Accepted formats: JPG, PNG, WEBP, PDF (Max 10MB). High-resolution photos are recommended for infrastructure concerns.</p>

                    <div className="mt-3 flex items-center gap-2 pt-2 border-t border-slate-200">
                        <input
                            type="checkbox"
                            id="confidentialEvidence"
                            checked={isConfidentialEvidence}
                            onChange={(e) => setIsConfidentialEvidence(e.target.checked)}
                            className="rounded border-slate-300 text-nie-navy focus:ring-nie-navy"
                        />
                        <label htmlFor="confidentialEvidence" className="text-xs text-slate-700">
                            <strong>Confidential Evidence:</strong> Restrict evidence visibility strictly to Authorized Officers (will not be visible to other students in community view).
                        </label>
                    </div>
                </div>

                {/* Duplicate Complaint Warning Notice */}
                {duplicateMatches.length > 0 && (
                    <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 text-xs">
                        <div className="flex items-center gap-1.5 font-bold text-amber-800 mb-1">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            Possible Existing Complaints Detected
                        </div>
                        <p className="text-amber-700 mb-2">
                            The following active complaints match your issue description. If this is the same problem, you can also support them directly in the Community Grievances tab:
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

    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [studentSatisfaction, setStudentSatisfaction] = useState(true);
    const [confirmRemarks, setConfirmRemarks] = useState("");

    // Internal Officer Messages
    const [internalMessages, setInternalMessages] = useState([]);
    const [newInternalMsg, setNewInternalMsg] = useState("");
    const [postingMsg, setPostingMsg] = useState(false);

    const isOfficer = ["dept_officer", "grievance_cell", "principal", "super_admin"].includes(currentUser.role);
    const canConfirmResolution = currentUser.role === "student";

    // silent = true refreshes data without showing the full-page spinner
    const loadDetails = (silent = false) => {
        if (!silent) setLoading(true);
        API.request(`/api/complaints/${complaintId}`)
            .then((data) => setComplaint(data))
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    };

    const loadInternalMessages = () => {
        if (!isOfficer) return;
        API.request(`/api/complaints/${complaintId}/internal-messages`)
            .then((data) => setInternalMessages(data))
            .catch(() => { });
    };

    const handlePostInternalMsg = async (e) => {
        e.preventDefault();
        if (!newInternalMsg.trim()) return;
        setPostingMsg(true);
        try {
            await API.request(`/api/complaints/${complaintId}/internal-messages`, {
                method: "POST",
                body: JSON.stringify({ message: newInternalMsg.trim() }),
            });
            setNewInternalMsg("");
            addToast("Internal discussion note posted.", "success");
            loadInternalMessages();
        } catch (err) {
            addToast(err.message, "error");
        } finally {
            setPostingMsg(false);
        }
    };

    const handleToggleUpvote = async () => {
        try {
            if (complaint.has_upvoted) {
                await API.request(`/api/complaints/${complaintId}/upvote`, { method: "DELETE" });
                addToast("Support vote removed.", "info");
            } else {
                await API.request(`/api/complaints/${complaintId}/upvote`, { method: "POST" });
                addToast("Support vote recorded. ML priority re-evaluated.", "success");
            }
            loadDetails(true);
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    useEffect(() => {
        loadDetails();
        if (isOfficer) loadInternalMessages();
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
            loadDetails(true);
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
            setStatusRemarks("");
            loadDetails(true);
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
            setOverrideReason("");
            loadDetails(true);
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
            loadDetails(true);
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
            loadDetails(true);
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
        resolved_awaiting_confirmation: 5,
        confirmed_resolved: 5,
        auto_confirmed_resolved: 5,
        closed: 5,
        reopened: 3,
    };
    const currentStageIdx = statusIdxMap[complaint.status] ?? 0;
    const isFinalState = [
        "resolved",
        "resolved_awaiting_confirmation",
        "confirmed_resolved",
        "auto_confirmed_resolved",
        "closed",
    ].includes(complaint.status);

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
                        <CampusBadge campus={complaint.campus} />
                        <PriorityBadge priority={complaint.final_priority} size="lg" />
                        <StatusBadge status={complaint.status} />
                        <TierBadge tier={complaint.current_tier} />
                        <button
                            type="button"
                            onClick={handleToggleUpvote}
                            className={`ml-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border transition flex items-center gap-1.5 ${complaint.has_upvoted
                                ? "bg-blue-600 text-white border-blue-700 shadow-sm"
                                : "bg-white hover:bg-slate-50 text-slate-700 border-slate-300 shadow-sm"
                                }`}
                            title="Indicate that you are also facing or witnessing this grievance"
                        >
                            <span>{complaint.has_upvoted ? "👍 Supported" : "👍 I am facing this issue too"}</span>
                            <span className={`px-1.5 py-px rounded-full text-[10px] ${complaint.has_upvoted ? "bg-white text-blue-800" : "bg-slate-100 text-slate-700 font-bold"}`}>
                                {complaint.upvote_count || 1}
                            </span>
                        </button>
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

            {/* Consolidated Grievance Notice */}
            {complaint.is_duplicate && (
                <div className="bg-blue-50 border border-blue-200 p-4 rounded-xl shadow-sm text-xs space-y-1.5">
                    <div className="flex items-center gap-1.5 font-bold text-blue-900">
                        <span>🔗 Consolidated Common Issue</span>
                        {complaint.master_complaint_grievance_id && (
                            <span className="bg-blue-200 text-blue-900 text-[10px] px-2 py-0.5 rounded font-mono">
                                Master Case: {complaint.master_complaint_grievance_id}
                            </span>
                        )}
                    </div>
                    <p className="text-blue-800">
                        This grievance has been consolidated into active common issue {complaint.master_complaint_grievance_id ? <strong>{complaint.master_complaint_grievance_id}</strong> : ""}.
                        Your individual submission reference, timestamp, and details are preserved, and status updates are synchronized with the master case.
                    </p>
                </div>
            )}

            {/* 6-Stage Timeline Stepper */}
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-6">Redressal Lifecycle Timeline</h2>
                <div className="relative flex items-center justify-between">
                    <div className="absolute top-2.5 left-0 right-0 h-0.5 bg-slate-200 -z-0"></div>
                    {stages.map((stage, idx) => {
                        const isDone = idx < currentStageIdx || isFinalState;
                        const isCurrent = idx === currentStageIdx && !isFinalState;
                        return (
                            <div key={stage.key} className="flex flex-col items-center relative z-10 text-center">
                                <div
                                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${isDone
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
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold capitalize ${ev.verification_status === "verified"
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
                                                <a href={ev.file_url} target="_blank" rel="noopener noreferrer" className="text-nie-navy hover:underline text-xs font-semibold">
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
                            {(complaint.timeline_entries || []).map((t) => (
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

                    {/* Internal Officer Discussion Card (Restricted to Officers) */}
                    {isOfficer && (
                        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
                            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                                <div>
                                    <h3 className="text-xs font-bold text-nie-navy uppercase tracking-wider flex items-center gap-1.5">
                                        <span>🔒</span> Internal Inter-Tier Discussion
                                    </h3>
                                    <p className="text-[11px] text-slate-500">
                                        Restricted to Tier 1 Dept Officers, Tier 2 Grievance Cell, Tier 3 Principal, and Super Admin.
                                    </p>
                                </div>
                                <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                                    {internalMessages.length} Notes
                                </span>
                            </div>

                            <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                                {internalMessages.length === 0 ? (
                                    <p className="text-xs text-slate-400 italic py-2">No internal discussion notes recorded yet.</p>
                                ) : (
                                    internalMessages.map((msg) => (
                                        <div key={msg.id} className="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs space-y-1">
                                            <div className="flex items-center justify-between">
                                                <span className="font-semibold text-slate-800">
                                                    {msg.author_name} <span className="text-[10px] text-nie-navy font-mono">({(msg.author_role || "").replace("_", " ")})</span>
                                                </span>
                                                <span className="text-[10px] text-slate-400 font-mono">
                                                    {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} &bull; {new Date(msg.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                            <p className="text-slate-700 whitespace-pre-line">{msg.message}</p>
                                        </div>
                                    ))
                                )}
                            </div>

                            <form onSubmit={handlePostInternalMsg} className="pt-2 border-t border-slate-100">
                                <textarea
                                    required
                                    rows="2"
                                    placeholder="Post an internal note or inter-tier guidance..."
                                    value={newInternalMsg}
                                    onChange={(e) => setNewInternalMsg(e.target.value)}
                                    className="w-full text-xs p-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-nie-navy"
                                ></textarea>
                                <div className="flex justify-end mt-1.5">
                                    <button
                                        type="submit"
                                        disabled={postingMsg}
                                        className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-3 py-1.5 rounded-md transition disabled:opacity-50"
                                    >
                                        {postingMsg ? "Posting..." : "Post Officer Note"}
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}
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
                            <div className="flex items-center justify-between">
                                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                    Linked Submissions ({complaint.duplicates_list.length})
                                </h3>
                                <span className="bg-blue-100 text-blue-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                                    👥 {complaint.affected_students_count || (complaint.duplicates_list.length + 1)} Total Affected
                                </span>
                            </div>
                            <p className="text-[11px] text-slate-500">
                                The following individual grievance submissions have been consolidated into this master case. Each student retains their submission reference and tracks progress.
                            </p>
                            <div className="space-y-2">
                                {complaint.duplicates_list.map((dup) => (
                                    <div key={dup.id} className="p-2.5 bg-slate-50 rounded border border-slate-200 text-xs">
                                        <div className="flex items-center justify-between">
                                            <span className="font-mono font-bold text-nie-navy">{dup.grievance_id}</span>
                                            {dup.complainant_identifier && (
                                                <span className="text-[10px] font-mono bg-slate-200 px-1.5 py-0.5 rounded text-slate-700">
                                                    {dup.complainant_identifier}
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-slate-800 font-medium truncate mt-1">{dup.title}</div>
                                        <div className="text-[10px] text-slate-500 mt-0.5">
                                            Reported by <strong>{dup.complainant_name}</strong> &bull; {new Date(dup.submission_date).toLocaleDateString()}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Student Confirmation Banner */}
                    {["resolved_awaiting_confirmation", "resolved"].includes(complaint.status) && (
                        <div className="bg-amber-50 border border-amber-300 p-4 rounded-xl shadow-sm text-xs space-y-2.5">
                            <div className="flex items-center gap-1.5 font-bold text-amber-900">
                                <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                {canConfirmResolution ? "Student Resolution Confirmation Required" : "Awaiting Student Confirmation"}
                            </div>
                            <p className="text-amber-800">
                                {canConfirmResolution
                                    ? "The responsible officer has marked this grievance as resolved. Please verify whether the corrective action is satisfactory."
                                    : "This grievance has been marked as resolved and is waiting for the complainant to confirm or reopen it."}
                            </p>
                            {complaint.resolution_remarks && (
                                <div className="bg-white p-2 rounded border border-amber-200 text-slate-700 font-medium">
                                    Officer Remarks: {complaint.resolution_remarks}
                                </div>
                            )}
                            {complaint.confirmation_deadline && (
                                <div className="text-[11px] text-amber-800 bg-amber-100/70 p-2 rounded font-medium">
                                    ⏱️ <strong>5-Day Auto-Confirmation:</strong> This grievance will be automatically confirmed and closed on <strong>{new Date(complaint.confirmation_deadline).toLocaleDateString()}</strong> unless reopened.
                                </div>
                            )}

                            {complaint.student_confirmed === null || complaint.student_confirmed === undefined ? (
                                canConfirmResolution && (
                                    <div className="pt-1 flex gap-2">
                                        <button
                                            onClick={() => { setStudentSatisfaction(true); setShowConfirmModal(true); }}
                                            className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-1.5 rounded transition shadow-sm"
                                        >
                                            ✓ Yes, Confirm Resolved
                                        </button>
                                        <button
                                            onClick={() => { setStudentSatisfaction(false); setShowConfirmModal(true); }}
                                            className="flex-1 bg-rose-600 hover:bg-rose-700 text-white font-semibold py-1.5 rounded transition shadow-sm"
                                        >
                                            ⚠️ No, Reopen Issue
                                        </button>
                                    </div>
                                )
                            ) : (
                                <div className="font-semibold text-emerald-800 pt-1">
                                    Student response: {complaint.student_confirmed ? "Confirmed Resolved ✓" : "Reopened with comments"}
                                </div>
                            )}
                        </div>
                    )}

                    {complaint.status === "confirmed_resolved" && (
                        <div className="bg-emerald-50 border border-emerald-300 p-3.5 rounded-xl text-xs text-emerald-800 font-medium">
                            ✓ <strong>Resolution Confirmed by Student.</strong> Case redressed and formally closed.
                        </div>
                    )}

                    {complaint.status === "auto_confirmed_resolved" && (
                        <div className="bg-emerald-50 border border-emerald-300 p-3.5 rounded-xl text-xs text-emerald-800 font-medium">
                            ✓ <strong>Auto-Confirmed Resolved.</strong> Standard 5-day redressal review period elapsed without student dispute.
                        </div>
                    )}

                    {complaint.status === "reopened" && (
                        <div className="bg-rose-50 border border-rose-300 p-3.5 rounded-xl text-xs text-rose-800 space-y-1">
                            <div className="font-bold flex items-center gap-1.5">
                                <span>⚠️</span> Grievance Reopened by Student
                            </div>
                            {complaint.reopen_reason && (
                                <p><strong>Reason stated:</strong> {complaint.reopen_reason}</p>
                            )}
                            <span className="text-[10px] text-rose-600">Reopened {complaint.reopen_count || 1} time(s) &bull; Priority re-queued</span>
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
// COMMUNITY GRIEVANCES & 14-CATEGORY BROWSER
// ----------------------------------------------------------------------
function CommunityGrievancesView({ currentUser, onSelectComplaint, addToast }) {
    const [complaints, setComplaints] = useState([]);
    const [categoriesSummary, setCategoriesSummary] = useState([]);
    const [selectedCategory, setSelectedCategory] = useState("");
    const [selectedCampus, setSelectedCampus] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [loading, setLoading] = useState(true);

    // searchOverride lets callers (e.g. "Clear") load with a specific search term
    // instead of reading the stale value captured in the closure.
    const loadData = (searchOverride) => {
        setLoading(true);
        const effectiveSearch = searchOverride !== undefined ? searchOverride : searchQuery;
        const params = new URLSearchParams();
        if (selectedCategory) params.append("category", selectedCategory);
        if (selectedCampus) params.append("campus", selectedCampus);
        if (effectiveSearch) params.append("search", effectiveSearch);

        const complaintsUrl = `/api/complaints/community${params.toString() ? `?${params.toString()}` : ""}`;

        Promise.all([
            API.request(complaintsUrl),
            API.request("/api/complaints/categories/summary"),
        ])
            .then(([compData, summaryData]) => {
                setComplaints(compData || []);
                setCategoriesSummary(summaryData || []);
            })
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadData();
    }, [selectedCategory, selectedCampus]);

    const handleSearch = (e) => {
        e.preventDefault();
        loadData();
    };

    const handleToggleUpvote = async (complaintId, currentlyUpvoted) => {
        try {
            if (currentlyUpvoted) {
                await API.request(`/api/complaints/${complaintId}/upvote`, { method: "DELETE" });
                addToast("Support removed.", "info");
            } else {
                await API.request(`/api/complaints/${complaintId}/upvote`, { method: "POST" });
                addToast("Support registered! ML priority re-evaluated.", "success");
            }
            // Update local state
            setComplaints((prev) =>
                prev.map((c) => {
                    if (c.id === complaintId) {
                        const newCount = currentlyUpvoted ? Math.max(1, c.upvote_count - 1) : c.upvote_count + 1;
                        return { ...c, has_upvoted: !currentlyUpvoted, upvote_count: newCount };
                    }
                    return c;
                })
            );
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    const categoryIcons = {
        "Placement and Career Services": "💼",
        "Infrastructure and Maintenance": "🔧",
        "Hostel and Accommodation": "🛏️",
        "Transportation": "🚌",
        "Academic and Curriculum": "📚",
        "Examination and Results": "📝",
        "Faculty-related Issues": "👨‍🏫",
        "Library": "📖",
        "Laboratory": "🔬",
        "Scholarship and Financial Aid": "🎓",
        "Fees and Administration": "🏛️",
        "Campus Safety": "🛡️",
        "IT and Network Issues": "💻",
        "Other": "📌",
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-bold text-nie-navy flex items-center gap-2">
                        <span>🏛️</span> Community Grievances & Category Explorer
                    </h1>
                    <p className="text-xs text-slate-500 mt-1 max-w-2xl">
                        Explore open grievances across all 14 official institutional categories and both campuses. If a concern is already listed, click <strong>"I am facing this issue too"</strong> to upvote it and automatically raise its priority without creating duplicate tickets.
                    </p>
                </div>
            </div>

            {/* 14 Categories Cards Grid */}
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                        Browse by Grievance Category (14 Official Tracks)
                    </h2>
                    {selectedCategory && (
                        <button
                            onClick={() => setSelectedCategory("")}
                            className="text-xs text-nie-navy hover:underline font-semibold"
                        >
                            Show All Categories &times;
                        </button>
                    )}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
                    {categoriesSummary.map((cat) => {
                        const isSelected = selectedCategory === cat.category;
                        const icon = categoryIcons[cat.category] || "📌";
                        return (
                            <button
                                key={cat.category}
                                type="button"
                                onClick={() => setSelectedCategory(isSelected ? "" : cat.category)}
                                className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${isSelected
                                    ? "bg-nie-navy text-white border-nie-navy shadow-md ring-2 ring-nie-gold/50"
                                    : "bg-white hover:bg-slate-50 text-slate-800 border-slate-200 shadow-sm"
                                    }`}
                            >
                                <div className="text-lg mb-1">{icon}</div>
                                <div>
                                    <div className="font-semibold text-[11px] leading-tight line-clamp-2">
                                        {cat.category}
                                    </div>
                                    <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-slate-100 text-[10px]">
                                        <span className={isSelected ? "text-slate-200" : "text-slate-500"}>Total</span>
                                        <span className={`font-mono font-bold ${isSelected ? "text-nie-gold" : "text-nie-navy"}`}>
                                            {cat.total_complaints}
                                        </span>
                                    </div>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-slate-600">Campus:</span>
                    <button
                        type="button"
                        onClick={() => setSelectedCampus("")}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold border transition ${selectedCampus === ""
                            ? "bg-nie-navy text-white border-nie-navy"
                            : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                            }`}
                    >
                        All Campuses
                    </button>
                    <button
                        type="button"
                        onClick={() => setSelectedCampus("North Campus")}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold border transition ${selectedCampus === "North Campus"
                            ? "bg-blue-600 text-white border-blue-700"
                            : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                            }`}
                    >
                        🏢 North Campus
                    </button>
                    <button
                        type="button"
                        onClick={() => setSelectedCampus("South Campus")}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold border transition ${selectedCampus === "South Campus"
                            ? "bg-emerald-600 text-white border-emerald-700"
                            : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                            }`}
                    >
                        🏛️ South Campus
                    </button>
                </div>

                <form onSubmit={handleSearch} className="flex gap-2">
                    <input
                        type="text"
                        placeholder="Search grievances..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-nie-navy w-48 sm:w-60"
                    />
                    <button
                        type="submit"
                        className="bg-nie-navy hover:bg-nie-navydark text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition"
                    >
                        Search
                    </button>
                    {searchQuery && (
                        <button
                            type="button"
                            onClick={() => { setSearchQuery(""); loadData(""); }}
                            className="text-xs text-slate-500 hover:text-slate-800"
                        >
                            Clear
                        </button>
                    )}
                </form>
            </div>

            {/* Complaints List */}
            <div>
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                        {selectedCategory ? `${selectedCategory} Grievances` : "Active Grievances"} ({complaints.length})
                    </h2>
                    {selectedCategory && (
                        <span className="text-xs text-slate-500">Filtered by: <strong>{selectedCategory}</strong></span>
                    )}
                </div>

                {loading ? (
                    <div className="p-12 text-center text-slate-500 text-xs">
                        <div className="w-6 h-6 border-2 border-nie-navy border-t-nie-gold rounded-full animate-spin mx-auto mb-2"></div>
                        Loading grievances...
                    </div>
                ) : complaints.length === 0 ? (
                    <div className="bg-white p-12 text-center rounded-xl border border-slate-200">
                        <p className="text-sm font-semibold text-slate-700">No grievances found</p>
                        <p className="text-xs text-slate-500 mt-1">There are no reported grievances under this category/filter.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {complaints.map((c) => (
                            <div
                                key={c.id}
                                className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between space-y-3"
                            >
                                <div>
                                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-100">
                                        <div className="flex items-center gap-2">
                                            <span className="font-mono font-bold text-xs text-nie-navy">{c.grievance_id}</span>
                                            <CampusBadge campus={c.campus} />
                                        </div>
                                        <div className="flex items-center gap-1.5">
                                            <PriorityBadge priority={c.final_priority} />
                                            <StatusBadge status={c.status} />
                                        </div>
                                    </div>

                                    <h3
                                        onClick={() => onSelectComplaint(c.id)}
                                        className="text-sm font-bold text-slate-900 mt-2.5 hover:text-nie-navy cursor-pointer line-clamp-2"
                                    >
                                        {c.title}
                                    </h3>

                                    <p className="text-xs text-slate-600 mt-1.5 line-clamp-3 leading-relaxed">
                                        {c.description}
                                    </p>

                                    <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                                        <span className="flex items-center gap-1">
                                            <span>📂</span> {c.category}
                                        </span>
                                        {c.location_name && (
                                            <span className="flex items-center gap-1">
                                                <span>📍</span> {c.location_name}
                                            </span>
                                        )}
                                        <span className="text-slate-400">
                                            {new Date(c.submission_date).toLocaleDateString()}
                                        </span>
                                    </div>
                                </div>

                                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                                    <button
                                        type="button"
                                        onClick={() => handleToggleUpvote(c.id, c.has_upvoted)}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition flex items-center gap-1.5 ${c.has_upvoted
                                            ? "bg-blue-600 text-white border-blue-700 shadow-sm"
                                            : "bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200"
                                            }`}
                                    >
                                        <span>{c.has_upvoted ? "✓ Supported" : "👍 I am facing this issue too"}</span>
                                        <span className={`px-1.5 py-px rounded-full text-[10px] ${c.has_upvoted ? "bg-white text-blue-800" : "bg-white text-slate-700 border border-slate-200 font-mono font-bold"}`}>
                                            {c.upvote_count}
                                        </span>
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => onSelectComplaint(c.id)}
                                        className="text-xs text-nie-navy hover:underline font-semibold"
                                    >
                                        View Details &rarr;
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

// ----------------------------------------------------------------------
// VERIFIED NATIONAL SCHOLARSHIP PORTAL (NSP) SCHEMES
// ----------------------------------------------------------------------
const VERIFIED_NSP_SCHEMES = [
    {
        id: "nsp-pragati",
        name: "AICTE Pragati Scholarship Scheme for Girl Students (Technical Degree)",
        provider: "All India Council for Technical Education (AICTE), Ministry of Education",
        target_group: "Girl Students",
        description: "Dedicated government scheme to provide financial encouragement to meritorious girl students pursuing technical degree education. Up to two girl children per family are eligible.",
        eligibility: "Meritorious girl students admitted to 1st year B.E./B.Tech (or 2nd year lateral entry) in AICTE-approved institutions through centralized admission process.",
        course_level: "Technical Degree (Undergraduate B.E. / B.Tech)",
        income_limit: "₹8,00,000 per annum (from official guidelines)",
        deadline_text: "Check current availability on NSP",
        guidelines_url: "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2010_G.pdf",
        apply_url: "https://scholarships.gov.in/Students",
    },
    {
        id: "nsp-saksham",
        name: "AICTE Saksham Scholarship Scheme for Specially-Abled Students (Technical Degree)",
        provider: "All India Council for Technical Education (AICTE), Ministry of Education",
        target_group: "Specially-Abled Students",
        description: "Financial grant of ₹50,000 per annum to encourage and support specially-abled students with benchmark disability of not less than 40% pursuing technical degree courses.",
        eligibility: "Specially-abled students having benchmark disability ≥ 40% (possessing valid UDID card) admitted to AICTE approved technical degree courses.",
        course_level: "Technical Degree (Undergraduate B.E. / B.Tech)",
        income_limit: "₹8,00,000 per annum (from official guidelines)",
        deadline_text: "Check current availability on NSP",
        guidelines_url: "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_2012_G.pdf",
        apply_url: "https://scholarships.gov.in/Students",
    },
    {
        id: "nsp-swanath",
        name: "AICTE Swanath Scholarship Scheme (Technical Degree)",
        provider: "All India Council for Technical Education (AICTE), Ministry of Education",
        target_group: "Eligible Swanath Applicants",
        description: "Institutional scheme to provide financial support of ₹50,000 per annum to orphaned students, children of parents deceased due to Covid-19, or children of Armed Forces & Central Paramilitary Forces personnel martyred in action.",
        eligibility: "Orphans, students whose both parents died due to Covid-19, or children of Armed Forces / CAPF personnel martyred in action admitted to AICTE approved degree programs.",
        course_level: "Technical Degree (Undergraduate B.E. / B.Tech)",
        income_limit: "₹8,00,000 per annum (from official guidelines)",
        deadline_text: "Check current availability on NSP",
        guidelines_url: "https://scholarships.gov.in/public/schemeGuidelines/AICTE/AICTE_3039_G.pdf",
        apply_url: "https://scholarships.gov.in/Students",
    },
    {
        id: "nsp-yasasvi",
        name: "PM YASASVI Central Sector Scheme of Top Class Education in College for OBC, EBC and DNT Students",
        provider: "Ministry of Social Justice and Empowerment, Govt of India",
        target_group: "OBC / EBC / DNT Applicants",
        description: "Central sector scholarship to recognize and promote quality higher education among OBC, EBC, and DNT students studying in notified higher education institutions beyond Class 12.",
        eligibility: "Students belonging to Other Backward Classes (OBC), Economically Backward Classes (EBC), or De-notified Tribes (DNT) pursuing studies in notified institutions.",
        course_level: "College / University Undergraduate Degree",
        income_limit: "₹2,50,000 per annum (from official NSP listing)",
        deadline_text: "Check current availability on NSP",
        guidelines_url: "https://scholarships.gov.in/All-Scholarships",
        apply_url: "https://scholarships.gov.in/Students",
    },
    {
        id: "nsp-csss",
        name: "PM-USP Central Sector Scheme of Scholarship for College and University Students (CSSS)",
        provider: "Department of Higher Education, Ministry of Education, Govt of India",
        target_group: "Merit-Based Applicants",
        description: "Merit-cum-means scholarship providing ₹12,000 per annum at graduation level to meritorious students from low-income families scoring above the 80th percentile in Class XII board exams.",
        eligibility: "Students scoring above the 80th percentile of successful candidates in the relevant stream from respective Class XII Board of Examination pursuing regular degree courses.",
        course_level: "College and University Undergraduate Degree",
        income_limit: "₹4,50,000 per annum (from official guidelines)",
        deadline_text: "Check current availability on NSP",
        guidelines_url: "https://scholarships.gov.in/public/schemeGuidelines/CSSS_GUIDLINES_07022024_updated.pdf",
        apply_url: "https://scholarships.gov.in/Students",
    },
];

// ----------------------------------------------------------------------
// SCHOLARSHIP RECOMMENDATION & PORTAL COMPONENT
// ----------------------------------------------------------------------
function ScholarshipPortal({ currentUser, addToast }) {
    const [activeTab, setActiveTab] = useState("nsp_schemes"); // "nsp_schemes", "announcements", "timeline", "recommendations"
    const [announcements, setAnnouncements] = useState([]);
    const [applications, setApplications] = useState([]);
    const [recommendations, setRecommendations] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showProfileCard, setShowProfileCard] = useState(currentUser?.role === "scholarship_coordinator");
    const [showProfileModal, setShowProfileModal] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showStageModal, setShowStageModal] = useState(false);
    const [selectedStage, setSelectedStage] = useState(null);

    // Profile form state
    const [branch, setBranch] = useState("Computer Science & Engineering");
    const [year, setYear] = useState(3);
    const [semester, setSemester] = useState(6);
    const [cgpa, setCgpa] = useState(8.5);
    const [annualIncome, setAnnualIncome] = useState(250000);
    const [category, setCategory] = useState("OBC");
    const [domicile, setDomicile] = useState("Karnataka");
    const [disability, setDisability] = useState(false);
    const [coordFullName, setCoordFullName] = useState(currentUser?.full_name || "");
    const [coordPhone, setCoordPhone] = useState(currentUser?.phone || "");
    const [coordDept, setCoordDept] = useState(currentUser?.department_name || "Scholarship & Financial Aid Cell");

    // Modal Edit Form State
    const [editFullName, setEditFullName] = useState("");
    const [editPhone, setEditPhone] = useState("");
    const [savingProfile, setSavingProfile] = useState(false);

    // Announcement Create Form State
    const [annSchName, setAnnSchName] = useState("");
    const [annTitle, setAnnTitle] = useState("");
    const [annDesc, setAnnDesc] = useState("");
    const [annEligibility, setAnnEligibility] = useState("");
    const [annDeadline, setAnnDeadline] = useState("");
    const [annLinks, setAnnLinks] = useState("");
    const [annEventDate, setAnnEventDate] = useState("");
    const [annEventTime, setAnnEventTime] = useState("");
    const [annEventLocation, setAnnEventLocation] = useState("");
    const [annRequiredDocs, setAnnRequiredDocs] = useState("");
    const [annAuthority, setAnnAuthority] = useState("");
    const [annSealInstructions, setAnnSealInstructions] = useState("");
    const [annIsUrgent, setAnnIsUrgent] = useState(false);
    const [annStatus] = useState("published");
    const [creatingAnn, setCreatingAnn] = useState(false);

    // Stage Update Form State
    const [stageStatus, setStageStatus] = useState("in_progress");
    const [stageDate, setStageDate] = useState("");
    const [stageTime, setStageTime] = useState("");
    const [stageLoc, setStageLoc] = useState("");
    const [stageDocs, setStageDocs] = useState("");
    const [stageAuthority, setStageAuthority] = useState("");
    const [stageSealInst, setStageSealInst] = useState("");
    const [stageRemarks, setStageRemarks] = useState("");
    const [updatingStage, setUpdatingStage] = useState(false);

    const canPublish = Boolean(
        currentUser && (
            currentUser.role === "super_admin" ||
            currentUser.role === "scholarship_coordinator" ||
            currentUser.can_publish_scholarships
        )
    );

    const loadAllData = () => {
        setLoading(true);
        Promise.all([
            API.request("/api/scholarships/announcements").catch(() => []),
            API.request("/api/scholarships/my-applications").catch(() => []),
            API.request("/api/scholarships/recommendations").catch(() => []),
            API.request("/api/scholarships/stats").catch(() => null),
            API.request("/api/scholarships/profile").catch(() => null),
        ])
            .then(([annData, appData, recData, statsData, profData]) => {
                setAnnouncements(annData || []);
                setApplications(appData || []);
                setRecommendations(recData || []);
                setStats(statsData);
                if (profData) {
                    if (profData.role === "student") {
                        if (profData.branch) setBranch(profData.branch);
                        if (profData.year) setYear(profData.year);
                        if (profData.semester) setSemester(profData.semester);
                        if (profData.cgpa !== undefined && profData.cgpa !== null) setCgpa(profData.cgpa);
                        if (profData.annual_income !== undefined && profData.annual_income !== null) setAnnualIncome(profData.annual_income);
                        if (profData.category) setCategory(profData.category);
                        if (profData.state_of_domicile) setDomicile(profData.state_of_domicile);
                        if (profData.disability_status !== undefined) setDisability(Boolean(profData.disability_status));
                    } else {
                        const nameVal = profData.full_name || currentUser?.full_name || "";
                        const phoneVal = profData.phone || currentUser?.phone || "";
                        const deptVal = profData.department_name || "Scholarship & Financial Aid Cell";
                        setCoordFullName(nameVal);
                        setCoordPhone(phoneVal);
                        setCoordDept(deptVal);
                        setEditFullName(nameVal);
                        setEditPhone(phoneVal);
                    }
                }
            })
            .catch((err) => addToast(err.message, "error"))
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        loadAllData();
    }, []);

    const openEditProfile = () => {
        if (currentUser?.role === "scholarship_coordinator") {
            setEditFullName(coordFullName || currentUser?.full_name || "");
            setEditPhone(coordPhone || currentUser?.phone || "");
        }
        setShowProfileModal(true);
    };

    const handleCreateAnnouncement = async (e) => {
        e.preventDefault();
        setCreatingAnn(true);
        try {
            await API.request("/api/scholarships/announcements", {
                method: "POST",
                body: JSON.stringify({
                    scholarship_name: annSchName.trim(),
                    title: annTitle.trim(),
                    description: annDesc.trim(),
                    eligibility_criteria: annEligibility.trim(),
                    application_deadline: annDeadline ? new Date(annDeadline).toISOString() : null,
                    links_and_documents: annLinks.trim() || null,
                    event_date: annEventDate ? new Date(annEventDate).toISOString() : null,
                    event_time_window: annEventTime.trim() || null,
                    event_location: annEventLocation.trim() || null,
                    required_documents: annRequiredDocs.trim() || null,
                    responsible_authority: annAuthority.trim() || null,
                    seal_signature_instructions: annSealInstructions.trim() || null,
                    is_urgent: annIsUrgent,
                    status: annStatus,
                }),
            });
            addToast("Scholarship announcement published successfully to all students.", "success");
            setShowCreateModal(false);
            setAnnSchName("");
            setAnnTitle("");
            setAnnDesc("");
            setAnnEligibility("");
            setAnnDeadline("");
            setAnnLinks("");
            setAnnEventDate("");
            setAnnEventTime("");
            setAnnEventLocation("");
            setAnnRequiredDocs("");
            setAnnAuthority("");
            setAnnSealInstructions("");
            setAnnIsUrgent(false);
            loadAllData();
        } catch (err) {
            addToast(err.message, "error");
        } finally {
            setCreatingAnn(false);
        }
    };

    const handleWithdrawAnnouncement = async (id) => {
        if (!confirm("Are you sure you want to withdraw this announcement? Students will no longer see it.")) return;
        try {
            await API.request(`/api/scholarships/announcements/${id}/withdraw`, { method: "POST" });
            addToast("Announcement withdrawn successfully.", "success");
            loadAllData();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    const openStageModal = (stage) => {
        setSelectedStage(stage);
        setStageStatus(stage.status || "in_progress");
        setStageDate(stage.expected_date ? stage.expected_date.split("T")[0] : "");
        setStageTime(stage.expected_time_window || "");
        setStageLoc(stage.location_or_office || "");
        setStageDocs(stage.required_documents || "");
        setStageAuthority(stage.responsible_authority || "");
        setStageSealInst(stage.seal_signature_instructions || "");
        setStageRemarks(stage.officer_remarks || "");
        setShowStageModal(true);
    };

    const handleUpdateStage = async (e) => {
        e.preventDefault();
        if (!selectedStage) return;
        setUpdatingStage(true);
        try {
            await API.request(`/api/scholarships/stages/${selectedStage.id}`, {
                method: "POST",
                body: JSON.stringify({
                    status: stageStatus,
                    expected_date: stageDate ? new Date(stageDate).toISOString() : null,
                    expected_time_window: stageTime.trim() || null,
                    location_or_office: stageLoc.trim() || null,
                    required_documents: stageDocs.trim() || null,
                    responsible_authority: stageAuthority.trim() || null,
                    seal_signature_instructions: stageSealInst.trim() || null,
                    officer_remarks: stageRemarks.trim() || null,
                }),
            });
            addToast("Stage schedule & seal/signature instructions updated.", "success");
            setShowStageModal(false);
            loadAllData();
        } catch (err) {
            addToast(err.message, "error");
        } finally {
            setUpdatingStage(false);
        }
    };

    const handleSaveProfile = async (e) => {
        e.preventDefault();
        setSavingProfile(true);
        try {
            if (currentUser && currentUser.role === "student") {
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
                addToast("Student academic and financial profile updated successfully.", "success");
            } else {
                if (!editFullName.trim()) {
                    addToast("Full name is required.", "error");
                    setSavingProfile(false);
                    return;
                }
                await API.request("/api/scholarships/profile", {
                    method: "POST",
                    body: JSON.stringify({
                        full_name: editFullName.trim(),
                        phone: editPhone.trim(),
                    }),
                });
                setCoordFullName(editFullName.trim());
                setCoordPhone(editPhone.trim());
                addToast("Coordinator profile details updated successfully.", "success");
            }
            setShowProfileModal(false);
            loadAllData();
        } catch (err) {
            addToast(err.message || "Failed to update profile", "error");
        } finally {
            setSavingProfile(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header Banner */}
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="text-2xl">🎓</span>
                        <h1 className="text-xl font-bold text-nie-navy">National Scholarship Portal (NSP) & Institutional Aid Hub</h1>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                        Official Government of India Schemes, Eligibility Verification, and Multi-Stage Tracking for NIE Mysuru.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <a
                        href="https://scholarships.gov.in/Students"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="bg-nie-gold hover:bg-amber-600 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition inline-flex items-center gap-1.5"
                    >
                        <span>🏛️ Apply on National Scholarship Portal</span>
                        <span>↗</span>
                    </a>

                    {canPublish && (
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-3.5 py-2 rounded-lg shadow-sm transition flex items-center gap-1.5"
                        >
                            <span>+ Publish Announcement</span>
                        </button>
                    )}

                    {currentUser && (currentUser.role === "student" || currentUser.role === "scholarship_coordinator" || currentUser.can_publish_scholarships) && (
                        <button
                            onClick={() => setShowProfileCard(!showProfileCard)}
                            className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold px-3.5 py-2 rounded-lg transition flex items-center gap-1.5"
                        >
                            <span>{showProfileCard ? "Close Profile" : (currentUser.role === "student" ? "View Academic Profile" : "View Coordinator Profile")}</span>
                        </button>
                    )}
                </div>
            </div>

            {/* Profile Summary Card (Displayed when toggled open) */}
            {showProfileCard && (
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-nie-navy text-white flex items-center justify-center font-bold text-base">
                                {(coordFullName || currentUser?.full_name || "U").charAt(0)}
                            </div>
                            <div>
                                <h2 className="text-sm font-bold text-nie-navy">
                                    {currentUser?.role === "student" ? "Student Academic Profile" : "Scholarship Coordinator Institutional Profile"}
                                </h2>
                                <p className="text-xs text-slate-500">
                                    {currentUser?.role === "student"
                                        ? "Academic and financial records used for transparent scholarship matching"
                                        : "Designated Institutional Nodal Officer for National Scholarship Portal (NSP)"}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={openEditProfile}
                                className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition inline-flex items-center gap-1.5"
                            >
                                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                </svg>
                                <span>Edit Profile</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setShowProfileCard(false)}
                                className="text-xs text-slate-500 hover:text-slate-800 font-semibold px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition"
                            >
                                Close Profile
                            </button>
                        </div>
                    </div>

                    {currentUser?.role === "student" ? (
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <span className="text-[10px] text-slate-500 uppercase font-semibold">Engineering Branch</span>
                                <p className="font-bold text-slate-800 mt-0.5">{branch}</p>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <span className="text-[10px] text-slate-500 uppercase font-semibold">Current CGPA</span>
                                <p className="font-bold text-slate-800 mt-0.5">{cgpa} / 10.0</p>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <span className="text-[10px] text-slate-500 uppercase font-semibold">Annual Family Income</span>
                                <p className="font-bold text-slate-800 mt-0.5">₹{Number(annualIncome).toLocaleString('en-IN')}</p>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <span className="text-[10px] text-slate-500 uppercase font-semibold">Reservation Category</span>
                                <p className="font-bold text-slate-800 mt-0.5">{category} &bull; {domicile}</p>
                            </div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <span className="text-[10px] text-slate-500 uppercase font-semibold">Full Name</span>
                                <p className="font-bold text-slate-800 mt-0.5">{coordFullName || currentUser?.full_name}</p>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <span className="text-[10px] text-slate-500 uppercase font-semibold">Official Phone</span>
                                <p className="font-bold text-slate-800 mt-0.5">{coordPhone || "Not configured"}</p>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <span className="text-[10px] text-slate-500 uppercase font-semibold">Institutional Email</span>
                                <p className="font-bold text-slate-800 mt-0.5">{currentUser?.email}</p>
                            </div>
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                                <span className="text-[10px] text-slate-500 uppercase font-semibold">Department / Cell</span>
                                <p className="font-bold text-slate-800 mt-0.5">{coordDept}</p>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Primary Tab Navigation */}
            <div className="border-b border-slate-200 flex gap-4 text-xs font-semibold overflow-x-auto">
                <button
                    onClick={() => setActiveTab("nsp_schemes")}
                    className={`pb-3 px-1 border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${activeTab === "nsp_schemes"
                        ? "border-nie-navy text-nie-navy font-bold"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                        }`}
                >
                    <span>🏛️ Verified National Schemes (NSP)</span>
                    <span className="bg-nie-navy text-white text-[10px] px-1.5 py-px rounded-full font-mono">
                        5 Official Schemes
                    </span>
                </button>

                <button
                    onClick={() => setActiveTab("announcements")}
                    className={`pb-3 px-1 border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${activeTab === "announcements"
                        ? "border-nie-navy text-nie-navy font-bold"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                        }`}
                >
                    <span>📢 Institutional Notices</span>
                    <span className="bg-slate-100 text-slate-700 text-[10px] px-1.5 py-px rounded-full font-mono">
                        {announcements.length}
                    </span>
                </button>

                <button
                    onClick={() => setActiveTab("timeline")}
                    className={`pb-3 px-1 border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${activeTab === "timeline"
                        ? "border-nie-navy text-nie-navy font-bold"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                        }`}
                >
                    <span>🧭 Application Stage Tracker</span>
                    <span className="bg-blue-100 text-blue-800 text-[10px] px-1.5 py-px rounded-full font-mono">
                        {applications.length}
                    </span>
                </button>

                <button
                    onClick={() => setActiveTab("recommendations")}
                    className={`pb-3 px-1 border-b-2 transition flex items-center gap-1.5 whitespace-nowrap ${activeTab === "recommendations"
                        ? "border-nie-navy text-nie-navy font-bold"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                        }`}
                >
                    <span>🎯 Eligibility Matching Engine</span>
                    <span className="bg-emerald-100 text-emerald-800 text-[10px] px-1.5 py-px rounded-full font-mono">
                        {recommendations.length}
                    </span>
                </button>
            </div>

            {/* TAB 1: VERIFIED NATIONAL SCHOLARSHIP PORTAL (NSP) SCHEMES */}
            {activeTab === "nsp_schemes" && (
                <div className="space-y-4">
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                            <h3 className="font-bold text-nie-navy text-sm">National Scholarship Portal (NSP) — Verified Central & AICTE Schemes</h3>
                            <p className="text-slate-600 mt-0.5">
                                Students must register and submit applications on the official NSP portal. Schemes are categorized by target student group.
                            </p>
                        </div>
                        <a
                            href="https://scholarships.gov.in/Students"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-4 py-2 rounded-lg transition inline-flex items-center gap-1 whitespace-nowrap shrink-0 shadow-sm"
                        >
                            <span>Apply on National Scholarship Portal</span>
                            <span>↗</span>
                        </a>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                        {VERIFIED_NSP_SCHEMES.map((sch) => {
                            let groupTagClass = "bg-slate-100 text-slate-700";
                            if (sch.target_group.includes("Girl")) groupTagClass = "bg-pink-50 text-pink-800 border border-pink-200";
                            else if (sch.target_group.includes("Specially")) groupTagClass = "bg-indigo-50 text-indigo-800 border border-indigo-200";
                            else if (sch.target_group.includes("Swanath")) groupTagClass = "bg-purple-50 text-purple-800 border border-purple-200";
                            else if (sch.target_group.includes("OBC")) groupTagClass = "bg-teal-50 text-teal-800 border border-teal-200";
                            else if (sch.target_group.includes("Merit")) groupTagClass = "bg-blue-50 text-blue-800 border border-blue-200";

                            return (
                                <div
                                    key={sch.id}
                                    className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between space-y-4"
                                >
                                    <div className="space-y-3">
                                        <div className="flex items-start justify-between gap-2">
                                            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                                                {sch.provider}
                                            </span>
                                            <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold px-2 py-0.5 rounded-full inline-flex items-center gap-1 shrink-0">
                                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                                                Open on NSP
                                            </span>
                                        </div>

                                        <div>
                                            <h3 className="text-base font-bold text-nie-navy leading-snug">
                                                {sch.name}
                                            </h3>
                                            <div className="mt-1.5 flex flex-wrap gap-1.5">
                                                <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-md ${groupTagClass}`}>
                                                    Target: {sch.target_group}
                                                </span>
                                            </div>
                                        </div>

                                        <p className="text-xs text-slate-600 leading-relaxed">
                                            {sch.description}
                                        </p>

                                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200/80 text-xs space-y-2">
                                            <div>
                                                <span className="font-semibold text-slate-700">Applicable Course Level:</span>{" "}
                                                <span className="text-slate-800">{sch.course_level}</span>
                                            </div>
                                            <div>
                                                <span className="font-semibold text-slate-700">Eligibility Criteria:</span>{" "}
                                                <span className="text-slate-800">{sch.eligibility}</span>
                                            </div>
                                            <div>
                                                <span className="font-semibold text-slate-700">Verified Income Limit:</span>{" "}
                                                <span className="text-emerald-800 font-semibold">{sch.income_limit}</span>
                                            </div>
                                            <div>
                                                <span className="font-semibold text-slate-700">Application Deadline:</span>{" "}
                                                <span className="text-amber-800 font-medium inline-flex items-center gap-1">
                                                    <span>⏰</span>
                                                    <span>{sch.deadline_text}</span>
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                                        <a
                                            href={sch.guidelines_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs font-semibold text-nie-navy hover:text-nie-gold inline-flex items-center gap-1 py-1.5 px-3 rounded border border-slate-200 hover:bg-slate-50 transition"
                                        >
                                            <span>📄 View Official Guidelines</span>
                                            <span>↗</span>
                                        </a>
                                        <a
                                            href={sch.apply_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="bg-nie-navy hover:bg-nie-navydark text-white text-xs font-semibold px-4 py-2 rounded-lg transition inline-flex items-center gap-1 shadow-sm"
                                        >
                                            <span>Apply on NSP</span>
                                            <span>↗</span>
                                        </a>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* TAB 1: ANNOUNCEMENTS & LIVE UPDATES */}
            {activeTab === "announcements" && (
                <div className="space-y-4">
                    {loading ? (
                        <div className="p-12 text-center text-slate-500 text-sm">
                            <div className="w-6 h-6 border-2 border-nie-navy border-t-nie-gold rounded-full animate-spin mx-auto mb-2"></div>
                            Loading published scholarship announcements...
                        </div>
                    ) : announcements.length === 0 ? (
                        <div className="bg-white p-12 text-center rounded-xl border border-slate-200">
                            <p className="text-sm font-semibold text-slate-700">No active announcements</p>
                            <p className="text-xs text-slate-500 mt-1">There are currently no new scholarship announcements published.</p>
                        </div>
                    ) : (
                        announcements.map((ann) => (
                            <div
                                key={ann.id}
                                className={`bg-white rounded-xl border p-5 shadow-sm space-y-4 transition ${ann.is_urgent ? "border-amber-400 ring-1 ring-amber-300" : "border-slate-200"}`}
                            >
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider font-mono">
                                                {ann.scholarship_name}
                                            </span>
                                            {ann.is_urgent && (
                                                <span className="bg-rose-100 text-rose-800 text-[10px] font-bold px-2 py-px rounded-full">
                                                    URGENT
                                                </span>
                                            )}
                                            {ann.status !== "published" && (
                                                <span className="bg-slate-100 text-slate-700 text-[10px] font-mono px-2 py-px rounded capitalize">
                                                    {ann.status}
                                                </span>
                                            )}
                                        </div>
                                        <h3 className="text-base font-bold text-slate-900 mt-0.5">{ann.title}</h3>
                                        <p className="text-[11px] text-slate-400">
                                            Published by {ann.author_name} ({ann.author_role}) &bull; {new Date(ann.created_at).toLocaleDateString()}
                                        </p>
                                    </div>

                                    {canPublish && (
                                        <div className="flex items-center gap-2">
                                            {ann.status === "published" && (
                                                <button
                                                    onClick={() => handleWithdrawAnnouncement(ann.id)}
                                                    className="text-xs text-rose-600 hover:text-rose-800 font-semibold px-2 py-1 rounded border border-rose-200 hover:bg-rose-50"
                                                >
                                                    Withdraw Notice
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>

                                <p className="text-xs text-slate-700 whitespace-pre-line leading-relaxed">{ann.description}</p>

                                <div className="bg-slate-50 p-3 rounded-lg text-xs space-y-1.5 border border-slate-200">
                                    <div>
                                        <strong className="text-nie-navy">Eligibility Criteria:</strong>{" "}
                                        <span className="text-slate-800">{ann.eligibility_criteria}</span>
                                    </div>
                                    {ann.application_deadline && (
                                        <div className="text-amber-800 font-medium">
                                            ⏰ <strong>Application Deadline:</strong> {new Date(ann.application_deadline).toLocaleDateString()}
                                        </div>
                                    )}
                                </div>

                                {/* Scheduled Appointment / Verification Box */}
                                {(ann.event_location || ann.event_time_window || ann.seal_signature_instructions) && (
                                    <div className="bg-gradient-to-r from-amber-50 to-orange-50/60 p-4 rounded-xl border border-amber-200 space-y-2 text-xs">
                                        <div className="font-bold text-amber-900 flex items-center gap-1.5 text-xs">
                                            <span>📅 Scheduled Physical Verification & Seal/Signature Camp</span>
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                                            {ann.event_location && (
                                                <div>
                                                    <span className="font-semibold text-slate-700">📍 Venue / Counter:</span>
                                                    <p className="text-slate-900 font-medium">{ann.event_location}</p>
                                                </div>
                                            )}
                                            {ann.event_time_window && (
                                                <div>
                                                    <span className="font-semibold text-slate-700">⏰ Time Window:</span>
                                                    <p className="text-slate-900 font-medium">
                                                        {ann.event_date ? `${new Date(ann.event_date).toLocaleDateString()} • ` : ""}
                                                        {ann.event_time_window}
                                                    </p>
                                                </div>
                                            )}
                                            {ann.required_documents && (
                                                <div className="sm:col-span-2">
                                                    <span className="font-semibold text-slate-700">📋 Required Physical Documents:</span>
                                                    <p className="text-slate-800 whitespace-pre-line mt-0.5">{ann.required_documents}</p>
                                                </div>
                                            )}
                                            {ann.seal_signature_instructions && (
                                                <div className="sm:col-span-2 bg-white/70 p-2.5 rounded border border-amber-200 text-amber-950">
                                                    <span className="font-bold">🔏 Seal & Signature Instructions:</span>
                                                    <p className="mt-0.5">{ann.seal_signature_instructions}</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {ann.links_and_documents && (
                                    <div className="flex flex-wrap gap-2 pt-1">
                                        {ann.links_and_documents.split("\n").filter(Boolean).map((link, i) => (
                                            <a
                                                key={i}
                                                href={link.trim()}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="bg-nie-navy hover:bg-nie-navydark text-white text-[11px] font-semibold px-3 py-1.5 rounded-md transition inline-flex items-center gap-1"
                                            >
                                                <span>Official Portal / Document Link #{i + 1}</span> &rarr;
                                            </a>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* TAB 2: APPLICATION APPROVAL TIMELINE & PROGRESS SCHEDULE */}
            {activeTab === "timeline" && (
                <div className="space-y-6">
                    {loading ? (
                        <div className="p-12 text-center text-slate-500 text-sm">
                            <div className="w-6 h-6 border-2 border-nie-navy border-t-nie-gold rounded-full animate-spin mx-auto mb-2"></div>
                            Loading scholarship application progress...
                        </div>
                    ) : applications.length === 0 ? (
                        <div className="bg-white p-12 text-center rounded-xl border border-slate-200 space-y-3">
                            <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto text-xl">
                                🧭
                            </div>
                            <h3 className="font-bold text-slate-800 text-sm">No Active Scholarship Applications Linked Yet</h3>
                            <p className="text-xs text-slate-500 max-w-md mx-auto">
                                Once you submit an application on the State Scholarship Portal (SSP), National Scholarship Portal (NSP), or NIE Alumni Fund, your institutional tracking timeline will appear here automatically.
                            </p>
                        </div>
                    ) : (
                        applications.map((app) => (
                            <div key={app.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-6">
                                {/* Application Header */}
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-mono text-xs font-bold text-nie-navy">{app.application_number}</span>
                                            <span className="bg-blue-100 text-blue-800 text-[10px] font-semibold px-2 py-0.5 rounded capitalize">
                                                Status: {app.status.replace("_", " ")}
                                            </span>
                                        </div>
                                        <h2 className="text-base font-bold text-slate-900 mt-1">{app.scholarship_name}</h2>
                                        <p className="text-[11px] text-slate-400">
                                            Submitted on {new Date(app.submitted_at).toLocaleDateString()} &bull; Last updated {new Date(app.updated_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <span className="text-[11px] font-semibold text-slate-500 block">Current Institutional Stage:</span>
                                        <span className="font-bold text-xs text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200 inline-block mt-0.5">
                                            {app.current_stage}
                                        </span>
                                    </div>
                                </div>

                                {/* Multi-Stage Timeline Progression */}
                                <div className="space-y-4">
                                    <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                                        Institutional Verification & Approval Stages
                                    </h3>

                                    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
                                        {app.stages.map((st) => {
                                            const isDone = st.status === "completed";
                                            const isCurrent = st.status === "in_progress";
                                            return (
                                                <div key={st.id} className="relative">
                                                    {/* Step Dot */}
                                                    <div
                                                        className={`absolute -left-6 top-1 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white shadow-sm ${isDone
                                                            ? "bg-emerald-600 ring-2 ring-emerald-200"
                                                            : isCurrent
                                                                ? "bg-amber-600 ring-4 ring-amber-100 animate-pulse"
                                                                : "bg-slate-300"
                                                            }`}
                                                    >
                                                        {isDone ? "✓" : st.stage_order}
                                                    </div>

                                                    {/* Stage Card */}
                                                    <div
                                                        className={`p-4 rounded-xl border transition ${isCurrent
                                                            ? "bg-amber-50/50 border-amber-300 shadow-sm"
                                                            : isDone
                                                                ? "bg-slate-50/60 border-slate-200"
                                                                : "bg-white border-slate-200 opacity-75"
                                                            }`}
                                                    >
                                                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                                            <div>
                                                                <h4 className="font-bold text-xs text-slate-900 flex items-center gap-2">
                                                                    <span>Stage {st.stage_order}: {st.stage_name}</span>
                                                                    <span
                                                                        className={`text-[10px] font-semibold px-2 py-px rounded capitalize ${isDone
                                                                            ? "bg-emerald-100 text-emerald-800"
                                                                            : isCurrent
                                                                                ? "bg-amber-100 text-amber-800"
                                                                                : "bg-slate-100 text-slate-600"
                                                                            }`}
                                                                    >
                                                                        {st.status.replace("_", " ")}
                                                                    </span>
                                                                </h4>
                                                            </div>

                                                            {canPublish && (
                                                                <button
                                                                    onClick={() => openStageModal(st)}
                                                                    className="text-[11px] font-semibold text-nie-navy hover:underline bg-white px-2 py-1 rounded border border-slate-200 self-start sm:self-auto"
                                                                >
                                                                    Update Stage Schedule / Status &rarr;
                                                                </button>
                                                            )}
                                                        </div>

                                                        {/* Details if current or completed */}
                                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 text-xs text-slate-600">
                                                            {st.location_or_office && (
                                                                <div>
                                                                    <strong className="text-slate-800">📍 Venue / Counter:</strong>{" "}
                                                                    {st.location_or_office}
                                                                </div>
                                                            )}
                                                            {st.expected_time_window && (
                                                                <div>
                                                                    <strong className="text-slate-800">⏰ Processing Window:</strong>{" "}
                                                                    {st.expected_date ? `${new Date(st.expected_date).toLocaleDateString()} • ` : ""}
                                                                    {st.expected_time_window}
                                                                </div>
                                                            )}
                                                            {st.responsible_authority && (
                                                                <div>
                                                                    <strong className="text-slate-800">👤 Authority / Officer:</strong>{" "}
                                                                    {st.responsible_authority}
                                                                </div>
                                                            )}
                                                            {st.required_documents && (
                                                                <div>
                                                                    <strong className="text-slate-800">📋 Documents Required:</strong>{" "}
                                                                    {st.required_documents}
                                                                </div>
                                                            )}
                                                            {st.seal_signature_instructions && (
                                                                <div className="sm:col-span-2 bg-amber-100/70 p-2.5 rounded border border-amber-200 text-amber-950 font-medium">
                                                                    <strong>🔏 Seal & Signature Instructions:</strong>{" "}
                                                                    {st.seal_signature_instructions}
                                                                </div>
                                                            )}
                                                            {st.officer_remarks && (
                                                                <div className="sm:col-span-2 text-[11px] text-slate-500 italic">
                                                                    Remarks: &ldquo;{st.officer_remarks}&rdquo;
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}

            {/* TAB 3: RECOMMENDATIONS ENGINE */}
            {activeTab === "recommendations" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {recommendations.length === 0 ? (
                        <div className="col-span-2 bg-white p-8 rounded-xl border text-center text-slate-500">
                            No matching scholarships found. Complete your academic details to re-evaluate.
                        </div>
                    ) : (
                        recommendations.map((rec) => {
                            const sch = rec.scholarship;
                            const isEligible = rec.status === "Eligible";
                            const isPot = rec.status === "Potentially Eligible";
                            return (
                                <div
                                    key={sch.id}
                                    className={`bg-white rounded-xl border p-5 shadow-sm space-y-3 transition-all ${isEligible
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
                                            className={`px-2.5 py-1 rounded-full text-xs font-semibold ${isEligible
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
                        })
                    )}
                </div>
            )}

            {/* CREATE ANNOUNCEMENT MODAL (COORDINATORS & SUPER ADMIN) */}
            {showCreateModal && (
                <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-4">
                        <div className="flex justify-between items-center border-b pb-3">
                            <h2 className="text-base font-bold text-nie-navy">Publish Scholarship Announcement & Schedule</h2>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="text-slate-400 hover:text-slate-700 text-lg font-bold"
                            >
                                &times;
                            </button>
                        </div>

                        <form onSubmit={handleCreateAnnouncement} className="space-y-4 text-xs">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div>
                                    <label className="block font-semibold text-slate-700">Scholarship Name *</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. SSP Post-Matric Karnataka 2026-27"
                                        value={annSchName}
                                        onChange={(e) => setAnnSchName(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded"
                                    />
                                </div>
                                <div>
                                    <label className="block font-semibold text-slate-700">Announcement Title *</label>
                                    <input
                                        type="text"
                                        required
                                        placeholder="e.g. Mandatory Seal & Signature Verification"
                                        value={annTitle}
                                        onChange={(e) => setAnnTitle(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block font-semibold text-slate-700">Detailed Description *</label>
                                <textarea
                                    required
                                    rows="3"
                                    placeholder="Provide detailed instructions and guidelines for students..."
                                    value={annDesc}
                                    onChange={(e) => setAnnDesc(e.target.value)}
                                    className="mt-1 w-full p-2 border rounded"
                                />
                            </div>

                            <div>
                                <label className="block font-semibold text-slate-700">Eligibility Criteria *</label>
                                <input
                                    type="text"
                                    required
                                    placeholder="e.g. SC/ST/OBC students with family income <= 2.5 LPA"
                                    value={annEligibility}
                                    onChange={(e) => setAnnEligibility(e.target.value)}
                                    className="mt-1 w-full p-2 border rounded"
                                />
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div>
                                    <label className="block font-semibold text-slate-700">Application Deadline</label>
                                    <input
                                        type="date"
                                        value={annDeadline}
                                        onChange={(e) => setAnnDeadline(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded"
                                    />
                                </div>
                                <div>
                                    <label className="block font-semibold text-slate-700">Relevant Links / Documents (one per line)</label>
                                    <textarea
                                        rows="2"
                                        placeholder="https://ssp.postmatric.karnataka.gov.in"
                                        value={annLinks}
                                        onChange={(e) => setAnnLinks(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded"
                                    />
                                </div>
                            </div>

                            {/* Scheduled Appointment Details */}
                            <div className="bg-amber-50/70 p-3.5 rounded-xl border border-amber-200 space-y-3">
                                <h3 className="font-bold text-amber-950 text-xs">Physical Verification / Seal & Signature Camp Schedule</h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div>
                                        <label className="block font-semibold text-slate-700">Event Date</label>
                                        <input
                                            type="date"
                                            value={annEventDate}
                                            onChange={(e) => setAnnEventDate(e.target.value)}
                                            className="mt-1 w-full p-2 border rounded bg-white"
                                        />
                                    </div>
                                    <div>
                                        <label className="block font-semibold text-slate-700">Time Window</label>
                                        <input
                                            type="text"
                                            placeholder="e.g. 10:30 AM – 1:30 PM"
                                            value={annEventTime}
                                            onChange={(e) => setAnnEventTime(e.target.value)}
                                            className="mt-1 w-full p-2 border rounded bg-white"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block font-semibold text-slate-700">Designated Office / Room Location</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. Scholarship Section, Room 104, Administrative Block"
                                        value={annEventLocation}
                                        onChange={(e) => setAnnEventLocation(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded bg-white"
                                    />
                                </div>

                                <div>
                                    <label className="block font-semibold text-slate-700">Required Documents (Checklist)</label>
                                    <textarea
                                        rows="2"
                                        placeholder="e.g. 1. Fee Receipt 2. Income Certificate 3. Acknowledgment Slip"
                                        value={annRequiredDocs}
                                        onChange={(e) => setAnnRequiredDocs(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded bg-white"
                                    />
                                </div>

                                <div>
                                    <label className="block font-semibold text-slate-700">Seal & Signature Instructions</label>
                                    <textarea
                                        rows="2"
                                        placeholder="e.g. HOD signature required before submitting for Principal's seal."
                                        value={annSealInstructions}
                                        onChange={(e) => setAnnSealInstructions(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded bg-white"
                                    />
                                </div>
                            </div>

                            <div className="flex items-center justify-between pt-2">
                                <label className="flex items-center gap-2 font-semibold text-rose-700 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={annIsUrgent}
                                        onChange={(e) => setAnnIsUrgent(e.target.checked)}
                                    />
                                    <span>Mark as Urgent Notice (Highlighted Banner)</span>
                                </label>

                                <div className="flex items-center gap-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowCreateModal(false)}
                                        className="px-4 py-2 border rounded font-semibold text-slate-600 hover:bg-slate-50"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={creatingAnn}
                                        className="bg-nie-navy hover:bg-nie-navydark text-white px-5 py-2 rounded font-semibold disabled:opacity-50"
                                    >
                                        {creatingAnn ? "Publishing..." : "Publish Announcement"}
                                    </button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* STAGE SCHEDULE UPDATE MODAL (COORDINATORS) */}
            {showStageModal && selectedStage && (
                <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-4">
                        <div className="flex justify-between items-center border-b pb-3">
                            <div>
                                <h2 className="text-base font-bold text-nie-navy">Update Stage Schedule & Instructions</h2>
                                <p className="text-[11px] text-slate-500">Stage: {selectedStage.stage_name}</p>
                            </div>
                            <button
                                onClick={() => setShowStageModal(false)}
                                className="text-slate-400 hover:text-slate-700 text-lg font-bold"
                            >
                                &times;
                            </button>
                        </div>

                        <form onSubmit={handleUpdateStage} className="space-y-3 text-xs">
                            <div>
                                <label className="block font-semibold text-slate-700">Stage Status</label>
                                <select
                                    value={stageStatus}
                                    onChange={(e) => setStageStatus(e.target.value)}
                                    className="mt-1 w-full p-2 border rounded bg-white"
                                >
                                    <option value="pending">Pending</option>
                                    <option value="in_progress">In Progress (Active)</option>
                                    <option value="completed">Completed (Advances to Next Stage)</option>
                                    <option value="rejected">Rejected / Incomplete</option>
                                </select>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block font-semibold text-slate-700">Scheduled Date</label>
                                    <input
                                        type="date"
                                        value={stageDate}
                                        onChange={(e) => setStageDate(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded"
                                    />
                                </div>
                                <div>
                                    <label className="block font-semibold text-slate-700">Time Window</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. 10:30 AM – 1:30 PM"
                                        value={stageTime}
                                        onChange={(e) => setStageTime(e.target.value)}
                                        className="mt-1 w-full p-2 border rounded"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block font-semibold text-slate-700">Counter / Room Location</label>
                                <input
                                    type="text"
                                    placeholder="e.g. Room 104, Admin Block"
                                    value={stageLoc}
                                    onChange={(e) => setStageLoc(e.target.value)}
                                    className="mt-1 w-full p-2 border rounded"
                                />
                            </div>

                            <div>
                                <label className="block font-semibold text-slate-700">Required Documents for this Stage</label>
                                <textarea
                                    rows="2"
                                    placeholder="List physical documents student must bring..."
                                    value={stageDocs}
                                    onChange={(e) => setStageDocs(e.target.value)}
                                    className="mt-1 w-full p-2 border rounded"
                                />
                            </div>

                            <div>
                                <label className="block font-semibold text-slate-700">Responsible Authority / Officer</label>
                                <input
                                    type="text"
                                    placeholder="e.g. Scholarship Superintendent"
                                    value={stageAuthority}
                                    onChange={(e) => setStageAuthority(e.target.value)}
                                    className="mt-1 w-full p-2 border rounded"
                                />
                            </div>

                            <div>
                                <label className="block font-semibold text-slate-700">Seal & Signature Instructions</label>
                                <textarea
                                    rows="2"
                                    placeholder="Special prerequisites for official seal..."
                                    value={stageSealInst}
                                    onChange={(e) => setStageSealInst(e.target.value)}
                                    className="mt-1 w-full p-2 border rounded"
                                />
                            </div>

                            <div>
                                <label className="block font-semibold text-slate-700">Officer Remarks</label>
                                <textarea
                                    rows="2"
                                    placeholder="Progress notes or verification comments..."
                                    value={stageRemarks}
                                    onChange={(e) => setStageRemarks(e.target.value)}
                                    className="mt-1 w-full p-2 border rounded"
                                />
                            </div>

                            <div className="flex justify-end gap-2 pt-2 border-t">
                                <button
                                    type="button"
                                    onClick={() => setShowStageModal(false)}
                                    className="px-4 py-2 border rounded font-semibold text-slate-600 hover:bg-slate-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={updatingStage}
                                    className="bg-nie-navy hover:bg-nie-navydark text-white px-5 py-2 rounded font-semibold disabled:opacity-50"
                                >
                                    {updatingStage ? "Saving..." : "Save Schedule"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* EDIT PROFILE MODAL (COORDINATORS & STUDENTS) */}
            {showProfileModal && (
                <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto space-y-4">
                        <div className="flex justify-between items-center border-b pb-3">
                            <div>
                                <h2 className="text-base font-bold text-nie-navy">
                                    {currentUser?.role === "student" ? "Edit Academic & Financial Profile" : "Edit Scholarship Coordinator Profile"}
                                </h2>
                                <p className="text-xs text-slate-500 mt-0.5">
                                    {currentUser?.role === "student"
                                        ? "Update details used for scholarship matching and institutional records"
                                        : "Update official coordinator contact details and institutional directory listing"}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => setShowProfileModal(false)}
                                className="text-slate-400 hover:text-slate-700 text-xl font-bold p-1 leading-none"
                            >
                                &times;
                            </button>
                        </div>

                        <form onSubmit={handleSaveProfile} className="space-y-4 text-xs">
                            {currentUser?.role === "student" ? (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <div>
                                        <label className="block font-semibold text-slate-700">Engineering Branch</label>
                                        <input
                                            type="text"
                                            required
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
                                            required
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
                                            required
                                            value={annualIncome}
                                            onChange={(e) => setAnnualIncome(e.target.value)}
                                            className="mt-1 w-full p-2 border rounded"
                                        />
                                    </div>
                                    <div>
                                        <label className="block font-semibold text-slate-700">Reservation Category</label>
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
                                            required
                                            value={domicile}
                                            onChange={(e) => setDomicile(e.target.value)}
                                            className="mt-1 w-full p-2 border rounded"
                                        />
                                    </div>
                                    <div className="flex items-center gap-2 pt-6">
                                        <input
                                            type="checkbox"
                                            id="disabilityModalCheck"
                                            checked={disability}
                                            onChange={(e) => setDisability(e.target.checked)}
                                        />
                                        <label htmlFor="disabilityModalCheck" className="text-slate-700 font-semibold cursor-pointer">
                                            Specially-Abled (Disability &ge; 40%)
                                        </label>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    <div>
                                        <label className="block font-semibold text-slate-700">Full Name *</label>
                                        <input
                                            type="text"
                                            required
                                            value={editFullName}
                                            onChange={(e) => setEditFullName(e.target.value)}
                                            className="mt-1 w-full p-2 border rounded text-xs"
                                            placeholder="e.g. Prof. Savitha Murthy"
                                        />
                                    </div>
                                    <div>
                                        <label className="block font-semibold text-slate-700">Official Contact Phone</label>
                                        <input
                                            type="text"
                                            value={editPhone}
                                            onChange={(e) => setEditPhone(e.target.value)}
                                            placeholder="e.g. +91 98800 23456"
                                            className="mt-1 w-full p-2 border rounded text-xs"
                                        />
                                    </div>
                                    <div>
                                        <label className="block font-semibold text-slate-700">Official Institutional Email (Read Only)</label>
                                        <input
                                            type="email"
                                            disabled
                                            value={currentUser?.email || ""}
                                            className="mt-1 w-full p-2 border rounded bg-slate-100 text-slate-500 cursor-not-allowed text-xs"
                                        />
                                        <p className="text-[10px] text-slate-400 mt-0.5">Assigned by institutional administration</p>
                                    </div>
                                    <div>
                                        <label className="block font-semibold text-slate-700">Department / Cell (Read Only)</label>
                                        <input
                                            type="text"
                                            disabled
                                            value={coordDept}
                                            className="mt-1 w-full p-2 border rounded bg-slate-100 text-slate-500 cursor-not-allowed text-xs"
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="flex justify-end items-center gap-2 pt-3 border-t border-slate-100">
                                <button
                                    type="button"
                                    onClick={() => setShowProfileModal(false)}
                                    className="px-4 py-2 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 font-semibold transition"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={savingProfile}
                                    className="px-5 py-2 rounded-lg bg-nie-navy hover:bg-nie-navydark text-white font-semibold transition flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
                                >
                                    {savingProfile ? (
                                        <React.Fragment>
                                            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                                            <span>Saving...</span>
                                        </React.Fragment>
                                    ) : (
                                        <span>Save Changes</span>
                                    )}
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
            await API.request("/api/escalations/run-check", { method: "POST" });
            addToast("15-day escalation boundaries evaluated.", "success");
            loadEscalationData();
        } catch (err) {
            addToast(err.message, "error");
        }
    };

    if (loading) {
        return <div className="p-12 text-center text-slate-500">Loading escalation matrix...</div>;
    }

    if (!data) {
        return <div className="p-12 text-center text-slate-500">Escalation data is unavailable right now.</div>;
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
                    {(data.department_escalations || []).map((d) => (
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
                                        className={`h-2 rounded-full ${prio.label === "Critical"
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
    const [coordinators, setCoordinators] = useState([]);
    const [announcements, setAnnouncements] = useState([]);
    const [scholarshipStats, setScholarshipStats] = useState(null);
    const [updatingPermission, setUpdatingPermission] = useState(false);

    const loadAdminData = () => {
        API.request("/api/admin/users").then(setUsers).catch(() => { });
        API.request("/api/admin/departments").then(setDepartments).catch(() => { });
        API.request("/api/admin/audit-logs").then(setAuditLogs).catch(() => { });
        API.request("/api/scholarships/coordinators").then(setCoordinators).catch(() => { });
        API.request("/api/scholarships/announcements").then(setAnnouncements).catch(() => { });
        API.request("/api/scholarships/stats").then(setScholarshipStats).catch(() => { });
    };

    useEffect(() => {
        loadAdminData();
    }, []);

    const handleTogglePermission = async (userId, currentVal) => {
        setUpdatingPermission(true);
        try {
            const nextVal = !currentVal;
            await API.request("/api/scholarships/coordinators/permissions", {
                method: "POST",
                body: JSON.stringify({ user_id: userId, can_publish_scholarships: nextVal }),
            });
            addToast(`Scholarship publishing permission ${nextVal ? "granted" : "revoked"} successfully.`, "success");
            loadAdminData();
        } catch (err) {
            addToast(err.message, "error");
        } finally {
            setUpdatingPermission(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <h1 className="text-xl font-bold text-nie-navy">Super Admin Operations & Institutional Governance</h1>
                <p className="text-xs text-slate-500 mt-1">
                    System configuration, user provisioning, scholarship publishing authorizations, and full security audit trail.
                </p>
            </div>

            {/* Scholarship Updates & Coordinator Authorization Management */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-5 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <div>
                        <h2 className="text-sm font-bold text-nie-navy flex items-center gap-2">
                            <span>🎓 Scholarship Updates Management & Coordinator Authorization</span>
                        </h2>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                            Grant or revoke scholarship announcement and verification schedule publishing permissions under the Principle of Least Privilege.
                        </p>
                    </div>
                </div>

                {/* Overall Scholarship Stats */}
                {scholarshipStats && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                            <p className="text-[11px] font-semibold text-slate-500">Active Schemes</p>
                            <p className="text-xl font-bold text-nie-navy mt-0.5">{scholarshipStats.total_scholarships}</p>
                        </div>
                        <div className="bg-amber-50 p-3 rounded-lg border border-amber-200">
                            <p className="text-[11px] font-semibold text-amber-800">Published Notices</p>
                            <p className="text-xl font-bold text-amber-900 mt-0.5">{scholarshipStats.published_announcements}</p>
                        </div>
                        <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
                            <p className="text-[11px] font-semibold text-blue-800">Active Applications</p>
                            <p className="text-xl font-bold text-blue-900 mt-0.5">{scholarshipStats.active_applications}</p>
                        </div>
                        <div className="bg-purple-50 p-3 rounded-lg border border-purple-200">
                            <p className="text-[11px] font-semibold text-purple-800">Scheduled Camps</p>
                            <p className="text-xl font-bold text-purple-900 mt-0.5">{scholarshipStats.upcoming_appointments}</p>
                        </div>
                    </div>
                )}

                {/* Coordinators Authorization Table */}
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                            Authorized Coordinators & Faculty Publishers
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">{coordinators.length} Officers</span>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs text-slate-600">
                            <thead className="bg-slate-50/50 text-[10px] uppercase font-semibold text-slate-700 border-b">
                                <tr>
                                    <th className="px-4 py-2">Name & Designation</th>
                                    <th className="px-4 py-2">System Role</th>
                                    <th className="px-4 py-2">Email</th>
                                    <th className="px-4 py-2">Notices Published</th>
                                    <th className="px-4 py-2">Publish Permission</th>
                                    <th className="px-4 py-2 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {coordinators.map((c) => (
                                    <tr key={c.id} className="hover:bg-slate-50">
                                        <td className="px-4 py-2.5 font-semibold text-slate-900">{c.full_name}</td>
                                        <td className="px-4 py-2.5 capitalize font-mono text-[11px]">{c.role.replace("_", " ")}</td>
                                        <td className="px-4 py-2.5 font-mono text-slate-500">{c.email}</td>
                                        <td className="px-4 py-2.5 font-mono font-bold text-nie-navy">{c.announcements_count}</td>
                                        <td className="px-4 py-2.5">
                                            {c.can_publish_scholarships ? (
                                                <span className="bg-emerald-100 text-emerald-800 font-semibold px-2 py-0.5 rounded text-[10px]">
                                                    ✓ Authorized Publisher
                                                </span>
                                            ) : (
                                                <span className="bg-slate-100 text-slate-600 font-semibold px-2 py-0.5 rounded text-[10px]">
                                                    Standard Privileges
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-4 py-2.5 text-right">
                                            <button
                                                type="button"
                                                disabled={updatingPermission}
                                                onClick={() => handleTogglePermission(c.id, c.can_publish_scholarships)}
                                                className={`px-3 py-1 rounded text-xs font-semibold transition disabled:opacity-50 ${c.can_publish_scholarships
                                                    ? "bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200"
                                                    : "bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200"
                                                    }`}
                                            >
                                                {c.can_publish_scholarships ? "Revoke Permission" : "Grant Publishing Rights"}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Published Announcements Audit */}
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                            All Announcements & Notice Audit Trail
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">{announcements.length} Records</span>
                    </div>
                    <div className="overflow-x-auto max-h-56">
                        <table className="w-full text-left text-xs text-slate-600">
                            <thead className="bg-slate-50/50 text-[10px] uppercase font-semibold text-slate-700 sticky top-0 border-b">
                                <tr>
                                    <th className="px-4 py-2">Scholarship & Title</th>
                                    <th className="px-4 py-2">Author</th>
                                    <th className="px-4 py-2">Status</th>
                                    <th className="px-4 py-2">Event Schedule</th>
                                    <th className="px-4 py-2">Date Created</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {announcements.map((a) => (
                                    <tr key={a.id} className="hover:bg-slate-50">
                                        <td className="px-4 py-2 max-w-xs">
                                            <div className="font-semibold text-slate-900">{a.scholarship_name}</div>
                                            <div className="text-[10px] text-slate-500 truncate">{a.title}</div>
                                        </td>
                                        <td className="px-4 py-2 font-mono text-[11px]">{a.author_name}</td>
                                        <td className="px-4 py-2">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold capitalize ${a.status === "published" ? "bg-emerald-100 text-emerald-800" : a.status === "draft" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"}`}>
                                                {a.status}
                                            </span>
                                        </td>
                                        <td className="px-4 py-2 text-[11px] text-slate-600">
                                            {a.event_location ? `${a.event_time_window || "Scheduled"} @ ${a.event_location}` : "None"}
                                        </td>
                                        <td className="px-4 py-2 font-mono text-[10px] text-slate-400">
                                            {new Date(a.created_at).toLocaleDateString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Users Directory */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b flex justify-between items-center">
                    <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Registered Institutional Users</h2>
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
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
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
            message: `Hello ${currentUser ? currentUser.full_name.split(" ")[0] : "there"}! I am NIEresolve AI, your official NIE Mysuru institutional assistant.\n\nAsk me about grievance status, 15-day escalation policies, departments, or scholarships!`,
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
                    className="bg-white hover:bg-slate-100 border rounded-full px-2.5 py-1 whitespace-nowrap text-slate-700 shadow-sm"
                >
                    My Grievance Status
                </button>
                <button
                    onClick={() => handleSend("How does the 15-day escalation matrix work?")}
                    className="bg-white hover:bg-slate-100 border rounded-full px-2.5 py-1 whitespace-nowrap text-slate-700 shadow-sm"
                >
                    15-Day Escalation Policy
                </button>
                <button
                    onClick={() => handleSend("What scholarships am I eligible for?")}
                    className="bg-white hover:bg-slate-100 border rounded-full px-2.5 py-1 whitespace-nowrap text-slate-700 shadow-sm"
                >
                    Scholarships For Me
                </button>
                <button
                    onClick={() => handleSend("Which department handles hostel water issues?")}
                    className="bg-white hover:bg-slate-100 border rounded-full px-2.5 py-1 whitespace-nowrap text-slate-700 shadow-sm"
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
                            className={`p-3 rounded-xl max-w-[85%] whitespace-pre-line leading-relaxed ${m.sender === "user"
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
        } catch (err) { }
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
                            className={`p-3 space-y-0.5 hover:bg-slate-50 transition ${!n.is_read ? "bg-amber-50/50" : ""}`}
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

// Mount React Root Resiliently
function mountApp() {
    const rootEl = document.getElementById("root");
    if (rootEl) {
        const root = ReactDOM.createRoot(rootEl);
        root.render(<App />);
    } else {
        window.addEventListener("DOMContentLoaded", mountApp);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountApp);
} else {
    mountApp();
}