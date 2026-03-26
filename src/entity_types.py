"""Custom Pydantic entity/edge types for developer memory ontology.

These types guide Graphiti's LLM extraction — when ingesting episodes,
entities are classified into these categories automatically.
"""

from pydantic import BaseModel, Field

# --- Entity Types (nodes in the knowledge graph) ---

class CodePattern(BaseModel):
    """A coding pattern, technique, or solution discovered during development."""
    language: str | None = Field(default=None, description="Programming language")
    framework: str | None = Field(default=None, description="Related framework")


class TechDecision(BaseModel):
    """A technology choice, architectural decision, or design trade-off."""
    rationale: str | None = Field(default=None, description="Why this was decided")
    alternatives: str | None = Field(default=None, description="Other options considered")


class ProjectContext(BaseModel):
    """Project-level context: goals, constraints, deadlines, status."""
    priority: str | None = Field(default=None, description="Priority level")
    status: str | None = Field(default=None, description="Current status")


class Person(BaseModel):
    """A person mentioned in context (team member, stakeholder, user)."""
    role: str | None = Field(default=None, description="Role or title")


class Tool(BaseModel):
    """A software tool, library, framework, or service."""
    version: str | None = Field(default=None, description="Version if known")
    purpose: str | None = Field(default=None, description="What it's used for")


class Concept(BaseModel):
    """A technical concept, domain term, or abstract idea."""
    domain: str | None = Field(default=None, description="Knowledge domain")


class BugReport(BaseModel):
    """A bug, issue, or error encountered during development."""
    severity: str | None = Field(default=None, description="Severity: low/medium/high/critical")
    status: str | None = Field(default=None, description="Status: open/fixed/wontfix")


class Requirement(BaseModel):
    """A functional or non-functional requirement."""
    priority: str | None = Field(default=None, description="Priority: must/should/could/wont")


# --- Registries passed to Graphiti add_episode() ---

ENTITY_TYPES: dict[str, type[BaseModel]] = {
    "CodePattern": CodePattern,
    "TechDecision": TechDecision,
    "ProjectContext": ProjectContext,
    "Person": Person,
    "Tool": Tool,
    "Concept": Concept,
    "BugReport": BugReport,
    "Requirement": Requirement,
}
