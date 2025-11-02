# repo_integrator_ui.py
"""
RepoIntegrator UI built with Reflex
Integrated with Lightning AI for model inference
"""

import reflex as rx
from typing import Optional, List, Dict
import asyncio

class FileAnalysis(rx.Base):
    path: str
    reason: str
    confidence: int
    status: str = "pending"

class AnalysisResult(rx.Base):
    main_file: str
    affected_files: List[FileAnalysis]
    dependencies: List[str]
    estimated_changes: str
    risks: List[str]
    diff_preview: Optional[str] = None

class State(rx.State):
    # Form inputs
    repo_url: str = ""
    target_file: str = ""
    instructions: str = ""
    selected_model: str = "CODE_LLAMA_34B" # TODO: Add more models and not hard coded!
    
    # Process state
    stage: str = "input"
    progress: int = 0
    current_step: str = ""
    
    # Analysis results
    analysis: Optional[AnalysisResult] = None
    selected_files: List[str] = []
    
    # Lightning AI specific
    remaining_quota: int = 20
    model_info: str = "CodeLlama 34B - Best for code integration"
    
    # UI state
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    def set_repo_url(self, value: str):
        self.repo_url = value
        
    def set_target_file(self, value: str):
        self.target_file = value
        
    def set_instructions(self, value: str):
        self.instructions = value
    
    def set_model(self, value: str):
        self.selected_model = value
        
        # Update model info TODO: Add more models and not hard coded!
        model_descriptions = {
            "CODE_LLAMA_34B": "CodeLlama 34B - Best for code integration",
            "DEEPSEEK_CODER_33B": "DeepSeek Coder 33B - Excellent for refactoring",
            "STARCODER2_15B": "StarCoder2 15B - Fast and efficient",
            "LLAMA_3_70B": "Llama 3 70B - General purpose, very capable",
            "MIXTRAL_8X7B": "Mixtral 8x7B - Fast inference"
        }
        self.model_info = model_descriptions.get(value, "Advanced model")

    async def analyze_repo(self):
        """Main analysis workflow using Lightning AI"""
        if not self.repo_url:
            self.error_message = "Please enter a repository URL"
            return
            
        self.is_loading = True
        self.stage = "analyzing"
        self.error_message = ""
        self.progress = 0
        
        try:
            # Step 1: Clone repo
            self.current_step = "cloning repository from github..."
            self.progress = 15
            yield
            await asyncio.sleep(0.5)
            
            # Step 2: Extract key files
            self.current_step = "extracting relevant files..."
            self.progress = 30
            yield
            await asyncio.sleep(0.5)
            
            # Step 3: Call Lightning AI for analysis
            self.current_step = f"analyzing with {self.model_info}..."
            self.progress = 50
            yield
            
            # Import Lightning AI service
            from services.lightning_ai_service import analyze_repo_with_lightning
            
            result = await analyze_repo_with_lightning(
                repo_url=self.repo_url,
                target_file=self.target_file,
                instructions=self.instructions
            )
            
            self.progress = 75
            self.current_step = "analyzing results..."
            yield
            await asyncio.sleep(0.3)
            
            # Format results
            self.analysis = AnalysisResult( # TODO: remove string fields
                main_file=result.get("main_file", "src/main.py"),
                affected_files=[
                    FileAnalysis(**f) if isinstance(f, dict) else FileAnalysis(
                        path=f.get("path", ""),
                        reason=f.get("reason", ""),
                        confidence=f.get("confidence", 70),
                        status="done"
                    )
                    for f in result.get("affected_files", [])
                ],
                dependencies=result.get("dependencies", []),
                estimated_changes=result.get("estimated_changes", "basic changes"),
                risks=result.get("risks", [])
            )
            
            self.selected_files = [f.path for f in self.analysis.affected_files]
            self.progress = 100
            self.current_step = "completed"
            
            # Update quota (mock - in production get from API)
            self.remaining_quota -= 1
            
            await asyncio.sleep(0.3)
            self.stage = "reviewing"
            
        except Exception as e:
            self.error_message = f"error: {str(e)}"
            self.stage = "input"
        finally:
            self.is_loading = False

    def toggle_file_selection(self, file_path: str):
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
        else:
            self.selected_files.append(file_path)

    async def apply_changes(self):
        """Apply the changes using Lightning AI for code generation"""
        self.is_loading = True
        self.stage = "applying"
        self.progress = 0
        
        try:
            from services.lightning_ai_service import CodeAnalysisAgent
            
            agent = CodeAnalysisAgent()
            
            for i, file_path in enumerate(self.selected_files):
                self.current_step = f"updating {file_path} with Lightning AI..."
                self.progress = int((i + 1) / len(self.selected_files) * 100)
                yield
                
                # Generate code changes
                # In production: load original code, generate changes, apply
                await asyncio.sleep(0.5)
            
            await agent.close()
            
            self.stage = "done"
            self.success_message = f"updated {len(self.selected_files)} files!"
            self.remaining_quota -= len(self.selected_files)
            
        except Exception as e:
            self.error_message = f"error: {str(e)}"
            self.stage = "reviewing"
        finally:
            self.is_loading = False

    def reset(self):
        self.stage = "input"
        self.repo_url = ""
        self.target_file = ""
        self.instructions = ""
        self.analysis = None
        self.selected_files = []
        self.progress = 0
        self.current_step = ""
        self.error_message = ""
        self.success_message = ""


def quota_badge() -> rx.Component:
    """Show remaining Lightning AI quota"""
    return rx.badge(
        rx.hstack(
            rx.icon("zap", size=14),
            rx.text(f"{State.remaining_quota}/20 calls remaining this month"), # TODO: get from API and remmber change in prod!
            spacing="1"
        ),
        color_scheme="orange" if State.remaining_quota < 5 else "green",
        variant="soft"
    )


def model_selector() -> rx.Component:
    """Model selection dropdown"""
    return rx.vstack(
        rx.hstack(
            rx.icon("cpu", size=16),
            rx.text("select model", font_weight="medium"),
            spacing="2"
        ),
        rx.select( # TODO: change to strings file!
            ["CODE_LLAMA_34B", "DEEPSEEK_CODER_33B", "STARCODER2_15B", 
             "LLAMA_3_70B", "MIXTRAL_8X7B"],
            value=State.selected_model,
            on_change=State.set_model,
            size="3"
        ),
        rx.text(State.model_info, font_size="sm", color="gray.500"),
        align="start",
        spacing="2",
        width="100%"
    )


def confidence_badge(confidence: int) -> rx.Component:
    if confidence > 80:
        color_scheme = "green"
    elif confidence > 60:
        color_scheme = "yellow"
    else:
        color_scheme = "orange"
    
    return rx.badge(
        f"{confidence}%",
        color_scheme=color_scheme,
        variant="solid"
    )


def file_card(file: FileAnalysis, is_selected: bool) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.checkbox(
                checked=is_selected,
                on_change=lambda _: State.toggle_file_selection(file.path),
                color_scheme="purple"
            ),
            rx.vstack(
                rx.hstack(
                    rx.icon("file-code", size=16, color="purple"),
                    rx.code(file.path, font_size="sm"),
                    align="center",
                    spacing="2"
                ),
                rx.text(file.reason, font_size="sm", color="gray.500"),
                align="start",
                spacing="1",
                flex="1"
            ),
            confidence_badge(file.confidence),
            align="center",
            spacing="4",
            width="100%"
        ),
        border="1px solid",
        border_color="gray.200",
        border_radius="lg",
        padding="4",
        bg="white",
        _hover={"border_color": "purple.300", "shadow": "sm"},
        transition="all 0.2s"
    )


def input_stage() -> rx.Component:
    return rx.vstack(
        # Quota indicator
        quota_badge(),
        
        # Model selector
        model_selector(),
        
        # Repo URL
        rx.vstack(
            rx.hstack(
                rx.icon("github", size=16),
                rx.text("link to GitHub repository", font_weight="medium"),
                spacing="2"
            ),
            rx.input(
                placeholder="https://github.com/microsoft/LLMLingua",
                value=State.repo_url,
                on_change=State.set_repo_url,
                width="100%",
                size="3"
            ),
            align="start",
            spacing="2",
            width="100%"
        ),
        
        # Target file
        rx.vstack(
            rx.hstack(
                rx.icon("file-code", size=16),
                rx.text("my target file", font_weight="medium"),
                spacing="2"
            ),
            rx.input(
                placeholder="src/my_compression.py",
                value=State.target_file,
                on_change=State.set_target_file,
                width="100%",
                size="3"
            ),
            align="start",
            spacing="2",
            width="100%"
        ),
        
        # Instructions
        rx.vstack(
            rx.hstack(
                rx.icon("zap", size=16),
                rx.text("my instructions", font_weight="medium"),
                spacing="2"
            ),
            rx.text_area(
                placeholder="for example: 'merge compression algorithm, make it async, add error handling'",
                value=State.instructions,
                on_change=State.set_instructions,
                width="100%",
                rows="4",
                size="3"
            ),
            align="start",
            spacing="2",
            width="100%"
        ),
        
        # Error message
        rx.cond(
            State.error_message != "",
            rx.callout(
                State.error_message,
                icon="alert-circle",
                color_scheme="red"
            )
        ),
        
        # Analyze button
        rx.button(
            rx.hstack(
                rx.icon("sparkles", size=16),
                rx.text("analyze with AI"),
                spacing="2"
            ),
            on_click=State.analyze_repo,
            disabled=(State.repo_url == "") | (State.remaining_quota <= 0),
            width="100%",
            size="3",
            color_scheme="purple",
            loading=State.is_loading
        ),
        
        # Quota warning
        rx.cond(
            State.remaining_quota <= 3,
            rx.callout(
                "you have few calls remaining this month. consider upgrading to Lightning AI",
                icon="alert-triangle",
                color_scheme="orange",
                size="1"
            )
        ),
        
        spacing="5",
        width="100%"
    )


def analyzing_stage() -> rx.Component:
    return rx.vstack(
        rx.icon("loader-2", size=48, color="purple", class_name="animate-spin"),
        rx.heading(State.current_step, size="6"),
        rx.text("מופעל על GPU של Lightning AI ☁️", color="gray.500", font_size="sm"),
        rx.progress(value=State.progress, width="100%", color_scheme="purple"),
        rx.text(f"{State.progress}%", color="gray.500"),
        spacing="4",
        align="center",
        padding="12"
    )


def reviewing_stage() -> rx.Component:
    return rx.vstack(
        rx.callout(
            rx.vstack(
                rx.text("תכנית השינויים", font_weight="bold"),
                rx.text(State.analysis.estimated_changes),
                spacing="1"
            ),
            icon="info",
            color_scheme="blue"
        ),
        
        rx.vstack(
            rx.heading("affected files:", size="5"),
            rx.foreach(
                State.analysis.affected_files,
                lambda file: file_card(
                    file,
                    State.selected_files.contains(file.path)
                )
            ),
            spacing="3",
            width="100%"
        ),
        
        rx.cond(
            State.analysis.risks.length() > 0,
            rx.callout(
                rx.vstack(
                    rx.text("risks:", font_weight="bold"),
                    rx.unordered_list(
                        *[rx.list_item(risk) for risk in State.analysis.risks],
                        spacing="1"
                    ),
                    spacing="2"
                ),
                icon="alert-triangle",
                color_scheme="yellow"
            )
        ),
        
        rx.hstack(
            rx.button(
                "return to input stage",
                on_click=State.reset,
                variant="outline",
                color_scheme="gray"
            ),
            rx.button(
                rx.hstack(
                    rx.icon("check", size=16),
                    rx.text(f"apply changes ({State.selected_files.length()} files)"),
                    spacing="2"
                ),
                on_click=State.apply_changes,
                color_scheme="green",
                disabled=State.selected_files.length() == 0,
                loading=State.is_loading
            ),
            spacing="3",
            width="100%",
            justify="end"
        ),
        
        spacing="6",
        width="100%"
    )


def applying_stage() -> rx.Component:
    return rx.vstack(
        rx.icon("loader-2", size=48, color="green", class_name="animate-spin"),
        rx.heading("applying changes...", size="6"),
        rx.text(State.current_step, color="gray.500"),
        rx.progress(value=State.progress, width="100%", color_scheme="green"),
        spacing="4",
        align="center",
        padding="12"
    )


def done_stage() -> rx.Component:
    return rx.vstack(
        rx.icon("check-circle", size=64, color="green"),
        rx.heading("done successfully! 🎉", size="7"),
        rx.text(State.success_message, font_size="lg", color="gray.600"),
        quota_badge(),
        rx.button(
            "start new integration",
            on_click=State.reset,
            color_scheme="purple",
            size="3"
        ),
        spacing="4",
        align="center",
        padding="12"
    )


def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            # Header
            rx.vstack(
                rx.hstack(
                    rx.icon("zap", size=32, color="yellow"),
                    rx.heading("RepoIntegrator", size="9"),
                    rx.badge("Powered by Lightning AI", color_scheme="purple"),
                    spacing="3",
                    align="center"
                ),
                rx.text(
                    "smart integration of GitHub repos into your code with GPU in the cloud",
                    font_size="xl",
                    color="gray.600",
                    text_align="center"
                ),
                spacing="2",
                align="center",
                padding_bottom="6"
            ),
            
            # Main card
            rx.box(
                rx.match(
                    State.stage,
                    ("input", input_stage()),
                    ("analyzing", analyzing_stage()),
                    ("reviewing", reviewing_stage()),
                    ("applying", applying_stage()),
                    ("done", done_stage()),
                ),
                bg="white",
                border="1px solid",
                border_color="gray.200",
                border_radius="xl",
                padding="8",
                shadow="xl",
                width="100%"
            ),
            
            # Footer #TODO: change to strings file! AND remove in production
            rx.text(
                "💡 Lightning AI provides 20 free calls per month | GPU Studio",
                font_size="sm",
                color="gray.500",
                text_align="center"
            ),
            
            spacing="8",
            align="center",
            padding_y="12"
        ),
        max_width="4xl",
        center_content=True
    )


app = rx.App(
    theme=rx.theme(
        appearance="light",
        accent_color="purple"
    )
)
app.add_page(index, route="/", title="RepoIntegrator | Lightning AI")