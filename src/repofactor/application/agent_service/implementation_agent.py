from typing import Dict, List
import copy
import logging
from repofactor.application.services.lightning_ai_service import (
    LightningAIClient,
    LightningModel
)
from repofactor.domain.models.integration_models import ImplementationResult, ModifiedFile, Error

logger = logging.getLogger(__name__)

class ImplementationAgent:
    def __init__(self, ai_client: LightningAIClient):
        self.ai_client = ai_client

    def _backup_file(self, file_path: str, content: str) -> str:
        # Create a backup of original content (e.g. save to a .bak file)
        backup_path = file_path + ".bak"
        try:
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Backup created for {file_path} at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return ""

    def implement_changes(self, repo_content: Dict[str, str], instructions: str) -> ImplementationResult:
        """
        Implements code changes based on the given instructions.
        Uses AI client to generate changes, creates backups, and logs.

        Args:
            repo_content: Dict mapping file paths to their original content.
            instructions: User instructions guiding the implementation.

        Returns:
            ImplementationResult detailing success, modified files, errors and logs.
        """
        modified_files = []
        errors = []
        logs = []
        success = True

        current_content = copy.deepcopy(repo_content)

        for path, original in repo_content.items():
            try:
                # Build prompt for AI code generation
                prompt = f"Modify this code according to: {instructions}\n\nCode:\n{original}"
                modified = self.ai_client.generate_code(prompt)  # Replace with async if needed

                if modified and modified != original:
                    backup_path = self._backup_file(path, original)
                    modified_file = ModifiedFile(
                        path=path,
                        original_content=original,
                        modified_content=modified,
                        backup_path=backup_path,
                        changes_made=[f"Modified according to instructions."]
                    )
                    modified_files.append(modified_file)
                    current_content[path] = modified
                    logs.append(f"File '{path}' modified successfully.")
                else:
                    logs.append(f"No changes needed for file '{path}'.")

            except Exception as e:
                error_msg = f"Error processing file '{path}': {str(e)}"
                logger.error(error_msg)
                errors.append(Error(message=error_msg, file_path=path))
                success = False

        return ImplementationResult(
            success=success and len(errors) == 0,
            modified_files=modified_files,
            errors=errors,
            execution_logs=logs
        )
