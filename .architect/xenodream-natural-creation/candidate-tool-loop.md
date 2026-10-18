# Candidate B: model-driven tool loop

Expose scene inspection, capability lookup, add, mutate, group, and validation
as model tools. Let a hosted model call those tools iteratively until it elects
to publish a workspace.

This could adapt after each structural change and eventually handle longer
sessions. It also creates a much larger authority boundary: tool ordering,
partial durable state, retries, token budgets, provider-specific tool-call
formats, and recovery all become product contracts. The current operation
catalog is small enough that an iterative agent adds more failure modes than
capability.

Decision: defer this design until the constrained recipe cannot express a
verified workflow. If adopted later, it should operate on an isolated staged
workspace and publish only after an explicit deterministic verifier succeeds.
