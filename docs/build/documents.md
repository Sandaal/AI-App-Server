# Documents and connectors

Apps answer from **sources**: folders on disk, or connectors that sync from other systems. Documents are split into chunks, embedded with the app's `embedding` model, and stored in the app's `sources` collection, encrypted.

**File types:** PDF, Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`), HTML, Markdown, text, CSV and email (`.eml`). Scanned PDFs need OCR first.

## Local folders

```bash
aiapp source add ./policies/      # adds it to ai-app.yaml and indexes it
aiapp deploy
```

```yaml
sources:
  - path: ./policies/
  - path: ./faq.md
    chunking: { size: 800, overlap: 100 }     # characters per chunk (optional)
```

Only new and changed files are re-indexed on each deploy. `aiapp jobs` shows indexing progress.

## Connectors

Connectors sync on a `schedule` (such as `1h` or `@daily`). `aiapp sources` shows their status; `aiapp source sync APP [NAME]` syncs now. Deleted documents are removed from the index.

=== "Git"

    ```yaml
    sources:
      - name: handbook
        git: { url: "https://github.com/contoso/handbook", branch: main, paths: [docs/], token: "${GITHUB_TOKEN}" }
        schedule: 1h
    ```

=== "Websites"

    ```yaml
    sources:
      - name: website
        http: { sitemap: "https://www.contoso.com/sitemap.xml", max_pages: 500 }
        # or: http: { urls: ["https://www.contoso.com/help", "https://www.contoso.com/faq"] }
        schedule: 24h
    ```

=== "SharePoint / OneDrive"

    Register an Entra ID app with the Microsoft Graph permission `Sites.Read.All` (or `Files.Read.All` for OneDrive), as an application permission with admin consent.

    ```yaml
    sources:
      - name: hr-site
        sharepoint:
          tenant: contoso.onmicrosoft.com
          client_id: 00000000-0000-0000-0000-000000000000
          client_secret: "${GRAPH_CLIENT_SECRET}"
          site: contoso.sharepoint.com:/sites/hr
          folder: Policies               # optional; drive: "Documents" picks the library
        schedule: 1h
    ```

    For OneDrive, use `user: someone@contoso.com` instead of `site:`.

=== "S3"

    ```yaml
    sources:
      - name: manuals
        s3: { bucket: product-manuals, prefix: en/, region: eu-west-1 }   # keys from AWS_* or access_key/secret_key
        schedule: 6h
    ```

    For S3-compatible storage (MinIO…), add `endpoint:` and `path_style: true`.

=== "Azure Blob"

    ```yaml
    sources:
      - name: contracts
        azure_blob: { account: contosodocs, container: contracts, prefix: 2026/, sas: "${AZURE_BLOB_SAS}" }
        schedule: 6h
    ```

    The SAS needs read and list permissions.

=== "SQL"

    Each row becomes a document:

    ```yaml
    sources:
      - name: kb-articles
        sql:
          driver: postgres          # or sqlserver
          dsn: "${KB_DATABASE_URL}"
          query: "SELECT id, title, body, updated_at FROM articles WHERE published"
          id: id
          text: body
          title: title              # shown in citations
          updated: updated_at       # only changed rows are re-indexed
        schedule: 30m
    ```

## Code repositories

For the `code-assistant` blueprint, set `code: true` on a source: code is split along functions and classes, and answers cite files and line numbers.

## Searching sources from your code

```python
hits = await app.vectors.search("sources", "parental leave", k=5, mode="hybrid")
for h in hits:
    print(h.score, h.metadata["source"], h.metadata.get("page"), h.text[:80])
```

See [Storage, memory and search](storage.md).
