# ADR 0013 — MIT License for the Public Release

**Date**: 2026-11-10 (MIT in force since the initial scaffold, 2026-05-19; confirmed
before the repository goes public)
**Status**: Accepted

---

## Context

The repository has been private since inception and has a single author. The MIT
license was set by the initial scaffold (`LICENSE`, README "License" section) and
VISION §6 states "MIT License · open-source forever for the core · future commercial
version possible (managed hosting, premium support)". That choice was never
challenged.

The repository is about to go public, before the v0.1 MVP is complete. Its primary
purpose is a public portfolio: architecture, ADRs, specs, reviews and tests are meant
to be read. A future revenue stream remains possible but uncertain, most plausibly a
hosted subscription for solopreneurs whose machine cannot run local models.

The license must be decided **before** the first public push: code published under a
license stays available under that license permanently, even if later versions are
relicensed.

Forces at play:

- **The valuable features are close.** The agent loop, the 2D workspace and real
  execution are weeks away, not months. The argument "there is nothing worth
  protecting yet" does not hold for long.
- **The code is not the moat in this category.** As of 2026-11, funded SaaS products
  already sell pre-built "AI employees" to small businesses, and several open-source
  projects (most under MIT) already ship agent teams in a 2D/pixel-art office with
  local-first runtimes. A competitor does not need this codebase to build a similar
  product. What a hosted product would compete on is distribution, integrations,
  reliability, security and support.
- **Local-first and paying customers barely overlap.** Users who run Ollama tend to
  expect free, open software; users who pay for AI employees tend not to run local
  models.
- **Brand assets exist independently of the code**: the Adjents name and the
  `adjents.com` domain.
- **The author is the sole copyright holder** and can license future versions
  differently, as long as no third-party code is merged without a rights grant.
- **Consistency**: the author's other public repositories are MIT-licensed.

---

## Decision

**Keep the MIT license** for the public release, with three guardrails.

1. **No external code contributions without a CLA.** Issues and discussions are
   welcome; pull requests from third parties are not merged until a Contributor
   License Agreement is in place. This keeps the author the sole copyright holder, so
   the license of future versions remains the author's decision alone.
2. **The license covers the code, not the brand.** The README states that the
   Adjents name, logo and the `adjents.com` domain are not licensed under MIT. A fork
   may reuse the code but must not present itself as Adjents.
3. **Explicit review trigger.** The license of *future* versions is re-evaluated —
   with FSL-1.1-ALv2 as the default candidate — if either of these happens:
   - a paid hosted version of Adjents is launched or actively prepared;
   - the project shows traction that makes a commercial clone plausible (sustained
     stars/forks growth, users asking for a hosted version).

   Versions already published under MIT stay under MIT.

Any monetization in the meantime goes through services (installing and adapting
Adjents for a business), which MIT does not restrict for the author.

---

## Alternatives Considered

| Option | Reason rejected |
| --- | --- |
| **FSL-1.1-ALv2** (Fair Source: source-available, no competing commercial use, each version converts to Apache-2.0 after 2 years) | Best fit for protecting a hosted offer, and the default candidate if guardrail 3 triggers. Rejected for now: it protects code that competitors can already obtain elsewhere for free, the project can no longer be called "open source", and the commercial upside it guards is speculative. |
| **AGPL-3.0** | OSI-approved and blocks closed-source SaaS forks, but does not prevent a competitor from hosting Adjents commercially if it publishes its changes. Some companies ban AGPL internally, which slows adoption. Middle ground that serves neither goal fully. |
| **Apache-2.0** | Same commercial exposure as MIT. Its patent grant and explicit trademark clause matter little for a single-author project; the trademark point is covered by guardrail 2. Switching would break consistency with VISION §6 and the author's other repositories for no practical gain. |
| **BSL 1.1** | Strong protection, but poor community perception since high-profile relicensings to BSL triggered forks; conversion period (up to 4 years) is long for a fast-moving AI product. |
| **Custom "sustainable use" licenses** (n8n Sustainable Use License, Elastic License 2.0) | Non-standard text, harder for readers and recruiters to evaluate; Elastic itself added AGPL back in 2024. |
| **Public repository without a license** (all rights reserved by default) | Visible but unusable: nobody may legally reuse or contribute. Looks unfinished and contradicts VISION §6. |
| **Keep the repository private** | Defeats the portfolio purpose; the work cannot be evaluated by employers or clients. |

---

## Consequences

**Positive:**

- Maximum readability and reuse: a standard, universally understood license, no
  friction for developers, recruiters or clients evaluating the code.
- No change needed to `LICENSE` or VISION §6; consistent with the author's other
  public repositories.
- The option to monetize stays open: the brand is protected separately (guardrail 2)
  and future versions can be relicensed (guardrails 1 and 3).

**Negative:**

- Anyone may fork the published code, rebrand it and sell it, including as a hosted
  SaaS, without paying or visibly crediting the author. MIT only requires keeping the
  copyright notice in the distributed source.
- Relicensing later only protects *new* versions; every version published before the
  switch remains freely usable under MIT.
- Refusing external pull requests limits community contributions until a CLA exists.
- License-based protection is weaker than it looks in any case: enforcing a license
  against a company is costly for an individual. This is one more reason not to rely
  on the license as a moat, whichever license is chosen.

**Follow-up (public release preparation):**

- README: add the trademark notice (guardrail 2) and the contribution policy
  (guardrail 1).
- VISION §6: add a pointer to this ADR and its review trigger.
