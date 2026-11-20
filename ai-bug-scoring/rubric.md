# Factor rubric: Jahia bug scoring, system A2

You read one Jahia bug ticket and record the factors that the PM score needs. You do not compute the
score: a script adds the points. Judge the ticket from its own title, body, labels and comments
only.

Write one JSON object per ticket, with exactly these keys.

## ref

Copy it from the ticket file.

## security (boolean)

`true` only for a real security impact: an authentication or authorization bypass, access to data
the caller should not see, code or command execution, an exposed secret, a CVE. A security ticket
gets no score. Still fill the other factors.

## impact (string, exactly one)

Pick the WORST line that applies, from the point of view of Jahia's customers.

| value | meaning |
| -- | -- |
| `data` | Content loss or data corruption, in production. Example: publication drops translations. Also: the authoring UI drops an editor's typed work without warning, saved or not. Example: switching language empties an unsaved rich text field. |
| `unstable` | The platform behaves erratically in production: crashes, hangs, memory leaks, jobs that stop, failures you cannot predict. |
| `siteDown` | A production site is fully broken for its visitors: every page or the whole site errors or is unreachable. |
| `sitePartial` | Visitors are impacted, but the site still works: a page or a component is broken, wrong content shown, slow pages, SEO output wrong (sitemap, metadata). |
| `editorBlocked` | An editor or an administrator cannot complete a task in the authoring or admin UI. |
| `devBlocked` | A developer cannot complete a task: an API returns wrong results or fails, a build, a deploy or a module install fails. Developers follow the same rule as editors. |
| `hindered` | Editors, administrators or developers are slowed down or annoyed, but can complete the task: confusing message, extra clicks, a slow screen, noisy logs. |
| `cosmetic` | Visual glitch or wording only. |

`data`, `unstable` and `siteDown` need a production effect. A failure seen only in a test setup, a
CI pipeline or a developer's local install is never one of these three.

A ticket about Jahia's own internal tooling (its CI, its test libraries such as jahia-cypress) is
`devBlocked` or `hindered`.

## feature (string)

The feature or module the failure is in, in 2–5 plain words. Example: "publication workflow",
"jContent media picker", "Forms submissions".

## reach (string: `high`, `medium`, `low`)

The share of Jahia customers who use that feature. Use this list as the anchor, and judge a feature
inside core (`jahia-private`) by what it is.

- **high**: core features every site uses (publication, page rendering and cache, URLs and vanity
  URLs, content storage, permissions, users and groups, languages, workflow, module deployment),
  jContent and the content editor, the CKEditor rich text, GraphQL as the authoring UI uses it, the
  CSRF guard.
- **medium**: sitemap, Forms, Augmented Search, jExperience, jCustomer, SAML single sign-on, the
  administration pages (server settings), cluster-only features, the server availability manager,
  Jahia Cloud platform modules (jahia-cloud-modules), the Maven build plugin (jahia-configuration),
  GraphQL as customer code uses it, external data providers.
- **low**: the Keepeek picker (keepicker), remote publication (remotepublish), content versioning,
  rare configurations (for example a private site with a custom error page), one browser or one
  language only, Jahia's internal tooling.

## workaround (string: `none`, `painful`, `easy`, `unknown`)

- `easy`: a simple way around exists or is stated. Example: use another browser.
- `painful`: a way around exists but costs real effort or a restart, or needs Jahia support.
- `none`: the ticket says there is none, or none is reasonably possible.
- `unknown`: you cannot tell.

## regression (boolean)

`true` only when the ticket says it worked before: a `regression` label, "worked in 8.1", "since the
upgrade", "this used to work", or a last version that worked. Otherwise `false`.

## clear (boolean)

`true` when the expected behaviour is stated concretely, or is obvious from the symptom (an error
500, an exception, a crash, data that disappears: the expected behaviour is that it does not
happen). `false` when the reader must guess what "correct" looks like.

## cloud (boolean)

`true` when the repository is jahia-cloud-modules, when the ticket has a `cloud` label, or when the
text says the failure happens on Jahia Cloud.

## older_version_only (boolean)

`true` only when every Jahia version the ticket names is below 8.2.0 (for example 8.1.x or 7.x),
and nothing in the text says it also happens on 8.2 or later. Also `true` when the text says it no
longer happens on a recent version. `false` otherwise, including when no version is named.

## customers (integer)

The number of distinct customers hit by the bug, as the ticket and its comments name them. Count
each customer once. A customer name, a support ticket, "a second customer" or "new occurrence at
another customer" each add one. The reporter counts when the text says the report comes from a
customer or a support ticket. A link to an older ticket adds one only when it names another
customer. 0 when the text names none.

## confidence (string: `high`, `medium`, `low`)

Your confidence in the `impact` value.

## why (string)

One plain sentence of 25 words or fewer: why you chose this impact and this reach. Write it for the
team that reads the ticket. Name no customer, and quote no secret, URL or code.
