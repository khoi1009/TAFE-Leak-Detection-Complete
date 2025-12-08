# frontend/login_app.py
"""
TAFE Leak Detection - Login Portal with Authentication
Authenticates against FastAPI backend and redirects to dashboard.
Automatically starts the dashboard subprocess.
"""
# %%
import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import requests
import os
import subprocess
import sys
import time
import threading
import atexit
from flask import session, redirect

# Configuration
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
PORT = int(os.environ.get("LOGIN_PORT", 8050))
API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8051")
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", 8051))

# Global variable to track dashboard process
dashboard_process = None

# Create Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CYBORG,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css",
    ],
    suppress_callback_exceptions=True,
    title="TAFE Leak Detection - Login",
    assets_folder="assets",
)
server = app.server
server.secret_key = os.environ.get("SECRET_KEY", "tafe-leak-detection-secret-key-2025")


# Custom CSS for login page - AQUA-GOV Enhanced Theme
login_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    body {
        background: linear-gradient(135deg, #020617 0%, #0a1628 25%, #0c1e3d 50%, #0a1628 75%, #020617 100%);
        min-height: 100vh;
        position: relative;
        overflow-x: hidden;
    }
    
    /* Deep Ocean Data Background Effect */
    body::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            /* Bioluminescent glow spots */
            radial-gradient(ellipse 600px 400px at 15% 85%, rgba(6, 182, 212, 0.2) 0%, transparent 70%),
            radial-gradient(ellipse 500px 350px at 85% 15%, rgba(20, 184, 166, 0.15) 0%, transparent 70%),
            radial-gradient(ellipse 400px 300px at 50% 50%, rgba(8, 145, 178, 0.1) 0%, transparent 60%),
            /* Flowing data streams */
            radial-gradient(ellipse 200px 800px at 25% 50%, rgba(6, 182, 212, 0.08) 0%, transparent 70%),
            radial-gradient(ellipse 200px 800px at 75% 50%, rgba(20, 184, 166, 0.06) 0%, transparent 70%),
            /* Subtle sparkle points */
            radial-gradient(circle 2px at 20% 30%, rgba(255, 255, 255, 0.3) 0%, transparent 100%),
            radial-gradient(circle 2px at 80% 70%, rgba(255, 255, 255, 0.2) 0%, transparent 100%),
            radial-gradient(circle 1px at 60% 20%, rgba(255, 255, 255, 0.25) 0%, transparent 100%),
            radial-gradient(circle 1px at 40% 80%, rgba(255, 255, 255, 0.2) 0%, transparent 100%);
        pointer-events: none;
        z-index: 0;
        animation: oceanPulse 8s ease-in-out infinite;
    }
    
    /* Secondary animated layer for depth */
    body::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background:
            /* Moving wave effect */
            linear-gradient(180deg, transparent 0%, rgba(6, 182, 212, 0.03) 50%, transparent 100%),
            /* Vignette edges */
            radial-gradient(ellipse at center, transparent 40%, rgba(0, 0, 0, 0.4) 100%);
        pointer-events: none;
        z-index: 0;
        animation: waveFlow 12s ease-in-out infinite;
    }
    
    @keyframes oceanPulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.02); }
    }
    
    @keyframes waveFlow {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
    
    .login-container {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        position: relative;
        z-index: 1;
    }
    
    .login-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1.5rem;
    }
    
    .brand-header {
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .brand-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }
    
    .brand-logo-text {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
        letter-spacing: -0.025em;
    }
    
    .brand-logo-text span {
        color: #14b8a6;
    }
    
    .brand-tagline {
        color: #64748b;
        font-size: 0.875rem;
    }
    
    .login-card {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(20, 184, 166, 0.2);
        border-radius: 20px;
        box-shadow: 
            0 25px 50px -12px rgba(0, 0, 0, 0.5),
            0 0 0 1px rgba(255, 255, 255, 0.05),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        padding: 2rem 1.75rem;
        max-width: 320px;
        width: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .login-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #14b8a6, #06b6d4, #14b8a6);
        background-size: 200% 100%;
        animation: shimmer 3s linear infinite;
    }
    
    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .login-icon-wrapper {
        width: 80px;
        height: 80px;
        background: linear-gradient(135deg, rgba(20, 184, 166, 0.2) 0%, rgba(6, 182, 212, 0.1) 100%);
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 1.25rem;
        border: 1px solid rgba(20, 184, 166, 0.3);
        box-shadow: 0 8px 32px rgba(20, 184, 166, 0.15);
    }
    
    .login-icon {
        font-size: 2.5rem;
        color: #14b8a6;
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
    
    .login-title {
        color: #f1f5f9;
        font-weight: 700;
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
    }
    
    .login-subtitle {
        color: #64748b;
        font-size: 0.9rem;
    }
    
    .version-badge {
        background: linear-gradient(135deg, rgba(20, 184, 166, 0.15) 0%, rgba(6, 182, 212, 0.1) 100%);
        color: #14b8a6;
        padding: 0.375rem 0.875rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        display: inline-block;
        margin-top: 0.75rem;
        border: 1px solid rgba(20, 184, 166, 0.2);
    }
    
    .form-label-custom {
        color: #94a3b8;
        font-size: 0.8125rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    .form-input {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(71, 85, 105, 0.5) !important;
        color: #f1f5f9 !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
        max-width: 100% !important;
        height: auto !important;
    }
    
    .form-input:focus {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border-color: #14b8a6 !important;
        box-shadow: 0 0 0 4px rgba(20, 184, 166, 0.15) !important;
        outline: none !important;
    }
    
    .form-input::placeholder {
        color: #475569 !important;
    }
    
    .login-btn {
        background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%) !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 1rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        letter-spacing: 0.01em !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 14px rgba(20, 184, 166, 0.25) !important;
    }
    
    .login-btn:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(20, 184, 166, 0.35) !important;
        background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important;
    }
    
    .login-btn:active {
        transform: translateY(0) !important;
    }
    
    .demo-credentials {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.08) 0%, rgba(20, 184, 166, 0.05) 100%);
        border: 1px solid rgba(34, 197, 94, 0.2);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-top: 1.5rem;
    }
    
    .demo-credentials h6 {
        color: #22c55e;
        font-size: 0.8125rem;
        font-weight: 600;
        margin-bottom: 0.625rem;
        display: flex;
        align-items: center;
        gap: 0.375rem;
    }
    
    .demo-credentials code {
        background: rgba(15, 23, 42, 0.6);
        color: #e2e8f0;
        padding: 0.1875rem 0.5rem;
        border-radius: 6px;
        font-size: 0.8125rem;
        font-family: 'SF Mono', 'Fira Code', monospace;
        border: 1px solid rgba(71, 85, 105, 0.3);
    }
    
    .footer-text {
        text-align: center;
        color: #475569;
        font-size: 0.75rem;
        margin-top: 1.5rem;
    }
    
    .footer-text a {
        color: #14b8a6;
        text-decoration: none;
    }
    
    .footer-text a:hover {
        text-decoration: underline;
    }
    
    /* Custom Alert Styles */
    .alert-danger {
        background: rgba(239, 68, 68, 0.1) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        color: #fca5a5 !important;
        border-radius: 10px !important;
    }
    
    .alert-success {
        background: rgba(34, 197, 94, 0.1) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        color: #86efac !important;
        border-radius: 10px !important;
    }
    
    /* ========== Hydro-Pulse Loading Spinner ========== */
    .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem 0;
    }
    
    .hydro-pulse {
        position: relative;
        width: 50px;
        height: 50px;
        background: rgba(20, 184, 166, 0.4);
        border-radius: 50%;
        animation: pulse-ring 1.5s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
    }
    
    .hydro-pulse::after {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background: #14b8a6;
        border-radius: 50%;
        box-shadow: 0 0 20px rgba(20, 184, 166, 0.6);
        animation: pulse-dot 1.5s cubic-bezier(0.455, 0.03, 0.515, 0.955) -0.4s infinite;
    }
    
    @keyframes pulse-ring {
        0% { transform: scale(0.8); opacity: 1; }
        100% { transform: scale(2.5); opacity: 0; }
    }
    
    @keyframes pulse-dot {
        0% { transform: scale(0.8); }
        50% { transform: scale(1); }
        100% { transform: scale(0.8); }
    }
    
    .loading-text {
        margin-top: 1.25rem;
        color: #94a3b8;
        font-size: 0.75rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        animation: text-fade 1.5s infinite ease-in-out;
    }
    
    @keyframes text-fade {
        0%, 100% { opacity: 0.5; }
        50% { opacity: 1; }
    }
    
    /* Hide loader by default, show when loading */
    .loader-hidden {
        display: none !important;
    }
</style>
"""

# Main layout
app.layout = html.Div(
    [
        dcc.Store(id="auth-store", storage_type="session"),
        dcc.Location(id="url", refresh=True),
        html.Div(
            [
                html.Div(
                    [
                        # Brand Header above card
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className="bi bi-droplet-fill",
                                            style={
                                                "fontSize": "1.75rem",
                                                "color": "#14b8a6",
                                            },
                                        ),
                                        html.Span(
                                            [
                                                "Water",
                                                html.Span(
                                                    "Watch", style={"color": "#14b8a6"}
                                                ),
                                            ],
                                            className="brand-logo-text",
                                        ),
                                    ],
                                    className="brand-logo",
                                ),
                                html.P(
                                    "NSW Water Leak Detection",
                                    className="brand-tagline",
                                ),
                            ],
                            className="brand-header",
                        ),
                        # Login Card
                        html.Div(
                            [
                                # Header
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.I(
                                                    className="bi bi-shield-lock-fill login-icon"
                                                ),
                                            ],
                                            className="login-icon-wrapper",
                                        ),
                                        html.H1(
                                            "Welcome Back", className="login-title"
                                        ),
                                        html.P(
                                            "Sign in to access the dashboard",
                                            className="login-subtitle",
                                        ),
                                        html.Span(
                                            "TAFE NSW Demo v2.0",
                                            className="version-badge",
                                        ),
                                    ],
                                    className="login-header",
                                ),
                                # Login Form
                                html.Div(
                                    [
                                        # Error Alert
                                        dbc.Alert(
                                            id="login-error",
                                            color="danger",
                                            is_open=False,
                                            dismissable=True,
                                            className="mb-3",
                                        ),
                                        # Success Alert
                                        dbc.Alert(
                                            id="login-success",
                                            color="success",
                                            is_open=False,
                                            className="mb-3",
                                        ),
                                        # Username
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Username",
                                                    className="form-label-custom",
                                                ),
                                                dbc.Input(
                                                    id="login-username",
                                                    placeholder="Enter your username",
                                                    type="text",
                                                    className="form-input mb-3",
                                                ),
                                            ]
                                        ),
                                        # Password
                                        html.Div(
                                            [
                                                html.Label(
                                                    "Password",
                                                    className="form-label-custom",
                                                ),
                                                dbc.Input(
                                                    id="login-password",
                                                    placeholder="Enter your password",
                                                    type="password",
                                                    className="form-input mb-4",
                                                ),
                                            ]
                                        ),
                                        # Login Button
                                        dbc.Button(
                                            [
                                                html.I(
                                                    className="bi bi-arrow-right-circle-fill me-2"
                                                ),
                                                "Sign In to Dashboard",
                                            ],
                                            id="login-button",
                                            className="login-btn w-100",
                                            size="lg",
                                            n_clicks=0,
                                        ),
                                        # Hydro-Pulse Loading Spinner
                                        html.Div(
                                            [
                                                html.Div(className="hydro-pulse"),
                                                html.Div(
                                                    "Authenticating...",
                                                    className="loading-text",
                                                ),
                                            ],
                                            id="login-loader",
                                            className="loader-container loader-hidden",
                                        ),
                                        # Demo Credentials Info
                                        html.Div(
                                            [
                                                html.H6(
                                                    [
                                                        html.I(
                                                            className="bi bi-lightbulb-fill me-1"
                                                        ),
                                                        "Demo Credentials",
                                                    ]
                                                ),
                                                html.P(
                                                    [
                                                        "Admin: ",
                                                        html.Code("admin"),
                                                        " / ",
                                                        html.Code("admin123"),
                                                        html.Br(),
                                                        "Operator: ",
                                                        html.Code("operator"),
                                                        " / ",
                                                        html.Code("operator123"),
                                                    ],
                                                    className="mb-0 small",
                                                    style={"color": "#94a3b8"},
                                                ),
                                            ],
                                            className="demo-credentials",
                                        ),
                                    ]
                                ),
                            ],
                            className="login-card",
                        ),
                        # Footer
                        html.Div(
                            [
                                html.P(
                                    [
                                        "Powered by ",
                                        html.A("TAFE NSW", href="#"),
                                        " & ",
                                        html.A("Griffith University", href="#"),
                                    ],
                                    className="mb-0",
                                ),
                            ],
                            className="footer-text",
                        ),
                    ],
                    className="login-wrapper",
                ),
            ],
            className="login-container",
        ),
    ],
    className="login-page-root",
)


@callback(
    [
        Output("login-error", "children"),
        Output("login-error", "is_open"),
        Output("login-success", "children"),
        Output("login-success", "is_open"),
        Output("auth-store", "data"),
        Output("url", "href"),
        Output("login-loader", "className"),
        Output("login-button", "disabled"),
    ],
    Input("login-button", "n_clicks"),
    [
        State("login-username", "value"),
        State("login-password", "value"),
    ],
    prevent_initial_call=True,
)
def handle_login(n_clicks, username, password):
    """Handle login form submission."""
    if not n_clicks:
        return (
            "",
            False,
            "",
            False,
            None,
            dash.no_update,
            "loader-container loader-hidden",
            False,
        )

    if not username or not password:
        return (
            "Please enter both username and password.",
            True,
            "",
            False,
            None,
            dash.no_update,
            "loader-container loader-hidden",
            False,
        )

    try:
        # Call FastAPI backend
        response = requests.post(
            f"{API_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            auth_data = {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "user": data["user"],
            }
            # Redirect to dashboard with token
            dashboard_url = f"{DASHBOARD_URL}?token={data['access_token']}"
            return (
                "",
                False,
                f"Welcome, {data['user']['full_name'] or username}! Redirecting...",
                True,
                auth_data,
                dashboard_url,
                "loader-container",  # Show loader during redirect
                True,  # Disable button
            )

        elif response.status_code == 401:
            return (
                "Invalid username or password.",
                True,
                "",
                False,
                None,
                dash.no_update,
                "loader-container loader-hidden",
                False,
            )

        else:
            return (
                f"Login failed: {response.text}",
                True,
                "",
                False,
                None,
                dash.no_update,
                "loader-container loader-hidden",
                False,
            )

    except requests.exceptions.ConnectionError:
        # API is down - allow bypass for demo
        return (
            "⚠️ API server not running. Starting dashboard in demo mode...",
            False,
            "Redirecting to dashboard (demo mode)...",
            True,
            {"demo": True},
            f"{DASHBOARD_URL}?demo=true",
            "loader-container",  # Show loader during redirect
            True,  # Disable button
        )

    except Exception as e:
        return (
            f"Error: {str(e)}",
            True,
            "",
            False,
            None,
            dash.no_update,
            "loader-container loader-hidden",
            False,
        )


def start_dashboard():
    """Start the dashboard app as a subprocess."""
    global dashboard_process

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_script = os.path.join(script_dir, "app.py")

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["DEMO_MODE"] = "true"
    env["DASHBOARD_PORT"] = str(DASHBOARD_PORT)

    # Start the dashboard process
    # NOTE: Do NOT capture stdout/stderr with PIPE - it causes the dashboard to hang
    # when it tries to print output during replay operations
    try:
        dashboard_process = subprocess.Popen(
            [sys.executable, dashboard_script],
            cwd=script_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            ),
        )
        print(f"✅ Dashboard started (PID: {dashboard_process.pid})")

        # Give the dashboard time to start
        time.sleep(3)

        # Check if process is still running
        if dashboard_process.poll() is None:
            print(f"📊 Dashboard is running at: {DASHBOARD_URL}")
            return True
        else:
            print("❌ Dashboard failed to start")
            return False

    except Exception as e:
        print(f"❌ Failed to start dashboard: {e}")
        return False


def stop_dashboard():
    """Stop the dashboard subprocess on exit."""
    global dashboard_process
    if dashboard_process and dashboard_process.poll() is None:
        print("\n🛑 Stopping dashboard...")
        try:
            if sys.platform == "win32":
                dashboard_process.terminate()
            else:
                dashboard_process.terminate()
            dashboard_process.wait(timeout=5)
            print("✅ Dashboard stopped")
        except Exception as e:
            print(f"⚠️ Error stopping dashboard: {e}")
            dashboard_process.kill()


# Register cleanup function
atexit.register(stop_dashboard)


def check_dashboard_running():
    """Check if dashboard is accessible."""
    try:
        response = requests.get(DASHBOARD_URL, timeout=2)
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🔐 TAFE Leak Detection - Login Portal")
    print("=" * 60)

    # Check if dashboard is already running
    if check_dashboard_running():
        print(f"📊 Dashboard already running at: {DASHBOARD_URL}")
    else:
        print("🚀 Starting dashboard...")
        start_dashboard()

    print("-" * 60)
    print(f"📍 Login Portal: http://127.0.0.1:{PORT}")
    print(f"📊 Dashboard:    {DASHBOARD_URL}")
    print(f"🔗 API Backend:  {API_URL}")
    print("-" * 60)
    print("💡 Use demo credentials: admin/admin123 or operator/operator123")
    print("💡 Press Ctrl+C to stop both servers")
    print("=" * 60)

    app.run(debug=DEBUG, host="127.0.0.1", port=PORT, use_reloader=False)

# %%
