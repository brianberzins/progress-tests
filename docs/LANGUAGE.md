# Language

A glossary of domain terms for this library. No implementation details —
see `docs/design/` for those.

## Step

One deterministically-verifiable checkpoint in a progressive test's
ordered sequence. Identified by a `STEP_NAME`. A step's position in the
sequence is positional, not separately declared. Every step is
evaluated for every input regardless of any other step's result — a
step that reads a parameter an earlier step would have contributed is
naturally gated by that data being present, not by the runner stopping
early on its behalf.

## Class

The result of evaluating one step: `pass`, `wait`, or `fail`.

## Input

One instance's set of parameters, evaluated against the same ordered
sequence of steps as every other input belonging to the same progressive
test. Not every step necessarily applies to every input. A progressive
test with exactly one input (or none declared) is not a special case —
it's the same mechanism with one input instead of many. A step may
contribute new parameters to an input for later steps to use; two
different values claimed for the same parameter is ambiguous and is
never resolved silently.

## Progressive Test

An ordered sequence of steps, every one of which is evaluated for each
input regardless of any other step's result. A fully-passing
progressive test is a long-lived assertion of the final desired state,
not a disposable migration artifact — it keeps running in CI after the
state it verifies is reached.

## Progressive Table Test

The rendering of a progressive test's results as a grid: one row per
input, one column per `STEP_NAME` in first-seen order. Visualizes what
the progressive test already determined for each input; adds no
pass/fail judgment of its own beyond what the standard's `wait`/`fail`
policy already assigns.
