# ADK Evaluation

## Why Evaluate

LLM agents are non-deterministic. Traditional pass/fail assertions are insufficient. Evaluation must cover:

- **Tool correctness** — Did the agent call the right tools with the right arguments?
- **Response quality** — Is the final answer accurate, complete, and well-formed?
- **Safety** — Does the agent avoid harmful or inappropriate content?
- **Groundedness** — Are claims supported by context (no hallucinations)?
- **Regression** — Do agent updates preserve existing behavior?

Automating evaluations pays off quickly. If you intend to progress beyond prototype, this is a highly recommended best practice.

---

## Eval Data Format

ADK uses Pydantic-backed schemas: `EvalSet` containing `EvalCase`s, each with a `conversation` of `Invocation`s. Files use `.test.json` (unit tests) or `.evalset.json` (integration tests) suffix.

### Single-Turn Eval Case

```json
{
  "eval_set_id": "weather_agent_tests",
  "name": "Weather agent basic tests",
  "description": "Unit tests for weather agent tool use and responses",
  "eval_cases": [
    {
      "eval_id": "turn_off_bedroom_device",
      "conversation": [
        {
          "invocation_id": "inv-001",
          "user_content": {
            "parts": [{"text": "Turn off device_2 in the Bedroom."}],
            "role": "user"
          },
          "final_response": {
            "parts": [{"text": "I have set the device_2 status to off."}],
            "role": "model"
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "set_device_info",
                "args": {
                  "location": "Bedroom",
                  "device_id": "device_2",
                  "status": "OFF"
                }
              }
            ],
            "intermediate_responses": []
          }
        }
      ],
      "session_input": {
        "app_name": "home_automation_agent",
        "user_id": "test_user",
        "state": {}
      }
    }
  ]
}
```

### Multi-Turn Eval Case

Multiple invocations in one eval case test conversational flow:

```json
{
  "eval_id": "multi_turn_dice_and_prime",
  "conversation": [
    {
      "invocation_id": "inv-001",
      "user_content": {
        "parts": [{"text": "Roll a 10 sided dice twice"}],
        "role": "user"
      },
      "final_response": {
        "parts": [{"text": "I rolled a 4 and a 7."}],
        "role": "model"
      },
      "intermediate_data": {
        "tool_uses": [
          {"name": "roll_die", "args": {"sides": 10}},
          {"name": "roll_die", "args": {"sides": 10}}
        ],
        "intermediate_responses": []
      }
    },
    {
      "invocation_id": "inv-002",
      "user_content": {
        "parts": [{"text": "Check if 9 is prime"}],
        "role": "user"
      },
      "final_response": {
        "parts": [{"text": "9 is not a prime number."}],
        "role": "model"
      },
      "intermediate_data": {
        "tool_uses": [
          {"name": "check_prime", "args": {"nums": [9]}}
        ],
        "intermediate_responses": []
      }
    }
  ],
  "session_input": {
    "app_name": "hello_world",
    "user_id": "user",
    "state": {}
  }
}
```

### Key Schema Fields

| Field | Description |
|-------|-------------|
| `eval_set_id` | Unique identifier for the eval set |
| `eval_cases[].eval_id` | Unique identifier for each eval case |
| `conversation[]` | List of `Invocation` objects (one per user turn) |
| `user_content` | The user query (`role: "user"`, `parts` with `text`) |
| `final_response` | Expected agent response (reference for scoring) |
| `intermediate_data.tool_uses` | Expected tool calls in chronological order |
| `intermediate_data.intermediate_responses` | Expected sub-agent responses (for multi-agent) |
| `session_input` | Initial session config: `app_name`, `user_id`, `state` |

---

## Evaluation Criteria

ADK provides 8 built-in metrics:

| Criterion | Type | Reference-Based | Requires Rubrics | LLM Judge | User Sim |
|-----------|------|:-:|:-:|:-:|:-:|
| `tool_trajectory_avg_score` | Tool trajectory match | Yes | No | No | No |
| `response_match_score` | ROUGE-1 text overlap | Yes | No | No | No |
| `final_response_match_v2` | Semantic match (LLM judge) | Yes | No | Yes | No |
| `rubric_based_final_response_quality_v1` | Response quality rubrics | No | Yes | Yes | Yes |
| `rubric_based_tool_use_quality_v1` | Tool use quality rubrics | No | Yes | Yes | Yes |
| `hallucinations_v1` | Groundedness check | No | No | Yes | Yes |
| `safety_v1` | Harmlessness check | No | No | Yes | Yes |
| `per_turn_user_simulator_quality_v1` | User sim fidelity | No | No | Yes | Yes |

**Defaults** (when no config provided): `tool_trajectory_avg_score: 1.0`, `response_match_score: 0.8`.

### Tool Trajectory Evaluation

Compares actual tool calls against expected. Three match types:

| Match Type | Behavior |
|------------|----------|
| `EXACT` | Perfect match — same tools, same args, same order, no extras |
| `IN_ORDER` | Expected tools appear in order, other calls allowed between |
| `ANY_ORDER` | Expected tools all appear, order doesn't matter, extras allowed |

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "EXACT"
    }
  }
}
```

Shorthand for EXACT match: `"tool_trajectory_avg_score": 1.0`

### Response Match (ROUGE-1)

Fast lexical overlap scoring. Good for CI/CD and regression testing:

```json
{
  "criteria": {
    "response_match_score": 0.8
  }
}
```

### Semantic Response Match (LLM Judge)

More flexible than ROUGE — tolerates different phrasing, formatting, additional correct details:

```json
{
  "criteria": {
    "final_response_match_v2": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-2.5-flash",
        "num_samples": 5
      }
    }
  }
}
```

### Rubric-Based Response Quality

Evaluate subjective quality without a reference response. Define custom rubrics:

```json
{
  "criteria": {
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-2.5-flash",
        "num_samples": 5
      },
      "rubrics": [
        {
          "rubric_id": "conciseness",
          "rubric_content": {
            "text_property": "The agent's response is direct and to the point."
          }
        },
        {
          "rubric_id": "intent_inference",
          "rubric_content": {
            "text_property": "The agent accurately infers the user's underlying goal."
          }
        }
      ]
    }
  }
}
```

### Rubric-Based Tool Use Quality

Validate agent reasoning process with custom tool-use rubrics:

```json
{
  "criteria": {
    "rubric_based_tool_use_quality_v1": {
      "threshold": 1.0,
      "judge_model_options": {
        "judge_model": "gemini-2.5-flash",
        "num_samples": 5
      },
      "rubrics": [
        {
          "rubric_id": "geocoding_first",
          "rubric_content": {
            "text_property": "The agent calls GeoCoding before calling GetWeather."
          }
        },
        {
          "rubric_id": "correct_coords",
          "rubric_content": {
            "text_property": "GetWeather is called with coordinates from GeoCoding."
          }
        }
      ]
    }
  }
}
```

### Hallucination Detection

Checks if agent claims are grounded in context (tool outputs, instructions, user input):

```json
{
  "criteria": {
    "hallucinations_v1": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-2.5-flash"
      },
      "evaluate_intermediate_nl_responses": true
    }
  }
}
```

### Safety

Requires Google Cloud Project (`GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` env vars). Delegates to Vertex AI Eval SDK:

```json
{
  "criteria": {
    "safety_v1": 0.8
  }
}
```

---

## Eval Config File

Create `test_config.json` alongside eval data files. Combine multiple criteria:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "IN_ORDER"
    },
    "response_match_score": 0.8,
    "hallucinations_v1": {
      "threshold": 0.8,
      "evaluate_intermediate_nl_responses": true
    },
    "safety_v1": 0.8
  }
}
```

---

## Running Evaluations

### Method 1: CLI (`adk eval`)

```bash
# Basic: run all evals in an evalset file
adk eval \
  my_agent \
  my_agent/eval_set.evalset.json

# With config and detailed output
adk eval \
  my_agent \
  my_agent/eval_set.evalset.json \
  --config_file_path my_agent/test_config.json \
  --print_detailed_results

# Run specific eval cases from an evalset
adk eval \
  my_agent \
  my_agent/eval_set.evalset.json:case_1,case_2
```

### Method 2: Pytest (`AgentEvaluator`)

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator
import pytest

@pytest.mark.asyncio
async def test_basic_tool_use():
    """Test agent tool use via a test file."""
    await AgentEvaluator.evaluate(
        agent_module="my_agent",
        eval_dataset_file_path_or_dir="tests/eval/basic.test.json",
    )

@pytest.mark.asyncio
async def test_eval_directory():
    """Run all .test.json files in a directory."""
    await AgentEvaluator.evaluate(
        agent_module="my_agent",
        eval_dataset_file_path_or_dir="tests/eval/",
    )
```

### Method 3: Web UI (`adk web`)

```bash
adk web my_agent
```

1. Interact with the agent to create a session
2. Navigate to the **Eval** tab
3. Create or select an eval set, click **Add current session**
4. Edit eval cases (modify responses, delete messages)
5. Select cases and click **Run Evaluation** — configure metric thresholds
6. Analyze results — hover over Fail labels for actual vs expected comparison

The web UI also provides a **Trace** tab for debugging agent execution flow, tool calls, and model requests/responses.

---

## Dynamic User Simulation

For conversational agents where fixed prompts are impractical, use `ConversationScenario` to dynamically generate user prompts via an LLM:

### Conversation Scenarios File

```json
{
  "scenarios": [
    {
      "starting_prompt": "What can you do for me?",
      "conversation_plan": "Ask the agent to roll a 20-sided die. After you get the result, ask the agent to check if it is prime."
    },
    {
      "starting_prompt": "Hi, I need help with my account.",
      "conversation_plan": "Ask the agent to look up order #12345. Then ask to cancel it. If the agent asks for confirmation, confirm."
    }
  ]
}
```

### Adding Scenarios to an EvalSet

```bash
# Create eval set
adk eval_set create my_agent my_eval_set

# Add scenarios as eval cases
adk eval_set add_eval_case \
  my_agent \
  my_eval_set \
  --scenarios_file my_agent/conversation_scenarios.json \
  --session_input_file my_agent/session_input.json
```

### User Simulator Config

Override defaults in eval config:

```json
{
  "criteria": {
    "hallucinations_v1": {"threshold": 0.5},
    "safety_v1": {"threshold": 0.8}
  },
  "user_simulator_config": {
    "model": "gemini-2.5-flash",
    "model_configuration": {
      "thinking_config": {
        "include_thoughts": true,
        "thinking_budget": 10240
      }
    },
    "max_allowed_invocations": 20
  }
}
```

**Note**: User simulation only supports `hallucinations_v1`, `safety_v1`, rubric-based criteria, and `per_turn_user_simulator_quality_v1`. Reference-based criteria (`tool_trajectory_avg_score`, `response_match_score`, `final_response_match_v2`) are not supported with user simulation.

---

## Language Support

| Language | Eval Support | CLI Command | Notes |
|----------|:---:|-------------|-------|
| Python | Full | `adk eval` | 8 metrics, pytest, web UI, user simulation |
| TypeScript | Partial | `npx adk eval` | Same `.test.json` format, same CLI flags |
| Java | Not yet | — | Coming soon |
| Go | Not yet | — | Coming soon |

TypeScript uses the same eval data format (`.test.json`, `.evalset.json`) and the same `test_config.json` criteria. Run with:

```bash
npx adk eval \
  my_agent \
  my_agent/eval_set.evalset.json \
  --config_file_path my_agent/test_config.json
```

---

## Which Metric to Use

| Goal | Recommended Criteria |
|------|---------------------|
| CI/CD regression testing | `tool_trajectory_avg_score` + `response_match_score` |
| Semantic correctness with reference | `final_response_match_v2` |
| Quality without reference response | `rubric_based_final_response_quality_v1` |
| Validate tool call reasoning | `rubric_based_tool_use_quality_v1` |
| Detect hallucinations | `hallucinations_v1` |
| Safety compliance | `safety_v1` |
| Dynamic conversation testing | User simulation + `hallucinations_v1` + `safety_v1` |

---

## Best Practices

1. **Start with tool trajectory** — Most agent bugs manifest as wrong tool calls. Use `EXACT` match first, relax to `IN_ORDER` or `ANY_ORDER` as needed.
2. **Isolate tool calls** — One eval case per tool interaction pattern. Easier to debug failures.
3. **Cover edge cases** — Empty inputs, missing parameters, error conditions, multi-tool sequences.
4. **Use rubrics for subjective quality** — When "correct" has multiple valid forms, define rubrics instead of rigid references.
5. **Layer metrics** — Combine `tool_trajectory_avg_score` (fast, deterministic) with `hallucinations_v1` (deeper quality) for comprehensive coverage.
6. **Keep `.test.json` for unit tests** — Fast, single-session, run on every change.
7. **Use `.evalset.json` for integration tests** — Multi-session, complex flows, run less frequently.
8. **Use web UI to bootstrap eval data** — Interact with the agent, save sessions as eval cases, then edit to refine.
9. **Add eval config to source control** — `test_config.json` alongside eval data for reproducibility.
10. **Run user simulation for conversational agents** — Fixed prompts can't cover dynamic multi-turn interactions.
