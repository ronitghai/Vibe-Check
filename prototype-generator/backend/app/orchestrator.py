"""
orchestrator.py
---------------
Groq tool-calling chat loop for the AZ-900 Study Companion.

The orchestrator can:

1. Launch curated AZ-900 learning activities.
2. Generate completely new educational games.
3. Recover from Groq tool_use_failed errors where a valid function call is
   returned as malformed text instead of a structured tool call.
4. Preserve session-scoped chat history.
5. Report launched games back to the frontend.
"""

from __future__ import annotations

import json
import re
from typing import Any

from openai import BadRequestError, OpenAI

from . import config, session_store, tools
from .learning import store as learning_store
from .learning.knowledge_base import DOMAINS, SNIPPETS


client = OpenAI(
    api_key=config.GROQ_API_KEY,
    base_url=config.GROQ_BASE_URL,
)


MAX_TOOL_ROUNDS = 4
MAX_TOOL_RETRIES = 1


# knowledge_base.SNIPPETS now holds ~8 facts per skill-bullet topic (499
# total across the 3 domains — see that file's docstring for where they came
# from), not the ~1-per-topic starter set this was originally written
# against. Dumping all of them into every chat turn's system prompt would
# make each request needlessly large/slow for no real grounding benefit past
# a certain point, so cap how many facts per TOPIC (not per domain) go in —
# this keeps broad coverage across every one of the ~62 topics while keeping
# the block a reasonable size.
FACTS_PER_TOPIC = 2


def _facts_block() -> str:
    """
    Build a reference block containing AZ-900 facts from
    learning/knowledge_base.py, capped to FACTS_PER_TOPIC per topic so
    coverage stays broad (every topic represented) without the block growing
    unboundedly as more facts get added to the knowledge base over time.
    """
    lines: list[str] = []

    for domain in DOMAINS:
        lines.append(f"{domain}:")

        topic_counts: dict[str, int] = {}
        for entry in SNIPPETS[domain]:
            topic = entry.get("topic", "")
            if topic_counts.get(topic, 0) >= FACTS_PER_TOPIC:
                continue
            snippet = entry.get("snippet", "")
            if not snippet:
                continue
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            lines.append(f"  - {snippet}")

    return "\n".join(lines)


FACTS_BLOCK = _facts_block()


def _build_system_prompt(weakest_domain: str) -> str:
    """
    Build the system prompt for a new conversation.

    The learner's current weakest domain is included so the model can use it
    whenever the learner does not select a particular AZ-900 domain.
    """
    domains_text = ", ".join(DOMAINS)

    return f"""
You are the game-generation assistant inside the AZ-900 Study Companion.

Your purpose is to help learners prepare for the Microsoft Azure Fundamentals
AZ-900 certification through short, educational, playable activities.

Every learning activity must use genuine AZ-900 content from one of these
domains:

{domains_text}

REFERENCE MATERIAL

Use the following facts as grounding material:

{FACTS_BLOCK}

LEARNER PERSONALIZATION

The learner's current weakest domain is:

"{weakest_domain}"

Use this as the default domain when the learner does not name a domain or topic.

If the learner requests a non-Azure theme or mechanic, preserve the requested
style or game mechanic, but replace the educational content with genuine
AZ-900 material.

For example:

- A dinosaur trivia request can become an Azure trivia game with a dinosaur
  visual theme.
- A Jeopardy request can become an AZ-900 Jeopardy-style challenge.
- A racing game can test Azure concepts at checkpoints.

CURATED LEARNING ACTIVITIES

You may launch the following existing activities through
launch_template_game:

1. rapid_quiz
   A multiple-choice knowledge check with immediate feedback.

2. scenario_challenge
   A scenario-based activity where the learner applies Azure concepts to
   realistic business or technical situations.

3. matching_game
   A concept-connection activity where Azure terms are matched with their
   definitions, purposes, or examples.

4. crossword
   A vocabulary-review activity using AZ-900 terms and clues.

5. jeopardy
   A complete category board containing four categories and four questions
   per category.

JEOPARDY ROUTING RULE

If the learner asks for:

- Jeopardy
- a category board
- a point-value board
- trivia with categories and dollar values
- questions worth 100, 200, 300, and 400

you MUST call launch_template_game with:

game_id = "jeopardy"

Do not call generate_custom_game for a Jeopardy request.

The jeopardy config must have this exact structure:

{
  "title": string,
  "categories": [
    {
      "name": string,
      "questions": [
        {
          "value": 100,
          "question": string,
          "choices": [4 strings],
          "answerIndex": 0-3,
          "explanation": string
        },
        {
          "value": 200,
          "question": string,
          "choices": [4 strings],
          "answerIndex": 0-3,
          "explanation": string
        },
        {
          "value": 300,
          "question": string,
          "choices": [4 strings],
          "answerIndex": 0-3,
          "explanation": string
        },
        {
          "value": 400,
          "question": string,
          "choices": [4 strings],
          "answerIndex": 0-3,
          "explanation": string
        }
      ]
    }
  ]
}

Jeopardy requirements:

- exactly 4 categories
- exactly 4 questions per category
- exactly 16 questions
- values 100, 200, 300, and 400
- multiple-choice answers
- accurate AZ-900 content
- explanations after every answer
- no duplicate questions
- no placeholders

When calling launch_template_game:

- Include a valid domain.
- Include completed educational content in config.
- Never leave placeholder questions, clues, scenarios, or answers.
- Ensure all questions and answers are accurate.
- Include explanations whenever the selected template supports them.

CUSTOM GAME GENERATION

The learner may also request a completely new game mechanic.

When the request does not fit one of the curated activities, call
generate_custom_game.

The custom game must:

- Test or reinforce genuine AZ-900 knowledge.
- Use one clear core mechanic.
- Have understandable controls.
- Include a clear objective.
- Include scoring or measurable progress.
- Provide educational feedback.
- Be feasible as a self-contained HTML, CSS, and JavaScript experience.
- Report a correct and total score when the activity is complete.
- Include one valid AZ-900 domain.

Good custom-game examples include:

- Jeopardy-style category board
- Azure service sorting challenge
- Architecture decision simulator
- Cloud resource escape room
- Azure terminology platformer
- Service-model drag-and-drop challenge
- Timed infrastructure puzzle
- Cloud-cost decision game

TOOL-CALLING REQUIREMENTS

When launching or generating a game:

- Use a structured function call.
- Never write function calls as XML.
- Never output text such as <function=...>.
- Never place function-call JSON directly in the assistant message.
- Always supply every required tool argument.
- Always use one of the valid AZ-900 domains.

GENERAL CHAT

You do not have to launch a game every turn.

You may also:

- Explain AZ-900 concepts.
- Answer study questions.
- Recommend an activity.
- Clarify a learner's game request.

After a game launches successfully, respond with one short and enthusiastic
sentence confirming what was created.
""".strip()


def _normalise_tool_arguments(raw_arguments: str | None) -> dict[str, Any]:
    """
    Parse tool-call arguments safely.

    Tool arguments should normally contain valid JSON. This function prevents
    malformed JSON from crashing the entire chat request.
    """
    if not raw_arguments:
        return {}

    try:
        parsed = json.loads(raw_arguments)
    except (json.JSONDecodeError, TypeError):
        return {}

    if not isinstance(parsed, dict):
        return {}

    return parsed


def _error_body(exc: BadRequestError) -> dict[str, Any]:
    """
    Return the API error body when the SDK exposes it as a dictionary.
    """
    body = getattr(exc, "body", None)

    if isinstance(body, dict):
        return body

    return {}


def _is_tool_use_failure(exc: BadRequestError) -> bool:
    """
    Determine whether Groq rejected a malformed generated tool call.
    """
    body = _error_body(exc)
    error = body.get("error", {})

    if isinstance(error, dict):
        code = error.get("code")
        if code == "tool_use_failed":
            return True

    return "tool_use_failed" in str(exc)


def _extract_failed_generation(exc: BadRequestError) -> str | None:
    """
    Extract Groq's failed_generation value from a tool_use_failed response.
    """
    body = _error_body(exc)
    error = body.get("error", {})

    if isinstance(error, dict):
        failed_generation = error.get("failed_generation")

        if isinstance(failed_generation, str):
            return failed_generation

    # Fallback for SDK versions that only expose the error through str(exc).
    text = str(exc)

    match = re.search(
        r"""['"]failed_generation['"]\s*:\s*['"](.+?)['"]\s*}""",
        text,
        flags=re.DOTALL,
    )

    if match:
        return match.group(1)

    return None


def _extract_malformed_tool_call(
    failed_generation: str | None,
) -> tuple[str, dict[str, Any]] | None:
    """
    Recover a malformed function call such as:

    <function=generate_custom_game({"domain": "...", ...})</function>

    Groq occasionally returns this representation instead of a structured
    tool_calls object. If the function name and JSON arguments are valid, the
    backend can safely recover the request.
    """
    if not failed_generation:
        return None

    cleaned = (
        failed_generation
        .replace('\\"', '"')
        .replace("\\'", "'")
        .strip()
    )

    match = re.search(
        r"<function=([A-Za-z_][A-Za-z0-9_]*)\((\{.*\})\)</function>",
        cleaned,
        flags=re.DOTALL,
    )

    if not match:
        return None

    function_name = match.group(1)
    arguments_text = match.group(2)

    try:
        arguments = json.loads(arguments_text)
    except json.JSONDecodeError:
        return None

    if not isinstance(arguments, dict):
        return None

    return function_name, arguments


def _tool_exists(function_name: str) -> bool:
    """
    Confirm that a recovered function name is one of the functions actually
    exposed through tools.TOOLS.
    """
    for tool_definition in tools.TOOLS:
        if not isinstance(tool_definition, dict):
            continue

        function_definition = tool_definition.get("function", {})

        if (
            isinstance(function_definition, dict)
            and function_definition.get("name") == function_name
        ):
            return True

    return False


def _forced_tool_choice(function_name: str) -> dict[str, Any]:
    """
    Build a Chat Completions tool_choice value that forces one function.
    """
    return {
        "type": "function",
        "function": {
            "name": function_name,
        },
    }


def _create_completion(
    history: list[dict[str, Any]],
    *,
    tool_choice: str | dict[str, Any] = "auto",
):
    """
    Send one completion request to the configured Groq model.
    """
    return client.chat.completions.create(
        model=config.ORCHESTRATOR_MODEL,
        messages=history,
        tools=tools.TOOLS,
        tool_choice=tool_choice,
    )


def _retry_malformed_tool_call(
    history: list[dict[str, Any]],
    function_name: str | None,
):
    """
    Retry a malformed tool call once.

    If the failed function name was recovered and is a registered tool, force
    that exact function during the retry. Otherwise, allow the model to select
    a tool automatically.
    """
    retry_history = [
        *history,
        {
            "role": "system",
            "content": (
                "Your previous tool call was malformed. Retry the request using "
                "the API's structured tool-calling mechanism. Do not output XML "
                "function tags, function-call text, or raw function JSON in the "
                "assistant message. Supply valid JSON arguments matching the "
                "selected function schema."
            ),
        },
    ]

    tool_choice: str | dict[str, Any] = "auto"

    if function_name and _tool_exists(function_name):
        tool_choice = _forced_tool_choice(function_name)

    return _create_completion(
        retry_history,
        tool_choice=tool_choice,
    )


def _confirmation_for_game(
    function_name: str,
    arguments: dict[str, Any],
) -> str:
    """
    Create a short response when a malformed tool call was recovered and
    executed directly.
    """
    title = arguments.get("title")

    if isinstance(title, str) and title.strip():
        return f'Your "{title.strip()}" AZ-900 game is ready!'

    if function_name == "generate_custom_game":
        return "Your custom AZ-900 game is ready!"

    return "Your AZ-900 learning activity is ready!"


def _execute_tool_call(
    session_id: str,
    function_name: str,
    arguments: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    """
    Validate the function name and dispatch it through the existing tool layer.
    """
    if not _tool_exists(function_name):
        return (
            json.dumps(
                {
                    "ok": False,
                    "error": f"Unknown tool: {function_name}",
                }
            ),
            None,
        )

    return tools.dispatch(
        session_id,
        function_name,
        arguments,
    )


def run_turn(
    session_id: str,
    user_message: str,
) -> tuple[str, bool, str | None, str | None, str | None]:
    """
    Process one learner chat turn.

    Returns:

        reply
        game_ready
        game_id
        game_type
        game_domain
    """
    history = session_store.get_history(session_id)

    if not history:
        weakest_domain = learning_store.get_weakest_domain(session_id)

        history = [
            {
                "role": "system",
                "content": _build_system_prompt(weakest_domain),
            }
        ]

    history.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    game_ready = False
    game_id: str | None = None
    game_type: str | None = None
    game_domain: str | None = None

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = _create_completion(history)

        except BadRequestError as exc:
            if not _is_tool_use_failure(exc):
                raise

            failed_generation = _extract_failed_generation(exc)
            recovered_call = _extract_malformed_tool_call(failed_generation)

            recovered_function_name: str | None = None
            recovered_arguments: dict[str, Any] = {}

            if recovered_call:
                recovered_function_name, recovered_arguments = recovered_call

            # First recovery strategy:
            # Execute the malformed call directly when it contains valid JSON
            # and references a registered backend tool.
            if (
                recovered_function_name
                and recovered_arguments
                and _tool_exists(recovered_function_name)
            ):
                result_str, launched = _execute_tool_call(
                    session_id,
                    recovered_function_name,
                    recovered_arguments,
                )

                if launched:
                    game_ready = True
                    game_id = launched["game_id"]
                    game_type = launched["game_type"]
                    game_domain = launched.get("domain")

                    reply = _confirmation_for_game(
                        recovered_function_name,
                        recovered_arguments,
                    )

                    history.append(
                        {
                            "role": "assistant",
                            "content": reply,
                        }
                    )

                    session_store.save_history(session_id, history)

                    return (
                        reply,
                        game_ready,
                        game_id,
                        game_type,
                        game_domain,
                    )

                # The tool was recovered but failed during backend execution.
                history.append(
                    {
                        "role": "system",
                        "content": (
                            "The recovered tool request could not be completed. "
                            f"Tool result: {result_str}"
                        ),
                    }
                )

            # Second recovery strategy:
            # Ask the model to retry once using proper structured tool calling.
            retry_succeeded = False

            for _retry in range(MAX_TOOL_RETRIES):
                try:
                    response = _retry_malformed_tool_call(
                        history,
                        recovered_function_name,
                    )
                    retry_succeeded = True
                    break

                except BadRequestError as retry_exc:
                    if not _is_tool_use_failure(retry_exc):
                        raise

            if not retry_succeeded:
                reply = (
                    "I understood the game request, but the game-generation "
                    "tool returned an invalid call. Please try the request again."
                )

                history.append(
                    {
                        "role": "assistant",
                        "content": reply,
                    }
                )

                session_store.save_history(session_id, history)

                return (
                    reply,
                    False,
                    None,
                    None,
                    None,
                )

        message = response.choices[0].message

        if not message.tool_calls:
            reply = message.content or ""

            history.append(
                {
                    "role": "assistant",
                    "content": reply,
                }
            )

            session_store.save_history(session_id, history)

            return (
                reply,
                game_ready,
                game_id,
                game_type,
                game_domain,
            )

        history.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in message.tool_calls
                ],
            }
        )

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = _normalise_tool_arguments(
                tool_call.function.arguments
            )

            result_str, launched = _execute_tool_call(
                session_id,
                function_name,
                arguments,
            )

            if launched:
                game_ready = True
                game_id = launched["game_id"]
                game_type = launched["game_type"]
                game_domain = launched.get("domain")

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                }
            )

    session_store.save_history(session_id, history)

    return (
        "That took a few too many steps. Try describing the game in a simpler way.",
        game_ready,
        game_id,
        game_type,
        game_domain,
    )