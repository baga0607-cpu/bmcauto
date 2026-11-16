# RF-01-012 Link syntax and compatible parsing

2026-11-16. Step 2 separately checks RFC8288 parameter syntax. Unquoted values containing non-token characters fail the syntax checkpoint while compatible parsing continues through target/anchor validation and resource traversal. Syntax-only failures do not create unread-resource evidence. Final case status remains Fail for syntax violations.

19 offline test groups cover quoted/token success, unquoted path/anchor/media-type failures, continued Step 3 and child traversal, malformed headers and existing URI rules. Network access is blocked. Run: python web_ui/tests/test_rf012_link_syntax.py. Creation timestamp is preserved.

The user reports manually updating the Test Case Repository. This commit updates the tracked source mirror and tests only; no database/Plan mutation, service restart or live DUT test was performed here. The earlier compatibility-only version passed on the user's DUT; the final syntax-verdict revision has not been reported as live-tested.
