# Deployment

Use Cloudflare Pages Git integration to publish the MkDocs documentation site.

## Build Locally

Run the local build helper before changing deployment settings:

```bash
bash scripts/build-docs.sh
```

The script installs `uv` when it is missing, then builds the MkDocs site with the committed lockfile. The generated site is written to `site/`, which stays uncommitted.

## Cloudflare Pages

Create a Pages project from the Git repository and use these build settings:

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Root directory | `/` |
| Build command | `pip install uv && uv run --extra docs mkdocs build --strict` |
| Build output directory | `site` |

Set these environment variables in the Pages project:

| Variable | Value |
| --- | --- |
| `PYTHON_VERSION` | `3.12` |
| `SKIP_DEPENDENCY_INSTALL` | `1` |

`PYTHON_VERSION` matches the repository `.python-version` file. `SKIP_DEPENDENCY_INSTALL` leaves dependency installation to the build command, so Cloudflare does not try an automatic install before the project-specific command runs.

Cloudflare will deploy the production branch to `<project>.pages.dev` and create preview deployments for pull requests and non-production branches.

## Custom Domain

After the first deployment succeeds, open the Pages project in Cloudflare and add the documentation domain under **Custom domains**. Cloudflare will create the DNS record and certificate when the domain is managed in the same Cloudflare account.

## Direct Upload Fallback

Use Direct Upload only when the Git integration is not available:

```bash
bash scripts/build-docs.sh
CLOUDFLARE_ACCOUNT_ID=<account-id> npx wrangler pages deploy site --project-name=kithairon-docs
```

Direct Upload is a separate Pages project mode. Do not switch an existing Git-integrated project to it unless you intentionally disable automatic Git deployments.
