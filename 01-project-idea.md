# Prompt 01 --- BotMedic Project Idea

Hi Bob, I'm currently working on an IBM hackathon project called
**BotMedic**.

## What BotMedic Does

### The Core Problem

RPA robots (e.g. UiPath, Automation Anywhere, Blue Prism) break when UI
elements change --- a button moves, an ID changes, a label is renamed,
etc. Developers waste hours manually hunting down and fixing these
broken selectors.

### Your Solution --- 3-Layer Architecture

1.  **Fingerprinting (Proactive)**

    When a robot runs successfully, BotMedic captures a rich
    "fingerprint" of each UI element --- not just one attribute (like
    XPath), but multiple: position, text, parent hierarchy, CSS class,
    color, size, etc. This creates a resilient multi-attribute snapshot.

2.  **Auto-Healing (Reactive --- No AI)**

    When a robot fails, BotMedic tries to find the correct element using
    the stored fingerprint --- fuzzy matching and similarity scoring
    across attributes. Simple drift (e.g. an ID changed but text and
    position are the same) is resolved automatically, with no AI needed.

3.  **IBM Bob Escalation (Complex Cases)**

    If auto-healing can't confidently resolve the problem, the case is
    escalated to Bob (LLM), which analyzes the context and proposes a
    fix. The fix is automatically retested before being returned to the
    developer --- so they get a verified solution, not a guess.
