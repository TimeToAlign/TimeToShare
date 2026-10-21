# 0008. Publish both packages and the schema site from one release workflow

Date: 2026-10-09

## Context

The Python and npm packages share one schema version and must be published
together without long-lived registry secrets. Every version's schema
document names its own URL as its `$id`, and a host that refers to it must
be able to fetch it there.

## Considered options

- One tag and one workflow using OIDC trusted publishing.
- Two tags.
- Stored PyPI and npm tokens.
- release-please.
- Write release automation ourselves.
- Serve the schema documents from GitHub Pages, deployed by the release
  workflow: the repository's own Pages site, the organisation site, or
  both.
- Serve them from a registry CDN (the npm package's files) or from raw
  repository URLs.

## Decision

Publish both packages from one version tag using GitHub Actions OIDC trusted
publishing. TimeToAlign maintainers retain a single review point, and the bus
factor is improved by avoiding personal tokens. Primary sources:
https://docs.pypi.org/trusted-publishers/, https://docs.npmjs.com/trusted-publishers,
and https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect.

npm configures a trusted publisher only for a package that already exists,
so the first publish of the npm package authenticates with an `NPM_TOKEN`
secret. The npm step tries trusted publishing first and uses the token only
while the secret exists; it is deleted once the trusted publisher is
configured. PyPI accepts a trusted publisher for a project before its first
release and needs no token.

Every released schema is served at two addresses. Its `$id` is lowercase,
`https://timetoalign.github.io/timetoshare/<version>/timetoshare.schema.json`,
a path of the organisation site, which the repository
`TimeToAlign/timetoalign.github.io` publishes. The repository
`TimeToAlign/TimeToShare` publishes its own Pages site under
`https://timetoalign.github.io/TimeToShare/`, and a Pages path is
case-sensitive: `/TimeToShare/` and `/timetoshare/` are different addresses,
and a project site is served only under its repository's name as spelled.
So two jobs follow the publishing:

- The pages job deploys the repository's Pages site holding
  `<version>/timetoshare.schema.json` for every released tag, assembled from
  the tags themselves, so every released schema stays served at
  `https://timetoalign.github.io/TimeToShare/<version>/timetoshare.schema.json`.
  It uses GitHub's own actions `actions/configure-pages@v6`,
  `actions/upload-pages-artifact@v5` and `actions/deploy-pages@v5`, and no
  other dependency. Primary source:
  https://docs.github.com/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages.
- The org-site job copies the released schema from the release tag to
  `timetoshare/<version>/timetoshare.schema.json` in the organisation site's
  repository and pushes it to that repository's default branch as
  `github-actions[bot]`, committing only when the file changed, so the
  `$id` resolves. It authenticates with a deploy key, the secret
  `ORG_SITE_DEPLOY_KEY`, which may write to that one repository only, and
  uses `actions/checkout@v7` and git alone. Primary source:
  https://docs.github.com/authentication/connecting-to-github-with-ssh/managing-deploy-keys.

## Consequences

The workflow depends on a token only for the npm package's first publish,
and on nothing that enters a package's runtime. GitHub Actions and publisher
actions carry their own licences and transitive action dependencies. One
release cadence keeps versions aligned; exiting to separate tags costs
process and version checks. Writing OIDC exchange logic ourselves would add
security-sensitive maintenance. Each deployment replaces the whole site, so
the repository's site depends on the release tags alone, never on a stored
copy. The organisation site keeps every schema it was given, one commit per
release, and depends on the deploy key; without the key the `$id` of a new
release stays unresolved while the repository's site serves it. A registry
CDN or a raw repository URL would not resolve the `$id` the document names,
and a lowercase repository name would serve the `$id` from the repository's
site alone, at the cost of a repository name differing from the format's.

## Review date

2027-10-09.
