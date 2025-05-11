from prompt_toolkit import  print_formatted_text
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from tabulate import tabulate
from datetime import datetime

response_style = Style.from_dict({
    "border":          "#777777",
    "title":           "#2d578b bold",
    "version":         "#666666",
    "separator":       "#4a90d9",
    "icon":            "#ffd700 bold",
    "input":           "#e6e6e6",
    "database":        "#98fb98 bold",
    "completion-menu.completion": "bg:#333333 #e6e6e6",
    "completion-menu.completion.current": "bg:#444444 #ffffff",
    "success": "#98fb98 bold",
    "error": "#ff4444 bold",
    "warning": "#ffd700 bold",
    "info": "#4a90d9 bold",
    "table": "#ffffff",
    "code": "#d3d3d3 italic",
})

def print_response(message, style_class="info"):
    print_formatted_text(
        HTML(f"<{style_class}>{message}</{style_class}>"),
        style=response_style
    )

def print_table(data, headers):
    formatted = tabulate(data, headers=headers, tablefmt="psql")
    print_response(f"\n{formatted}\n", "table")

def print_success(message):
    print_response(f"✓ {message}", "success")

def print_error(message):
    print_response(f"✗ {message}", "error")

def print_warning(message):
    print_response(f"⚠ {message}", "warning")

def print_code(code_snippet):
    print_response(f"```sql\n{code_snippet}\n```", "code")

def log_query_execution(query, execution_time):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_response(f"[{timestamp}] Query executed in {execution_time:.2f} seconds: {query}", "info")

def log_materialized_view(view_name, action):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_response(f"[{timestamp}] Materialized view {view_name} {action}.", "info")