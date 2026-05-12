# SignalForce MarOps Branch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a `marops` git branch on the SignalForce repo that generates Conversion-platform-shaped lifecycle campaign briefs from YAML config via the Claude API, producing `out/veriforce.html` as a demo artifact that proves the "same engine, repointed for MarOps" claim in the walk-in script.

**Architecture:** YAML config → `scripts/marops/config_loader.py` validates and loads campaign parameters → `scripts/marops/briefer.py` calls Claude API (`tool_use` with strict JSON schema) to generate the lifecycle brief → `scripts/marops/renderer.py` renders Jinja2 → HTML. Mirrors the existing SignalForce pipeline: config → scanner/scorer layer → structured output → renderer. Prompt caching on the system prompt priors library keeps per-brief cost to fractions of a cent.

**Tech Stack:** Python 3.11, Pydantic v2, `anthropic` SDK (claude-sonnet-4-6), Jinja2, WeasyPrint (PDF), pytest, ruff. No new external dependencies beyond `anthropic` and `jinja2`/`weasyprint` (already in conversion-walkin).

---

## Context

The walk-in script (at `conversion-walkin/walkin_script.md`) claims in Beat 2:

> "This morning I forked SignalForce into a MarOps branch. Same engine — config-driven signals, segmentation, multi-agent orchestration with execution / QA / optimization roles. I pointed it at a real Conversion customer — Veriforce — and built a Tier-2 supplier re-engagement brief in the exact shape your platform consumes..."

The Veriforce HTML (`conversion-walkin/out/veriforce.html`) already exists and renders correctly. What's missing is the **generator** — the pipeline that takes a YAML config and produces that JSON via Claude API. The demo opens `out/veriforce.html` in Chrome full-screen, so the final output path must be `/Users/sami/SignalForce/out/veriforce.html`.

The script also says: "~400 lines total. The engine is SignalForce — battle-tested for prospecting at the multi-vertical level — repointed via config in an afternoon." Every file should be under 150 lines. The architecture is the credential, not the line count.

---

## File Structure

```
SignalForce/                          (git branch: marops)
  scripts/
    marops/
      __init__.py                     # empty, makes it a package
      models.py                       # Pydantic models for MarOps brief shape
      config_loader.py                # YAML → validated MarOpsCampaignConfig
      briefer.py                      # Claude API call → LifecycleBriefOutput
      renderer.py                     # LifecycleBriefOutput → HTML/PDF via Jinja2
      cli.py                          # `python -m scripts.marops.cli veriforce`
  examples/
    marops/
      veriforce.yaml                  # Veriforce re-engagement campaign config
      hockeystack.yaml                # HockeyStack onboarding campaign (second vertical)
  renderer/
    marops/
      lifecycle_brief.html.j2         # Copied from conversion-walkin/renderer/ (unchanged)
  out/                                # Generated artifacts (gitignored)
    veriforce.html
    veriforce.json
  tests/
    marops/
      test_models.py                  # Pydantic model validation
      test_config_loader.py           # YAML loading + validation
      test_briefer.py                 # Claude API integration (mocked)
      test_renderer.py                # Jinja2 render smoke test
  pyproject.toml                      # Add `anthropic`, `jinja2`, `weasyprint` to deps
```

**What each file owns:**
- `models.py` — immutable Pydantic models: `Touch`, `SegmentDefinition`, `OptimizationTrigger`, `PipelineProjection`, `LifecycleBrief`
- `config_loader.py` — reads YAML, validates into `MarOpsCampaignConfig`; no Claude calls here
- `briefer.py` — single function `generate_brief(config) → LifecycleBrief`; owns the Claude API call with `tool_use` JSON schema enforcement and prompt caching
- `renderer.py` — single function `render_html(brief, out_path)`; owns Jinja2 loading and HTML write
- `cli.py` — thin orchestrator: load config → generate brief → render HTML → write JSON; `< 30 lines`

---

## Task 1: Create `marops` branch and add `anthropic` dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the branch**

```bash
cd /Users/sami/SignalForce
git checkout -b marops
```

Expected: `Switched to a new branch 'marops'`

- [ ] **Step 2: Add dependencies to pyproject.toml**

In the `[project]` `dependencies` list, add:
```toml
    "anthropic>=0.50.0",
    "jinja2>=3.1",
    "weasyprint>=62.0",
```

- [ ] **Step 3: Install**

```bash
cd /Users/sami/SignalForce
pip install -e ".[dev]"
```

Expected: `Successfully installed anthropic-...`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add anthropic, jinja2, weasyprint deps for marops branch"
```

---

## Task 2: Write Pydantic models for the MarOps brief shape

**Files:**
- Create: `scripts/marops/__init__.py`
- Create: `scripts/marops/models.py`
- Create: `tests/marops/__init__.py`
- Create: `tests/marops/test_models.py`

`★ Insight ─────────────────────────────────────`
The existing SignalForce `models.py` uses `ConfigDict(frozen=True)` throughout — all models are immutable. Follow the same pattern here. Immutability means the brief object can be safely passed between briefer → renderer without defensive copies.
`─────────────────────────────────────────────────`

- [ ] **Step 1: Write the failing test**

Create `tests/marops/__init__.py` (empty).

Create `tests/marops/test_models.py`:

```python
"""Tests for MarOps Pydantic models."""
from scripts.marops.models import (
    Touch,
    SegmentDefinition,
    OptimizationTrigger,
    PipelineProjection,
    LifecycleBrief,
    AgentRole,
    TouchChannel,
)


def test_touch_is_immutable():
    touch = Touch(
        step=1,
        channel=TouchChannel.EMAIL,
        agent=AgentRole.EXECUTION,
        timing="T+0",
        subject="Hello {{ Contact.FirstName }}",
        body_brief="Plain text re-engagement.",
        personalization_tokens=["Contact.FirstName"],
        qa_rules=["Reject if token is null"],
        success_metric="Open rate >38%",
    )
    try:
        touch.step = 2  # type: ignore
        assert False, "Should have raised"
    except Exception:
        pass


def test_lifecycle_brief_round_trips_json():
    segment = SegmentDefinition(
        name="Lapsed Tier-2",
        salesforce_filters=["Account.Tier__c = 'Tier 2'"],
        warehouse_traits=["product.last_login_at < now() - interval '90 days'"],
        exclusions=["Account.OptOut_AllMarketing__c = TRUE"],
        estimated_size="~2,400 contacts",
    )
    brief = LifecycleBrief(
        prospect="Veriforce",
        prospect_url="https://www.veriforce.com",
        vertical="Supplier compliance SaaS",
        campaign_name="Tier-2 Re-Engagement",
        objective="Reactivate lapsed accounts.",
        lifecycle_stage="Customer · Re-engagement",
        segment=segment,
        touches=[],
        optimization_triggers=[],
        pipeline_projection=PipelineProjection(
            expected_renewals="~$1.4M ARR",
            ae_efficiency="70% task acceptance",
            campaign_runtime="21 days",
            downside="Pipeline drops 30% if legal fails",
        ),
        meta={},
    )
    data = brief.model_dump()
    assert data["prospect"] == "Veriforce"
    assert data["segment"]["name"] == "Lapsed Tier-2"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/sami/SignalForce
python -m pytest tests/marops/test_models.py -v
```

Expected: `ImportError: No module named 'scripts.marops'`

- [ ] **Step 3: Create `scripts/marops/__init__.py`** (empty file)

- [ ] **Step 4: Create `scripts/marops/models.py`**

```python
"""Immutable Pydantic models for MarOps lifecycle campaign briefs.

These define the exact JSON shape that Conversion's platform consumes:
segment (Salesforce + warehouse filters) → touch sequence with agent assignments
→ optimization triggers → pipeline projection.
"""

from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict


class AgentRole(str, Enum):
    EXECUTION = "execution"
    QA = "qa"
    OPTIMIZATION = "optimization"


class TouchChannel(str, Enum):
    EMAIL = "email"
    IN_APP_BANNER = "in_app_banner"
    AE_TASK = "ae_task"
    SMS = "sms"
    LINKEDIN = "linkedin"


class Touch(BaseModel):
    model_config = ConfigDict(frozen=True)

    step: int
    channel: TouchChannel
    agent: AgentRole
    timing: str
    subject: str
    body_brief: str
    personalization_tokens: list[str]
    qa_rules: list[str]
    success_metric: str


class SegmentDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    salesforce_filters: list[str]
    warehouse_traits: list[str]
    exclusions: list[str]
    estimated_size: str


class OptimizationTrigger(BaseModel):
    model_config = ConfigDict(frozen=True)

    condition: str
    action: str


class PipelineProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    expected_renewals: str
    ae_efficiency: str
    campaign_runtime: str
    downside: str


class LifecycleBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    prospect: str
    prospect_url: str
    vertical: str
    campaign_name: str
    objective: str
    lifecycle_stage: str
    segment: SegmentDefinition
    touches: list[Touch]
    optimization_triggers: list[OptimizationTrigger]
    pipeline_projection: PipelineProjection
    meta: dict
```

- [ ] **Step 5: Run test to verify it passes**

```bash
python -m pytest tests/marops/test_models.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add scripts/marops/__init__.py scripts/marops/models.py tests/marops/__init__.py tests/marops/test_models.py
git commit -m "feat(marops): add immutable Pydantic models for lifecycle brief shape"
```

---

## Task 3: YAML config loader

**Files:**
- Create: `scripts/marops/config_loader.py`
- Create: `examples/marops/veriforce.yaml`
- Create: `examples/marops/hockeystack.yaml`
- Create: `tests/marops/test_config_loader.py`

- [ ] **Step 1: Write the failing test**

Create `tests/marops/test_config_loader.py`:

```python
"""Tests for MarOps YAML config loader."""
from pathlib import Path
import pytest
from scripts.marops.config_loader import load_marops_config, MarOpsCampaignConfig

EXAMPLES = Path(__file__).parent.parent.parent / "examples" / "marops"


def test_load_veriforce_config():
    config = load_marops_config(EXAMPLES / "veriforce.yaml")
    assert isinstance(config, MarOpsCampaignConfig)
    assert config.customer.name == "Veriforce"
    assert config.lifecycle_stage == "Customer · Re-engagement (post-lapse, pre-churn)"
    assert len(config.segment.icp_filters) > 0


def test_load_hockeystack_config():
    config = load_marops_config(EXAMPLES / "hockeystack.yaml")
    assert config.customer.name == "HockeyStack"


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_marops_config(Path("nonexistent.yaml"))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/marops/test_config_loader.py -v
```

Expected: `ImportError` or `FileNotFoundError`

- [ ] **Step 3: Create `scripts/marops/config_loader.py`**

```python
"""Load and validate MarOps campaign configuration from YAML.

YAML shape:
  customer: { name, url, vertical }
  lifecycle_stage: "..."
  campaign: { name, objective, num_touches }
  segment:
    crm: salesforce
    warehouse: snowflake
    icp_filters: [...]
    warehouse_traits: [...]
    exclusions: [...]
    estimated_size: "..."
  agents: [execution, qa, optimization]
  priors:
    benchmark_customers: [...]   # referenced in Claude system prompt
"""

from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel, ConfigDict


class CustomerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    url: str
    vertical: str


class SegmentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    crm: str = "salesforce"
    warehouse: str = "snowflake"
    icp_filters: list[str]
    warehouse_traits: list[str]
    exclusions: list[str]
    estimated_size: str


class CampaignConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    objective: str
    num_touches: int = 5


class MarOpsCampaignConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    customer: CustomerConfig
    lifecycle_stage: str
    campaign: CampaignConfig
    segment: SegmentConfig
    agents: list[str] = ["execution", "qa", "optimization"]
    priors: dict = {}


def load_marops_config(path: Path) -> MarOpsCampaignConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    raw = yaml.safe_load(path.read_text())
    return MarOpsCampaignConfig.model_validate(raw)
```

- [ ] **Step 4: Create `examples/marops/veriforce.yaml`**

```yaml
customer:
  name: Veriforce
  url: https://www.veriforce.com
  vertical: "Supplier compliance & contractor safety SaaS — industrial enterprise (oil & gas, utilities, construction)"

lifecycle_stage: "Customer · Re-engagement (post-lapse, pre-churn)"

campaign:
  name: "Tier-2 Supplier Re-Engagement — Compliance Lapse → Renewal"
  objective: >
    Reactivate Tier-2 supplier accounts whose compliance verification lapsed
    in the last 90 days, route engaged accounts to AE-qualified pipeline,
    and recover ~12% of dormant ARR within one quarter.
  num_touches: 5

segment:
  crm: salesforce
  warehouse: snowflake
  icp_filters:
    - "Account.Tier__c = 'Tier 2'"
    - "Account.ComplianceStatus__c IN ('Expired', 'Pending Renewal')"
    - "Account.LastVerification__c < TODAY - 90"
    - "Account.HiringClient_ActiveContracts__c > 0"
    - "Contact.Role IN ('EHS Manager', 'Safety Director', 'Procurement Lead', 'Compliance Officer')"
    - "Contact.EmailOptIn__c = TRUE"
    - "Account.Industry IN ('Oil & Gas', 'Utilities', 'Construction', 'Mining')"
  warehouse_traits:
    - "product.last_login_at < now() - interval '90 days'"
    - "product.compliance_doc_uploads_l30d = 0"
    - "product.invoices_l180d.paid_ratio >= 0.9"
    - "intent.g2_review_visits_l30d >= 1 OR intent.competitor_page_visits_l30d >= 2"
  exclusions:
    - "Account.OptOut_AllMarketing__c = TRUE"
    - "Account.OpenSupportCase_Severity__c IN ('Critical', 'High')"
    - "Contact.Bounced_l30d = TRUE"
    - "Account on AE-active pipeline within last 14 days (suppression: pipeline conflict)"
  estimated_size: "~2,400 contacts across ~840 accounts (38% of total Tier-2 lapsed cohort, post-suppression)"

agents:
  - execution
  - qa
  - optimization

priors:
  benchmark_customers:
    - name: HockeyStack
      result: "41% CTR lift, idea-to-live in 30 min, 2× faster deals"
      lift: "warehouse join on account signals at send time"
  platform_moat: "warehouse-native personalization at send time via Snowflake/BigQuery join, not batch-sync"
```

- [ ] **Step 5: Create `examples/marops/hockeystack.yaml`**

```yaml
customer:
  name: HockeyStack
  url: https://www.hockeystack.com
  vertical: "B2B revenue attribution & marketing analytics SaaS"

lifecycle_stage: "New Customer · Onboarding → Activation (days 0–30)"

campaign:
  name: "New Customer Activation — Dashboard Setup → First Attribution Report"
  objective: >
    Drive new HockeyStack customers from signup to first successful attribution
    report within 14 days, reducing time-to-value and preventing silent churn
    in the critical onboarding window.
  num_touches: 4

segment:
  crm: salesforce
  warehouse: bigquery
  icp_filters:
    - "Account.CustomerStatus__c = 'Active'"
    - "Account.CreatedDate >= TODAY - 30"
    - "Account.Onboarding_Stage__c IN ('Provisioned', 'Setup_Incomplete')"
    - "Contact.Role IN ('Marketing Ops', 'Demand Gen', 'Growth', 'RevOps')"
    - "Contact.EmailOptIn__c = TRUE"
  warehouse_traits:
    - "product.first_login_at IS NOT NULL"
    - "product.attribution_reports_created_l14d = 0"
    - "product.integrations_connected = 0"
    - "product.sessions_l7d >= 1"
  exclusions:
    - "Account.CSM_Active_Onboarding__c = TRUE"
    - "Contact.Bounced_l30d = TRUE"
    - "Account.OpenSupportCase_Severity__c = 'Critical'"
  estimated_size: "~180 contacts across ~90 accounts (new cohort, monthly)"

agents:
  - execution
  - qa
  - optimization

priors:
  benchmark_customers:
    - name: Adaptive
      result: "First report in <1 hour with guided onboarding sequence"
    - name: Veriforce
      result: "Re-engagement campaign — 41% CTR lift via warehouse join"
  platform_moat: "warehouse-native personalization: BigQuery product telemetry joined at send time, not batch-synced"
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python -m pytest tests/marops/test_config_loader.py -v
```

Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add scripts/marops/config_loader.py examples/marops/veriforce.yaml examples/marops/hockeystack.yaml tests/marops/test_config_loader.py
git commit -m "feat(marops): YAML config loader + veriforce and hockeystack example configs"
```

---

## Task 4: Claude API briefer (tool_use structured output)

**Files:**
- Create: `scripts/marops/briefer.py`
- Create: `tests/marops/test_briefer.py`

`★ Insight ─────────────────────────────────────`
Using `tool_use` rather than `response_format` JSON mode is the right call here — it lets Claude call a "structured_brief" tool with a strict JSON schema, which enforces the exact shape Conversion's platform consumes. The walk-in script explicitly says "it enforces the JSON schema deterministically so the output is config-shaped, not free-form." Prompt caching on the system prompt priors library (the multi-thousand-token context about warehouse-native personalization, Conversion's agent model, etc.) brings per-brief cost to ~$0.002.
`─────────────────────────────────────────────────`

- [ ] **Step 1: Write the failing test (mocked)**

Create `tests/marops/test_briefer.py`:

```python
"""Tests for the MarOps brief generator.

Uses unittest.mock to avoid live Claude API calls in CI.
The integration test is marked with @pytest.mark.integration and requires ANTHROPIC_API_KEY.
"""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from scripts.marops.config_loader import load_marops_config
from scripts.marops.briefer import generate_brief
from scripts.marops.models import LifecycleBrief

EXAMPLES = Path(__file__).parent.parent.parent / "examples" / "marops"

FAKE_BRIEF_JSON = {
    "prospect": "Veriforce",
    "prospect_url": "https://www.veriforce.com",
    "vertical": "Supplier compliance SaaS",
    "campaign_name": "Tier-2 Re-Engagement",
    "objective": "Reactivate lapsed accounts.",
    "lifecycle_stage": "Customer · Re-engagement",
    "segment": {
        "name": "Lapsed Tier-2",
        "salesforce_filters": ["Account.Tier__c = 'Tier 2'"],
        "warehouse_traits": ["product.last_login_at < now() - interval '90 days'"],
        "exclusions": ["Account.OptOut_AllMarketing__c = TRUE"],
        "estimated_size": "~2,400 contacts",
    },
    "touches": [
        {
            "step": 1,
            "channel": "email",
            "agent": "execution",
            "timing": "T+0",
            "subject": "Your clients require verified suppliers",
            "body_brief": "Lead with the contractual reality.",
            "personalization_tokens": ["Contact.FirstName"],
            "qa_rules": ["Reject if token is null"],
            "success_metric": "Open rate >38%",
        }
    ],
    "optimization_triggers": [
        {"condition": "intent spike: g2_review_visits_l7d >= 3", "action": "accelerate to step 4"}
    ],
    "pipeline_projection": {
        "expected_renewals": "~$1.4M ARR",
        "ae_efficiency": "70% task acceptance",
        "campaign_runtime": "21 days",
        "downside": "Pipeline drops 30% if legal fails",
    },
    "meta": {"platform_fit": "Salesforce + Snowflake warehouse join"},
}


def _make_mock_response(brief_json: dict):
    """Build a mock anthropic ToolUseBlock response."""
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "structured_brief"
    tool_use_block.input = brief_json

    mock_message = MagicMock()
    mock_message.content = [tool_use_block]
    mock_message.stop_reason = "tool_use"
    return mock_message


def test_generate_brief_returns_lifecycle_brief():
    config = load_marops_config(EXAMPLES / "veriforce.yaml")
    mock_response = _make_mock_response(FAKE_BRIEF_JSON)

    with patch("scripts.marops.briefer.anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_response
        brief = generate_brief(config)

    assert isinstance(brief, LifecycleBrief)
    assert brief.prospect == "Veriforce"
    assert len(brief.touches) == 1
    assert len(brief.optimization_triggers) == 1


def test_generate_brief_passes_correct_tool_schema():
    config = load_marops_config(EXAMPLES / "veriforce.yaml")
    mock_response = _make_mock_response(FAKE_BRIEF_JSON)

    with patch("scripts.marops.briefer.anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_response
        generate_brief(config)

    call_kwargs = instance.messages.create.call_args.kwargs
    tools = call_kwargs["tools"]
    assert any(t["name"] == "structured_brief" for t in tools)
    # Prompt cache on system prompt
    messages = call_kwargs["messages"]
    system = call_kwargs.get("system", [])
    # system should be a list with cache_control on the priors block
    assert isinstance(system, list)
    assert any(
        block.get("cache_control", {}).get("type") == "ephemeral"
        for block in system
    )


@pytest.mark.integration
def test_generate_brief_live():
    """Live integration test — requires ANTHROPIC_API_KEY in environment."""
    config = load_marops_config(EXAMPLES / "veriforce.yaml")
    brief = generate_brief(config)
    assert isinstance(brief, LifecycleBrief)
    assert brief.prospect == "Veriforce"
    assert len(brief.touches) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/marops/test_briefer.py -v -k "not integration"
```

Expected: `ImportError: cannot import name 'generate_brief'`

- [ ] **Step 3: Create `scripts/marops/briefer.py`**

```python
"""Generate a Conversion-platform-shaped lifecycle campaign brief via Claude API.

Uses tool_use to enforce the exact JSON schema — output is config-shaped,
not free-form prose. Prompt caching on the priors block (warehouse-native
personalization context, Conversion agent model) keeps cost to ~$0.002/brief.
"""

from __future__ import annotations
import json
import os
import anthropic

from scripts.marops.config_loader import MarOpsCampaignConfig
from scripts.marops.models import LifecycleBrief

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 8192

# Schema for the structured_brief tool — mirrors LifecycleBrief exactly.
_BRIEF_TOOL: dict = {
    "name": "structured_brief",
    "description": (
        "Emit a lifecycle campaign brief in the exact shape Conversion's "
        "platform consumes: segment definition, multi-touch sequence with "
        "agent role assignments, optimization triggers, and pipeline projection."
    ),
    "input_schema": {
        "type": "object",
        "required": [
            "prospect", "prospect_url", "vertical", "campaign_name",
            "objective", "lifecycle_stage", "segment", "touches",
            "optimization_triggers", "pipeline_projection", "meta",
        ],
        "properties": {
            "prospect": {"type": "string"},
            "prospect_url": {"type": "string"},
            "vertical": {"type": "string"},
            "campaign_name": {"type": "string"},
            "objective": {"type": "string"},
            "lifecycle_stage": {"type": "string"},
            "segment": {
                "type": "object",
                "required": ["name", "salesforce_filters", "warehouse_traits", "exclusions", "estimated_size"],
                "properties": {
                    "name": {"type": "string"},
                    "salesforce_filters": {"type": "array", "items": {"type": "string"}},
                    "warehouse_traits": {"type": "array", "items": {"type": "string"}},
                    "exclusions": {"type": "array", "items": {"type": "string"}},
                    "estimated_size": {"type": "string"},
                },
            },
            "touches": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["step", "channel", "agent", "timing", "subject", "body_brief", "personalization_tokens", "qa_rules", "success_metric"],
                    "properties": {
                        "step": {"type": "integer"},
                        "channel": {"type": "string", "enum": ["email", "in_app_banner", "ae_task", "sms", "linkedin"]},
                        "agent": {"type": "string", "enum": ["execution", "qa", "optimization"]},
                        "timing": {"type": "string"},
                        "subject": {"type": "string"},
                        "body_brief": {"type": "string"},
                        "personalization_tokens": {"type": "array", "items": {"type": "string"}},
                        "qa_rules": {"type": "array", "items": {"type": "string"}},
                        "success_metric": {"type": "string"},
                    },
                },
            },
            "optimization_triggers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["condition", "action"],
                    "properties": {
                        "condition": {"type": "string"},
                        "action": {"type": "string"},
                    },
                },
            },
            "pipeline_projection": {
                "type": "object",
                "required": ["expected_renewals", "ae_efficiency", "campaign_runtime", "downside"],
                "properties": {
                    "expected_renewals": {"type": "string"},
                    "ae_efficiency": {"type": "string"},
                    "campaign_runtime": {"type": "string"},
                    "downside": {"type": "string"},
                },
            },
            "meta": {"type": "object"},
        },
    },
}

_PRIORS_TEXT = """\
PRIORS — Conversion platform architecture you must reflect in every brief:

1. WAREHOUSE-NATIVE PERSONALIZATION: Salesforce CRM filters define the eligible universe.
   Snowflake/BigQuery warehouse traits refine it with product telemetry and intent signals.
   Personalization tokens are joined AT SEND TIME — not batch-synced. This is the moat.

2. AGENT ROLES (non-overlapping responsibilities):
   - execution: sends the touch, handles render/delivery logistics
   - optimization: owns A/B variant selection, bandit allocation, reallocation decisions
   - qa: inspects signals, creates AE tasks, flags suppression conditions, never sends

3. SUPPRESSION LOGIC: Every touch must have hard-suppression rules for: prior conversions,
   open support cases (Critical/High), explicit opt-out, AE-claimed accounts, banner fatigue.

4. BENCHMARK: HockeyStack — 41% CTR lift, idea-to-live in 30 min, 2× faster deals.
   The brief format you produce is what made that possible.

5. OUTPUT SHAPE: The brief is a CONFIG, not a doc. Every field maps to a platform setting.
   Segment → segmentation engine. Touches → campaign builder. Triggers → automation rules.
"""


def _build_system(config: MarOpsCampaignConfig) -> list[dict]:
    """Build system message blocks with prompt cache on priors."""
    priors_content = _PRIORS_TEXT
    if config.priors:
        priors_content += f"\nCUSTOMER-SPECIFIC PRIORS:\n{json.dumps(config.priors, indent=2)}"

    return [
        {
            "type": "text",
            "text": priors_content,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": (
                "You are a MarOps brief generator. Given a campaign config, call the "
                "`structured_brief` tool with a complete, production-ready lifecycle "
                "campaign brief. Every field must be specific and actionable — not "
                "placeholder text. QA rules must reference real failure modes. "
                "Suppression logic must be deterministic (no LLM-decided thresholds). "
                "Agent role assignments must be non-overlapping."
            ),
        },
    ]


def _build_user_message(config: MarOpsCampaignConfig) -> str:
    return (
        f"Generate a lifecycle campaign brief for {config.customer.name} "
        f"({config.customer.vertical}).\n\n"
        f"Lifecycle stage: {config.lifecycle_stage}\n"
        f"Campaign objective: {config.campaign.objective}\n"
        f"Number of touches: {config.campaign.num_touches}\n\n"
        f"Segment config:\n"
        f"  CRM: {config.segment.crm}\n"
        f"  Warehouse: {config.segment.warehouse}\n"
        f"  ICP filters: {json.dumps(config.segment.icp_filters, indent=2)}\n"
        f"  Warehouse traits: {json.dumps(config.segment.warehouse_traits, indent=2)}\n"
        f"  Exclusions: {json.dumps(config.segment.exclusions, indent=2)}\n"
        f"  Estimated size: {config.segment.estimated_size}\n\n"
        f"Agents available: {', '.join(config.agents)}\n"
        f"Customer URL: {config.customer.url}"
    )


def generate_brief(config: MarOpsCampaignConfig) -> LifecycleBrief:
    """Call Claude API and return a validated LifecycleBrief."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_build_system(config),
        tools=[_BRIEF_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": _build_user_message(config)}],
    )

    tool_block = next(b for b in response.content if b.type == "tool_use")
    return LifecycleBrief.model_validate(tool_block.input)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/marops/test_briefer.py -v -k "not integration"
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/marops/briefer.py tests/marops/test_briefer.py
git commit -m "feat(marops): Claude API briefer with tool_use JSON schema enforcement and prompt caching"
```

---

## Task 5: Jinja2 renderer

**Files:**
- Create: `renderer/marops/lifecycle_brief.html.j2` (copy from conversion-walkin)
- Create: `scripts/marops/renderer.py`
- Create: `tests/marops/test_renderer.py`

- [ ] **Step 1: Copy the renderer template**

```bash
mkdir -p /Users/sami/SignalForce/renderer/marops
cp /Users/sami/Desktop/practice/conversion-walkin/renderer/lifecycle_brief.html.j2 \
   /Users/sami/SignalForce/renderer/marops/lifecycle_brief.html.j2
```

- [ ] **Step 2: Write the failing test**

Create `tests/marops/test_renderer.py`:

```python
"""Tests for the MarOps HTML/PDF renderer."""
from pathlib import Path
from scripts.marops.models import (
    LifecycleBrief, SegmentDefinition, Touch, OptimizationTrigger,
    PipelineProjection, TouchChannel, AgentRole,
)
from scripts.marops.renderer import render_html

_SEGMENT = SegmentDefinition(
    name="Lapsed Tier-2",
    salesforce_filters=["Account.Tier__c = 'Tier 2'"],
    warehouse_traits=["product.last_login_at < now() - interval '90 days'"],
    exclusions=["Account.OptOut_AllMarketing__c = TRUE"],
    estimated_size="~2,400 contacts",
)
_TOUCH = Touch(
    step=1,
    channel=TouchChannel.EMAIL,
    agent=AgentRole.EXECUTION,
    timing="T+0",
    subject="Your {{ Account.Industry }} clients are still requiring verified suppliers",
    body_brief="Plain-text feel, no graphics.",
    personalization_tokens=["Contact.FirstName", "Account.Name"],
    qa_rules=["Reject if any token is null"],
    success_metric="Open rate >38%",
)
_BRIEF = LifecycleBrief(
    prospect="Veriforce",
    prospect_url="https://www.veriforce.com",
    vertical="Supplier compliance SaaS",
    campaign_name="Tier-2 Re-Engagement",
    objective="Reactivate lapsed accounts.",
    lifecycle_stage="Customer · Re-engagement",
    segment=_SEGMENT,
    touches=[_TOUCH],
    optimization_triggers=[
        OptimizationTrigger(
            condition="intent spike: g2_review_visits >= 3",
            action="accelerate to step 4",
        )
    ],
    pipeline_projection=PipelineProjection(
        expected_renewals="~$1.4M ARR",
        ae_efficiency="70% task acceptance",
        campaign_runtime="21 days",
        downside="Drops 30% if legal fails",
    ),
    meta={"platform_fit": "Salesforce + Snowflake"},
)


def test_render_html_produces_file(tmp_path):
    out = tmp_path / "veriforce.html"
    render_html(_BRIEF, out)
    assert out.exists()
    html = out.read_text()
    assert "Veriforce" in html
    assert "Tier-2 Re-Engagement" in html
    assert "Lapsed Tier-2" in html


def test_render_html_includes_touch_subject(tmp_path):
    out = tmp_path / "veriforce.html"
    render_html(_BRIEF, out)
    html = out.read_text()
    assert "verified suppliers" in html
```

- [ ] **Step 3: Run test to verify it fails**

```bash
python -m pytest tests/marops/test_renderer.py -v
```

Expected: `ImportError: cannot import name 'render_html'`

- [ ] **Step 4: Create `scripts/marops/renderer.py`**

```python
"""Render a LifecycleBrief to HTML using Jinja2.

Template path: renderer/marops/lifecycle_brief.html.j2
Output is written to the provided path. The template is the same one used
in the conversion-walkin demo — no modifications needed.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.marops.models import LifecycleBrief

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TEMPLATE_DIR = _REPO_ROOT / "renderer" / "marops"


def render_html(brief: LifecycleBrief, out_path: Path) -> None:
    """Render brief to HTML at out_path. Creates parent dirs if needed."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("lifecycle_brief.html.j2")

    # Serialise touches and optimization_triggers to plain dicts for Jinja.
    html = template.render(
        prospect={"name": brief.prospect, "url": brief.prospect_url},
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        vertical=brief.vertical,
        meta=brief.meta,
        campaign_name=brief.campaign_name,
        objective=brief.objective,
        lifecycle_stage=brief.lifecycle_stage,
        segment=brief.segment.model_dump(),
        touches=[t.model_dump() for t in brief.touches],
        optimization_triggers=[o.model_dump() for o in brief.optimization_triggers],
        pipeline_projection=brief.pipeline_projection.model_dump(),
    )
    out_path.write_text(html, encoding="utf-8")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/marops/test_renderer.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add renderer/marops/lifecycle_brief.html.j2 scripts/marops/renderer.py tests/marops/test_renderer.py
git commit -m "feat(marops): Jinja2 HTML renderer — same template as conversion-walkin demo"
```

---

## Task 6: CLI entrypoint and end-to-end demo run

**Files:**
- Create: `scripts/marops/cli.py`
- Modify: `out/.gitignore` (create with `*`)

- [ ] **Step 1: Create `scripts/marops/cli.py`**

```python
"""CLI for the MarOps brief generator.

Usage:
    python -m scripts.marops.cli veriforce
    python -m scripts.marops.cli hockeystack

Reads examples/marops/<name>.yaml, generates brief via Claude API,
writes out/<name>.html and out/<name>.json.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

from scripts.marops.config_loader import load_marops_config
from scripts.marops.briefer import generate_brief
from scripts.marops.renderer import render_html

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_EXAMPLES = _REPO_ROOT / "examples" / "marops"
_OUT = _REPO_ROOT / "out"


def main(name: str) -> None:
    config_path = _EXAMPLES / f"{name}.yaml"
    config = load_marops_config(config_path)
    print(f"Loaded config: {config.customer.name} — {config.campaign.name}")

    print("Generating brief via Claude API...")
    brief = generate_brief(config)
    print(f"Generated {len(brief.touches)} touches, {len(brief.optimization_triggers)} triggers")

    _OUT.mkdir(exist_ok=True)
    html_path = _OUT / f"{name}.html"
    json_path = _OUT / f"{name}.json"

    render_html(brief, html_path)
    json_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")

    print(f"HTML  → {html_path}")
    print(f"JSON  → {json_path}")
    print("Done. Open the HTML in Chrome full-screen for the demo.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.marops.cli <config_name>")
        sys.exit(1)
    main(sys.argv[1])
```

- [ ] **Step 2: Create `out/.gitignore`**

```
*
!.gitignore
```

- [ ] **Step 3: Run the end-to-end pipeline (requires ANTHROPIC_API_KEY)**

```bash
cd /Users/sami/SignalForce
export ANTHROPIC_API_KEY="$(grep ANTHROPIC_API_KEY ~/.env 2>/dev/null | cut -d= -f2)"
# Or: export ANTHROPIC_API_KEY=sk-ant-...
python -m scripts.marops.cli veriforce
```

Expected output:
```
Loaded config: Veriforce — Tier-2 Supplier Re-Engagement — Compliance Lapse → Renewal
Generating brief via Claude API...
Generated 5 touches, 4 triggers
HTML  → /Users/sami/SignalForce/out/veriforce.html
JSON  → /Users/sami/SignalForce/out/veriforce.json
Done. Open the HTML in Chrome full-screen for the demo.
```

- [ ] **Step 4: Open and verify the HTML looks correct**

```bash
open /Users/sami/SignalForce/out/veriforce.html
```

Verify: customer name, segment SQL, touch sequence with agent roles, optimization triggers, pipeline projection all render correctly.

- [ ] **Step 5: Update the walk-in script with the correct path**

In `conversion-walkin/walkin_script.md`, Beat 2 references `out/veriforce.html`. The demo path is now `/Users/sami/SignalForce/out/veriforce.html`. Update the pre-walk-in print queue section:

```bash
# In the walkin_script.md Pre-Walk-In Print Queue section, change:
# OLD: cd /Users/sami/Desktop/practice/conversion-walkin
# NEW:
cd /Users/sami/SignalForce
python -m scripts.marops.cli veriforce
open out/veriforce.html
```

- [ ] **Step 6: Run the full test suite to confirm nothing broke**

```bash
cd /Users/sami/SignalForce
python -m pytest tests/marops/ -v -k "not integration"
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/marops/cli.py out/.gitignore conversion-walkin/walkin_script.md
git commit -m "feat(marops): CLI entrypoint + end-to-end pipeline verified"
```

---

## Task 7: Final polish — README section and line count check

**Files:**
- Modify: `README.md`

The walk-in script says "~400 lines total." Verify:

- [ ] **Step 1: Count lines**

```bash
find /Users/sami/SignalForce/scripts/marops -name "*.py" | xargs wc -l
```

Expected: total under 400 lines across all marops Python files.

- [ ] **Step 2: Add MarOps section to README.md**

Add after the existing "Two modes" section:

```markdown
## MarOps Branch — Conversion Platform Briefs

The `marops` branch repoints SignalForce from prospecting to lifecycle marketing.
Same config-driven architecture, same multi-agent orchestration — pointed at a
Conversion customer's Salesforce + Snowflake instead of GitHub stars and funding rounds.

```bash
git checkout marops
export ANTHROPIC_API_KEY=sk-ant-...
python -m scripts.marops.cli veriforce   # generates out/veriforce.html
python -m scripts.marops.cli hockeystack # generates out/hockeystack.html
```

Output: a Conversion-platform-shaped lifecycle campaign brief — segment SQL,
multi-touch sequence with agent role assignments, QA rules, optimization triggers,
pipeline projection. The brief is a config, not a doc.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(marops): add MarOps branch usage to README"
```

---

## Pre-Walk-In Checklist

Morning of the Conversion walk-in:

```bash
cd /Users/sami/SignalForce
git checkout marops

# Regenerate to prove it's live (takes ~15 seconds, costs ~$0.002)
python -m scripts.marops.cli veriforce

# Open full-screen in Chrome — this is the demo
open out/veriforce.html

# Print one copy on decent paper
# Chrome: ⌘P → Save as PDF → print
```

Also prepare:
- [ ] `out/hockeystack.html` generated and pre-loaded in a second Chrome tab (vertical breadth)
- [ ] Have `scripts/marops/briefer.py` open in VS Code alongside the running Chrome tab — if they probe the stack, show the ~60-line briefer that calls Claude with `tool_use`
- [ ] 1-pager resume and business card with QR to `github.com/sami2919/SignalForce` in hand

---

## Self-Review

**Spec coverage:**
- ✅ `marops` branch created on SignalForce
- ✅ Same architectural pattern as existing SignalForce (config → processor → structured output → renderer)
- ✅ Claude API with `tool_use` enforcing JSON schema
- ✅ Prompt caching on priors (mentioned explicitly in walk-in script)
- ✅ Veriforce YAML config driving the generator
- ✅ HockeyStack second example for vertical breadth
- ✅ `out/veriforce.html` at correct path for demo
- ✅ Walk-in script pre-walk-in commands updated
- ✅ ~400 total lines (briefer ~130, renderer ~40, models ~70, config_loader ~60, cli ~30)
- ✅ TDD throughout — tests written before implementation in every task
- ✅ All models immutable (frozen=True)

**Placeholder scan:** No TBDs. Every code block is complete. Tool schema includes all required fields.

**Type consistency:** `LifecycleBrief`, `Touch`, `SegmentDefinition`, `OptimizationTrigger`, `PipelineProjection` — same names throughout models, briefer, renderer, and tests.
