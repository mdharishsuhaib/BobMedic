# Prompt 02 --- Target Web App Task

I am responsible for the "Target Web App" component of our BotMedic
hackathon project.

Your task is to help me build ONLY this component. Other team members
are separately working on the RPA bot, parser/watcher, diagnosis engine,
dashboard, and submission.

Please do not build those other components.

## Goal

Build a small fictional banking internal web application that will
intentionally break during our BotMedic demo.

The application must be completely frontend-only:

-   Plain HTML
-   CSS
-   Vanilla JavaScript
-   No framework
-   No build step
-   No backend
-   No external dependencies
-   It must work by simply opening the HTML files locally in a browser.

The application should look like boring but credible internal banking
software. Do not make it look like a modern startup landing page.

Use a fictional bank name.

------------------------------------------------------------------------

# PAGE 1 --- Login

Create a login page containing:

-   Username input
-   Password input
-   Submit button

The submit button MUST initially have exactly:

id="btn-login" class="btn primary" type="submit"

Visible text:

"Sign in"

Any credentials should be accepted.

When the form is submitted successfully, redirect the user to Page 2
(Invoices).

IMPORTANT:

Do NOT add any data-testid attribute to this button.

The stable signals we want BotMedic to use are:

-   visible text
-   class
-   type
-   DOM structure
-   position
-   other normal HTML attributes

------------------------------------------------------------------------

# PAGE 2 --- Invoices

Create an internal banking-style invoice management page.

Include a table containing approximately 8 fake invoices.

Columns:

-   Invoice number
-   Client
-   Amount
-   Date
-   Status

Add a button:

id="btn-export"

Visible text:

"Download CSV"

The export button should have a stable class as well.

It should have simple functionality: clicking it can generate/download a
CSV containing the fake invoice data.

Also add several other buttons and links on this page.

This is important because BotMedic's candidate-ranking engine needs
realistic competing elements. The correct replacement element should NOT
be the only possible candidate.

Keep the page visually clean and simple.

------------------------------------------------------------------------

# PAGE 3 --- Payment Submission

Create a third page for the irreversible-action demo.

It should contain:

-   Recipient input
-   Amount input
-   Submit payment button

The payment button MUST initially have:

id="btn-pay"

Visible text:

"Submit payment"

This page does not need to perform a real payment.

It only exists so that our second RPA bot has an irreversible action to
interact with during the demo.

Do NOT implement any real payment functionality.

------------------------------------------------------------------------

# MOST IMPORTANT --- Break Control Panel

Create a hidden page:

/break.html

This page is extremely important.

It must contain controls that allow us to intentionally break the target
application without editing source code during the demo.

Create four toggle switches:

1.  Rename login button ID

Initial: btn-login

Broken: auth-submit-v2

2.  Move login button

Move the login button into a different container div.

3.  Change login button text

Initial: "Sign in"

Broken: "Login"

4.  Rename export button ID

Initial: btn-export

Broken: export-data-btn

Each toggle must store its state in localStorage.

The Login and Invoice pages must read these states from localStorage
when they load and render themselves accordingly.

For example:

If "rename login button ID" is enabled:

The login button should actually render as:

id="auth-submit-v2"

instead of:

id="btn-login"

If the toggle is disabled, it should return to:

id="btn-login"

The same principle should apply to the other break scenarios.

The break panel should also make it easy to reset all break states.

Please make the toggles visibly show whether each break is currently ON
or OFF.

------------------------------------------------------------------------

# Important Design Constraints

DO NOT add:

-   data-testid attributes
-   React
-   Vue
-   Angular
-   TypeScript
-   backend
-   database
-   unnecessary libraries
-   unnecessary animations
-   unnecessary features

DO add:

-   stable visible text
-   stable CSS classes
-   realistic DOM structure
-   several competing buttons/links on the invoice page
-   enough structure for fingerprinting and candidate ranking to be
    meaningful

The whole point is that when an ID changes, BotMedic should still be
able to identify the correct element using other signals.

For example, the login button should initially have:

id="btn-login" class="btn primary" type="submit" text="Sign in"

If its ID is changed to:

id="auth-submit-v2"

the other characteristics should remain available so BotMedic can
recognize it.

------------------------------------------------------------------------

# File Structure

Please use a simple structure such as:

/index.html /invoices.html /payment.html /break.html /css/style.css
/js/app.js /js/break.js /README.md

You may adjust the structure if there is a strong reason, but keep it
simple.

------------------------------------------------------------------------

# Demo Requirements

The following demo must be possible:

1.  Open login page.
2.  RPA bot successfully finds #btn-login and clicks it.
3.  User opens /break.html.
4.  User enables "Rename login button ID".
5.  Login page now uses auth-submit-v2.
6.  RPA bot attempts to use #btn-login and fails.
7.  BotMedic can then detect the failure and identify the replacement
    element using its fingerprint.
8.  The break can be disabled and the application should return to its
    original state.

The same system should allow us to test:

-   ID change
-   Element movement
-   Text change
-   Export button ID change

without modifying source code.

------------------------------------------------------------------------

# Important Implementation Detail

Do not make the break panel itself part of the normal application
navigation.

It is a hidden developer/demo control panel that we can directly open
using:

/break.html

The target application should still feel like a normal internal banking
application.

------------------------------------------------------------------------

# DONE WHEN

The component is complete when:

-   All three application pages work.
-   /break.html works.
-   All four break toggles work.
-   Break states persist through localStorage.
-   Pages render according to the break states.
-   Login works with any credentials.
-   Login redirects to invoices.
-   Invoice table contains approximately 8 fake invoices.
-   Download CSV works.
-   Payment page exists with the Submit payment button.
-   The application works by opening the HTML files locally without a
    server.
-   There are several competing buttons/links on the invoice page.
-   No data-testid attributes are used on the important target elements.
-   The code is simple enough for our team to understand and modify
    during the hackathon.

Before writing code, briefly explain the proposed file structure and
implementation approach.

Then implement the complete target web app.
