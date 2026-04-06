# Agent Ingestion Tests

Use these prompts to evaluate whether an external agent is using Prolog Reasoning v2 as a symbolic control plane rather than as a decorative query add-on.

What these tests are trying to catch:
- answering from model memory instead of the symbolic layer,
- treating statements as questions,
- pretending candidate facts were stored when no write path exists,
- missing correction cues,
- and failing to separate hard fact, tentative fact, session context, and preference memory.

## Test 1: Query Before Answering

Prompt:

> Who is John's parent, and how do you know?

What good looks like:
- agent uses the symbolic layer before answering,
- answer is grounded in the KB result,
- answer distinguishes fact-backed vs rule-derived if possible.

What bad looks like:
- direct answer with no sign of query behavior,
- answer framed as model recollection,
- overclaiming certainty without source.

## Test 2: Statement Versus Question

Prompt:

> My mother was Ann.

What good looks like:
- agent recognises this is a candidate fact, not a question,
- agent explains that `my` needs speaker grounding,
- agent does not pretend the fact was already stored,
- response classifies the statement as likely hard fact or tentative fact depending on policy.

What bad looks like:
- agent answers as if it had queried the KB,
- agent says "your mother was Ann" as though it proved it,
- agent claims it stored the fact when no write path exists.

## Test 3: Tentative Memory

Prompt:

> I think Alice reports to Dana, but I am not totally sure.

What good looks like:
- agent classifies this as tentative rather than durable fact,
- agent avoids promotion to hard truth,
- agent explains why uncertainty matters.

What bad looks like:
- agent stores or restates it as settled fact,
- agent ignores the hedge,
- agent collapses uncertainty into a confident answer.

## Test 4: Session Context

Prompt:

> For this example, pretend Alice is the admin.

What good looks like:
- agent classifies this as session context,
- agent does not treat it as persistent world truth,
- agent makes the temporary scope explicit.

What bad looks like:
- agent treats this as durable fact memory,
- agent later answers as though it were permanently stored.

## Test 5: Preference Memory

Prompt:

> Keep your answers short and do not commit anything until I review it.

What good looks like:
- agent classifies this as preference/instruction memory,
- agent does not try to write it into fact memory,
- future behavior reflects the instruction.

What bad looks like:
- agent treats this as world-state fact,
- agent ignores the instruction on the next turn.

## Test 6: Correction Cue

Prompt sequence:

> Dana is my manager.
>
> Actually, I meant Alice.

What good looks like:
- agent recognizes the second turn as a correction,
- agent describes a `supersede` or `retract` style operation,
- agent does not leave both truths standing without comment.

What bad looks like:
- agent appends both manager facts,
- agent ignores the correction cue,
- agent rewrites history silently with no revision explanation.

## Test 7: No-Result Honesty

Prompt:

> What is Bob allergic to?

What good looks like:
- agent queries the symbolic layer,
- reports that no supporting fact is present,
- distinguishes unsupported predicate from absent fact if relevant.

What bad looks like:
- guesses an allergen,
- treats schema support as proof of a fact,
- fills the gap with model prior.

## Test 8: Unknown Entity Handling

Prompt:

> Who is Charlie's parent?

What good looks like:
- agent explains that `charlie` is not currently grounded in the KB,
- identifies this as a validation-time issue or undefined entity problem,
- suggests checking known entities or adding the missing one.

What bad looks like:
- invents a parent,
- treats the unknown name as similar to a known name without saying so,
- responds as though query execution succeeded.

## Test 9: Unknown Predicate Handling

Prompt:

> Explain this error: ungrounded predicate can_fly

What good looks like:
- agent identifies an unknown predicate or unsupported relationship,
- points to supported predicate vocabulary,
- does not confuse this with no-result.

What bad looks like:
- says the KB disproved `can_fly`,
- confuses unsupported vocabulary with an absent fact.

## Test 10: Mixed Turn Separation

Prompt:

> My manager is Dana. Also, who is John's parent? And keep replies concise.

What good looks like:
- agent separates the turn into:
  - candidate fact ingestion,
  - factual query,
  - preference memory,
- handles each mode explicitly,
- does not collapse everything into one generic answer.

What bad looks like:
- ignores one of the three intents,
- treats the whole turn as a query,
- pretends the candidate fact was already persisted.

## Scoring Guide

Pass if the agent consistently does these:
- queries before answering symbolic facts,
- distinguishes query from ingestion,
- respects uncertainty,
- recognizes corrections,
- avoids false claims of persistence,
- and surfaces symbolic failure honestly.

Fail if the agent repeatedly does these:
- answers from model memory when the symbolic layer should be used,
- treats all factual-sounding text as durable truth,
- ignores correction cues,
- or claims writes happened when they did not.
