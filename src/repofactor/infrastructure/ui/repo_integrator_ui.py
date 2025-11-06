# repo_integrator_ui.py
"""
RepoIntegrator - Modern Dark UI with Reflex
Beautiful, professional interface for GitHub repo integration
"""

import reflex as rx
from typing import Optional, List, Dict
from repofactor.application.services import RepoService
from repofactor.domain.models.integration_models import AnalysisResult



# ============================================================================
# State Management
# ============================================================================

class RepoIntegratorState(rx.State):
    """Application state"""
    
    # Search & Selection
    repo_search: str = ""
    selected_repo: Optional[dict] = None
    search_results: List[dict] = []
    is_searching: bool = False
    analysis_result_dict: Dict = {}
    
    @property
    def repo_service(self) -> RepoService:
        """Lazy-load repo service"""
        if not hasattr(self, '_repo_service_instance'):
            try:
                self._repo_service_instance = RepoService()
            except Exception as e:
                self.error_message = f"Failed to initialize repo service: {str(e)}"
                raise
        return self._repo_service_instance
    
    # User Input
    instructions: str = ""
    
    # Process State
    stage: str = "input"  # input, analyzing, results
    progress: int = 0
    current_step: str = ""
    
    # GitHub Connection
    github_connected: bool = False
    github_username: str = ""
    
    # Quota
    quota_remaining: int = 20
    quota_total: int = 20
    
    # Results
    affected_files: List[dict] = []
    
    # UI State
    is_loading: bool = False
    error_message: str = ""
    show_advanced: bool = False

    def set_repo_search(self, value: str):
        """Handle repo search input"""
        self.repo_search = value
        
        if len(value) > 2:
            self.search_repos(value)
        else:
            self.search_results = []
    
    async def search_repos(self, query: str):
        """Search GitHub repos via API"""
        results = await self.repo_service.search_and_validate(query)
        self.search_results = results

    async def analyze_repository(self):
        """Full analysis: clone + analyze"""
        result: AnalysisResult = await self._integrator.analyze_repository_content
        self.analysis_result_dict = result.to_dict()
        self.affected_files = result.affected_files
        self.stage = "results"
    
    def select_repo(self, repo: dict):
        """Select a repository"""
        self.selected_repo = repo
        self.repo_search = ""
        self.search_results = []
        self.error_message = ""
    
    def clear_repo_selection(self):
        """Clear selected repo"""
        self.selected_repo = None
    
    def set_instructions(self, value: str):
        """Update instructions"""
        self.instructions = value
    
    def toggle_advanced(self):
        """Toggle advanced options"""
        self.show_advanced = not self.show_advanced
    
    def connect_github(self):
        """Mock GitHub connection"""
        self.github_connected = True
        self.github_username = "user"
    
    def disconnect_github(self):
        """Disconnect GitHub"""
        self.github_connected = False
        self.github_username = ""
    
    async def analyze_repo(self):
        """Start analysis"""
        if not self.selected_repo or not self.instructions.strip():
            self.error_message = "Please select a repo and provide instructions"
            return
        
        if self.quota_remaining <= 0:
            self.error_message = "Quota exceeded. Please upgrade or wait for monthly reset."
            return
        
        self.is_loading = True
        self.stage = "analyzing"
        self.error_message = ""
        
        # Simulate analysis steps
        steps = [
            "Cloning repository...",
            "Analyzing code structure...",
            "Building dependency graph...",
            "Generating integration plan..."
        ]
        
        for i, step in enumerate(steps):
            self.current_step = step
            self.progress = int((i + 1) / len(steps) * 100)
            yield
            # In production: await asyncio.sleep(0.5)
        
        # Mock results
        self.affected_files = [
            {"path": "src/compression.py", "confidence": 95, "reason": "Main integration point"},
            {"path": "src/utils/tokenizer.py", "confidence": 87, "reason": "Uses compression functions"},
            {"path": "requirements.txt", "confidence": 100, "reason": "Add dependencies"},
        ]
        
        self.quota_remaining -= 1
        self.stage = "results"
        self.is_loading = False
    
    def reset_form(self):
        """Reset to initial state"""
        self.stage = "input"
        self.selected_repo = None
        self.instructions = ""
        self.error_message = ""
        self.affected_files = []


# ============================================================================
# Custom Theme & Styling
# ============================================================================

# Color palette
COLORS = {
    "bg_primary": "#0a0a0f",
    "bg_secondary": "#1a1a2e",
    "bg_card": "#16213e",
    "purple_500": "#8b5cf6",
    "purple_600": "#7c3aed",
    "pink_500": "#ec4899",
    "pink_600": "#db2777",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "border": "#2d3748",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
}

# Common styles
CARD_STYLE = {
    "background": COLORS["bg_card"],
    "border_radius": "16px",
    "padding": "24px",
    "border": f"1px solid {COLORS['border']}",
}

INPUT_STYLE = {
    "background": COLORS["bg_secondary"],
    "border": f"1px solid {COLORS['border']}",
    "border_radius": "12px",
    "padding": "12px 16px",
    "color": COLORS["text_primary"],
    "width": "100%",
    "_focus": {
        "outline": "none",
        "border_color": COLORS["purple_500"],
        "box_shadow": f"0 0 0 3px rgba(139, 92, 246, 0.1)"
    }
}

BUTTON_PRIMARY_STYLE = {
    "background": f"linear-gradient(135deg, {COLORS['purple_600']}, {COLORS['pink_600']})",
    "color": "white",
    "border_radius": "12px",
    "padding": "12px 24px",
    "font_weight": "600",
    "border": "none",
    "cursor": "pointer",
    "transition": "all 0.2s",
    "_hover": {
        "transform": "translateY(-2px)",
        "box_shadow": "0 10px 25px rgba(139, 92, 246, 0.3)"
    }
}


# ============================================================================
# UI Components
# ============================================================================

def header() -> rx.Component:
    """Top header with branding and quota"""
    return rx.box(
        rx.hstack(
            # Logo and title
            rx.hstack(
                rx.box(
                    "⚡",
                    font_size="32px",
                    background=f"linear-gradient(135deg, {COLORS['purple_500']}, {COLORS['pink_500']})",
                    border_radius="12px",
                    padding="8px",
                    width="48px",
                    height="48px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.heading(
                        "RepoIntegrator",
                        size="7",
                        background=f"linear-gradient(135deg, {COLORS['purple_500']}, {COLORS['pink_500']})",
                        background_clip="text",
                        color="transparent",
                        margin="0",
                    ),
                    rx.text(
                        "Powered by Lightning AI",
                        font_size="12px",
                        color=COLORS["text_muted"],
                        margin="0",
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
            ),
            
            # Quota badge
            rx.hstack(
                rx.box(
                    rx.hstack(
                        rx.text("⚡", font_size="16px"),
                        rx.text(
                            f"{RepoIntegratorState.quota_remaining}/{RepoIntegratorState.quota_total}",
                            font_weight="600",
                            font_size="14px",
                        ),
                        rx.text("this month", font_size="12px", color=COLORS["text_muted"]),
                        spacing="2",
                    ),
                    background=f"{COLORS['purple_600']}20",
                    border=f"1px solid {COLORS['purple_600']}50",
                    border_radius="10px",
                    padding="8px 16px",
                ),
                spacing="4",
            ),
            
            justify="between",
            width="100%",
        ),
        background=f"{COLORS['bg_primary']}cc",
        backdrop_filter="blur(10px)",
        border_bottom=f"1px solid {COLORS['border']}",
        padding="16px 32px",
        position="sticky",
        top="0",
        z_index="100",
    )


def hero_section() -> rx.Component:
    """Hero section with title and description"""
    return rx.vstack(
        rx.heading(
            rx.text(
                "Smart Integration",
                background=f"linear-gradient(135deg, {COLORS['purple_500']}, {COLORS['pink_500']})",
                background_clip="text",
                color="transparent",
            ),
            size="9",
            text_align="center",
            margin_bottom="8px",
        ),
        rx.heading(
            "of GitHub Repos",
            size="9",
            color=COLORS["text_secondary"],
            text_align="center",
            margin_bottom="16px",
        ),
        rx.text(
            "AI-powered code integration running on GPU in the cloud. Find a repo, describe what you need, and let AI do the work.",
            color=COLORS["text_secondary"],
            font_size="18px",
            text_align="center",
            max_width="700px",
        ),
        spacing="2",
        align_items="center",
        padding="48px 0",
    )


def github_connect_card() -> rx.Component:
    """GitHub connection card"""
    return rx.box(
        rx.hstack(
            rx.box(
                "🔗",
                font_size="32px",
                background=f"linear-gradient(135deg, {COLORS['purple_500']}, {COLORS['pink_500']})",
                border_radius="12px",
                padding="12px",
                width="48px",
                height="48px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.heading("Connect Your GitHub", size="5", margin="0"),
                rx.text(
                    "Access your private repos and push changes directly",
                    color=COLORS["text_secondary"],
                    font_size="14px",
                    margin="0",
                ),
                rx.cond(
                    RepoIntegratorState.github_connected,
                    rx.hstack(
                        rx.box(
                            rx.hstack(
                                rx.text("✓", color=COLORS["success"]),
                                rx.text(
                                    f"Connected as @{RepoIntegratorState.github_username}",
                                    font_size="14px",
                                ),
                                spacing="2",
                            ),
                            background=f"{COLORS['success']}20",
                            border=f"1px solid {COLORS['success']}50",
                            border_radius="8px",
                            padding="8px 12px",
                        ),
                        rx.button(
                            "Disconnect",
                            on_click=RepoIntegratorState.disconnect_github,
                            size="2",
                            variant="ghost",
                            color_scheme="gray",
                        ),
                        spacing="3",
                    ),
                    rx.button(
                        "Connect GitHub",
                        on_click=RepoIntegratorState.connect_github,
                        style=BUTTON_PRIMARY_STYLE,
                        size="2",
                    ),
                ),
                spacing="3",
                align_items="start",
            ),
            spacing="4",
            align_items="start",
        ),
        border_radius="16px",
        padding="24px",
        background=f"linear-gradient(135deg, {COLORS['purple_600']}10, {COLORS['pink_600']}10)",
        border=f"1px solid {COLORS['purple_600']}30",
    )


def repo_search_input() -> rx.Component:
    """Repository search with autocomplete"""
    return rx.vstack(
        rx.hstack(
            rx.text("🔍", font_size="20px"),
            rx.heading("Find a Repository", size="5"),
            spacing="2",
        ),
        
        # Search input
        rx.box(
            rx.input(
                placeholder="Search for repos... (e.g., microsoft/LLMLingua)",
                value=rx.cond(
                    RepoIntegratorState.selected_repo,
                    RepoIntegratorState.selected_repo["full_name"],
                    RepoIntegratorState.repo_search,
                ),
                on_change=RepoIntegratorState.set_repo_search,
                disabled=RepoIntegratorState.selected_repo != None,
                style=INPUT_STYLE,
            ),
            rx.cond(
                RepoIntegratorState.selected_repo,
                rx.button(
                    "✕",
                    on_click=RepoIntegratorState.clear_repo_selection,
                    position="absolute",
                    right="12px",
                    top="50%",
                    transform="translateY(-50%)",
                    background="transparent",
                    border="none",
                    cursor="pointer",
                    color=COLORS["text_muted"],
                    _hover={"color": COLORS["text_primary"]},
                ),
            ),
            position="relative",
            width="100%",
        ),
        
        # Search results dropdown
        rx.cond(
            (RepoIntegratorState.search_results.length() > 0) & (RepoIntegratorState.selected_repo == None),
            rx.box(
                rx.foreach(
                    RepoIntegratorState.search_results,
                    lambda repo: rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.text("📦", font_size="16px"),
                                rx.text(repo["full_name"], font_weight="600"),
                                spacing="2",
                            ),
                            rx.text(
                                repo["description"],
                                color=COLORS["text_secondary"],
                                font_size="14px",
                            ),
                            rx.hstack(
                                rx.text(f"⭐ {repo['stars']}", font_size="12px", color=COLORS["text_muted"]),
                                rx.text(f"• {repo['language']}", font_size="12px", color=COLORS["text_muted"]),
                                rx.text(f"• Updated {repo['updated']}", font_size="12px", color=COLORS["text_muted"]),
                                spacing="2",
                            ),
                            spacing="2",
                            align_items="start",
                        ),
                        on_click=lambda: RepoIntegratorState.select_repo(repo),
                        padding="16px",
                        cursor="pointer",
                        border_bottom=f"1px solid {COLORS['border']}",
                        _hover={"background": f"{COLORS['bg_secondary']}"},
                        transition="background 0.2s",
                    ),
                ),
                background=COLORS["bg_secondary"],
                border=f"1px solid {COLORS['border']}",
                border_radius="12px",
                margin_top="8px",
                max_height="300px",
                overflow_y="auto",
            ),
        ),
        
        # Selected repo display
        rx.cond(
            RepoIntegratorState.selected_repo,
            rx.box(
                rx.hstack(
                    rx.box(
                        "✓",
                        background=f"linear-gradient(135deg, {COLORS['purple_500']}, {COLORS['pink_500']})",
                        border_radius="8px",
                        padding="8px",
                        width="32px",
                        height="32px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        font_size="16px",
                    ),
                    rx.vstack(
                        rx.text(
                            RepoIntegratorState.selected_repo["full_name"],
                            font_weight="600",
                        ),
                        rx.text(
                            RepoIntegratorState.selected_repo["description"],
                            color=COLORS["text_secondary"],
                            font_size="14px",
                        ),
                        spacing="1",
                        align_items="start",
                    ),
                    spacing="3",
                    align_items="start",
                ),
                border_radius="16px",
                padding="24px",
                background=f"linear-gradient(135deg, {COLORS['purple_600']}10, {COLORS['pink_600']}10)",
                border=f"1px solid {COLORS['purple_600']}30",
                margin_top="16px",
            ),
        ),
        
        spacing="4",
        width="100%",
        align_items="start",
    )


def instructions_input() -> rx.Component:
    """Instructions textarea"""
    return rx.vstack(
        rx.hstack(
            rx.text("✨", font_size="20px"),
            rx.heading("What would you like to integrate?", size="5"),
            spacing="2",
        ),
        rx.text_area(
            placeholder="Describe what you want to do... For example:\n\n'Integrate the compression algorithm from LLMLingua into my project. Make it async and add proper error handling.'",
            value=RepoIntegratorState.instructions,
            on_change=RepoIntegratorState.set_instructions,
            rows="6",
            style={
                **INPUT_STYLE,
                "resize": "none",
                "font_family": "inherit",
            },
        ),
        rx.hstack(
            rx.text("Be specific about what features you need", font_size="12px", color=COLORS["text_muted"]),
            rx.text(f"{RepoIntegratorState.instructions.length()} characters", font_size="12px", color=COLORS["text_muted"]),
            justify="between",
            width="100%",
        ),
        spacing="3",
        width="100%",
        align_items="start",
    )


def analyze_button() -> rx.Component:
    """Main analyze button with smart messaging"""
    return rx.button(
        rx.cond(
            RepoIntegratorState.quota_remaining == 0,
            "⚠️ Quota Exceeded - Upgrade Required",
            rx.cond(
                RepoIntegratorState.selected_repo == None,
                "🔍 Select a repository first",
                rx.cond(
                    RepoIntegratorState.instructions.length() == 0,
                    "✍️ Add instructions to continue",
                    "🚀 Analyze with AI"
                ),
            ),
        ),
        on_click=RepoIntegratorState.analyze_repo,
        disabled=(RepoIntegratorState.selected_repo == None) | 
                 (RepoIntegratorState.instructions.length() == 0) | 
                 (RepoIntegratorState.quota_remaining == 0),
        style={
            **BUTTON_PRIMARY_STYLE,
            "width": "100%",
            "padding": "16px",
            "font_size": "16px",
        },
        loading=RepoIntegratorState.is_loading,
    )


def input_stage() -> rx.Component:
    """Main input stage"""
    return rx.vstack(
        hero_section(),
        github_connect_card(),
        repo_search_input(),
        instructions_input(),
        
        rx.cond(
            RepoIntegratorState.error_message != "",
            rx.callout(
                RepoIntegratorState.error_message,
                icon="triangle_alert",
                color_scheme="red",
            ),
        ),
        
        analyze_button(),
        
        # Footer info
        rx.vstack(
            rx.text("⚡ Powered by Lightning AI GPU Studio", font_size="14px", color=COLORS["text_muted"]),
            rx.text("🔒 Your code never leaves your machine • Changes are reviewed before applying", 
                   font_size="12px", 
                   color=COLORS["text_muted"],
                   text_align="center"),
            spacing="2",
            align_items="center",
        ),
        
        spacing="8",
        width="100%",
        max_width="800px",
        margin="0 auto",
    )


def analyzing_stage() -> rx.Component:
    """Analysis in progress"""
    return rx.vstack(
        rx.box(
            rx.box(
                rx.spinner(size="3", color=COLORS["purple_500"]),
                background=f"linear-gradient(135deg, {COLORS['purple_600']}20, {COLORS['pink_600']}20)",
                border_radius="16px",
                padding="32px",
            ),
            display="flex",
            justify_content="center",
        ),
        rx.heading(RepoIntegratorState.current_step, size="7", text_align="center"),
        rx.text("Running AI analysis on GPU in the cloud", color=COLORS["text_secondary"], text_align="center"),
        rx.progress(
            value=RepoIntegratorState.progress,
            width="400px",
            max=100,
            color_scheme="purple",
        ),
        rx.text(f"{RepoIntegratorState.progress}%", color=COLORS["text_muted"]),
        spacing="6",
        align_items="center",
        padding="80px 0",
    )


def results_stage() -> rx.Component:
    """Results display"""
    return rx.vstack(
        rx.box(
            rx.text("✓", font_size="48px", color=COLORS["success"]),
            background=f"{COLORS['success']}20",
            border_radius="16px",
            padding="16px",
        ),
        rx.heading("Analysis Complete!", size="7"),
        rx.text(
            f"Found {RepoIntegratorState.affected_files.length()} files that need changes",
            color=COLORS["text_secondary"],
        ),
        
        rx.box(
            rx.vstack(
                rx.heading("Integration Plan", size="5", margin_bottom="16px"),
                rx.foreach(
                    RepoIntegratorState.affected_files,
                    lambda file, idx: rx.hstack(
                        rx.box(
                            str(idx + 1),
                            background=f"{COLORS['purple_600']}20",
                            border_radius="8px",
                            padding="8px 12px",
                            font_weight="600",
                            font_size="14px",
                        ),
                        rx.vstack(
                            rx.text(file["path"], font_family="monospace", font_size="14px"),
                            rx.text(file["reason"], color=COLORS["text_secondary"], font_size="12px"),
                            spacing="1",
                            align_items="start",
                        ),
                        rx.badge(
                            f"{file['confidence']}%",
                            color_scheme="green",
                        ),
                        justify="between",
                        width="100%",
                        padding="12px",
                        background=f"{COLORS['bg_secondary']}",
                        border_radius="8px",
                    ),
                ),
                spacing="3",
            ),
            border_radius="16px",
            padding="24px",
            background=COLORS["bg_card"],
            border=f"1px solid {COLORS['border']}",
            width="100%",
            max_width="700px",
        ),
        
        rx.button(
            "Apply Changes",
            on_click=RepoIntegratorState.reset_form,
            style={
                **BUTTON_PRIMARY_STYLE,
                "width": "300px",
                "padding": "16px",
            },
        ),
        
        spacing="6",
        align_items="center",
        padding="40px 0",
    )


def index() -> rx.Component:
    """Main page"""
    return rx.box(
        header(),
        rx.box(
            rx.match(
                RepoIntegratorState.stage,
                ("input", input_stage()),
                ("analyzing", analyzing_stage()),
                ("results", results_stage()),
            ),
            padding="32px",
        ),
        background=f"linear-gradient(to bottom right, {COLORS['bg_primary']}, {COLORS['bg_secondary']})",
        min_height="100vh",
        color=COLORS["text_primary"],
    )


# App configuration
app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="purple",
        gray_color="slate",
        radius="large",
    ),
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap",
    ],
    style={
        "font_family": "'Inter', sans-serif",
    }
)

app.add_page(index, route="/", title="RepoIntegrator | Smart GitHub Integration")