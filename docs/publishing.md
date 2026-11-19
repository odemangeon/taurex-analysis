# Building and publishing documentation

The site uses MkDocs, Markdown and the built-in search plugin. Building the docs
requires no TauREx installation, opacity files, shared filters or retrieval data.

## Local preview

From the repository root:

```bash
python -m venv /tmp/taurex-docs-env
/tmp/taurex-docs-env/bin/python -m pip install -r requirements-docs.txt
/tmp/taurex-docs-env/bin/python -m mkdocs serve
```

Open the local address printed by MkDocs. To validate and build:

```bash
/tmp/taurex-docs-env/bin/python -m mkdocs build --strict
```

The generated files go to `site/`, which is ignored by version control.
Edit the Markdown in `docs/`; add new pages to `mkdocs.yml` navigation.
Keep parameter documentation aligned with the model constructors, fit-parameter
names and validation rules. No generated scientific outputs are included.

## GitHub Pages setup

1. Commit and push the documentation, `mkdocs.yml`, `requirements-docs.txt`, and
   `.github/workflows/docs.yml` to your GitHub repository.
2. In repository **Settings → Pages → Build and deployment**, select
   **GitHub Actions** as the source.
3. Run the **Documentation** workflow from the Actions tab, or push a change to
   the default branch.
4. Open the URL shown by the deployment job's `github-pages` environment.

The workflow builds on pull requests and pushes. It deploys only from the
repository's default branch, including manual runs on that branch. Pull requests
never deploy. No personal access token is required: the deployment job uses
GitHub's scoped workflow token and OIDC permissions.

The workflow does not assume an owner, repository name or default branch name.
Relative site links support a repository Pages URL. Once the repository URL is
known, `site_url` and `repo_url` can optionally be added to `mkdocs.yml`.

See GitHub's [custom Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
and the [MkDocs configuration reference](https://www.mkdocs.org/user-guide/configuration/).

## Troubleshooting

- **Build fails on a link:** fix the referenced Markdown path or anchor; strict
  builds deliberately fail on warnings.
- **Deployment is skipped:** check that the workflow ran on the default branch.
- **Pages configuration fails:** confirm Pages is available for the repository
  and GitHub Actions is selected as its publishing source.
- **Environment approval pending:** review the repository's `github-pages`
  deployment-environment rules.
