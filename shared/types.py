from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class BugReport(BaseModel):
    id: str = Field(..., description="Unique identifier for the bug")
    filePath: Optional[str] = Field(None, description="Path to the file containing the bug")
    lineNumber: Optional[int] = Field(None, description="Line number where the bug occurred")
    errorMessage: str = Field(..., description="The main error message")
    stackTrace: Optional[str] = Field(None, description="The full stack trace if available")
    severity: Optional[str] = Field("error", description="Severity of the bug (e.g., error, warning)")

class CodeFix(BaseModel):
    bugId: str = Field(..., description="ID of the bug this fix addresses")
    filePath: str = Field(..., description="Path to the modified file")
    originalCode: Optional[str] = Field(None, description="Original code snippet that was replaced")
    fixedCode: Optional[str] = Field(None, description="The new code snippet applied")
    explanation: str = Field(..., description="Explanation of the fix")
    applied: bool = Field(..., description="Whether the fix was successfully applied to the file")
    error: Optional[str] = Field(None, description="Error message if application failed")

class PullRequest(BaseModel):
    url: str = Field(..., description="URL of the created pull request")
    number: int = Field(..., description="Pull request number")

class AnalysisPipeline(BaseModel):
    sessionId: str
    logSource: str
    startedAt: str
    status: str
    bugs: List[BugReport] = []
    fixes: List[CodeFix] = []
    pullRequest: Optional[PullRequest] = None
    error: Optional[str] = None
