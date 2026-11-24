# VS Code

The AI App Server extension adds:

- **New app from a blueprint** (Command Palette → *AI App: New App from Blueprint…*).
- **Run with Hot Reload, Run Tests, Deploy**, plus *Show Model Calls*, *Show Recent Traces*, *Open Console* and *Start Local Server*.
- An **AI Apps** view in the Explorer, with each app's versions and one-click rollback.
- **Completion and checks for `ai-app.yaml`** (needs the [YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml)).

## Install

Download `aiapp-vscode-VERSION.vsix` from the [Download](../download.md) page, then:

```bash
code --install-extension aiapp-vscode-1.1.0.vsix
```

or in VS Code: Extensions view → `…` menu → *Install from VSIX…*.

The extension talks to a server on the same machine (`aiapp serve`).

## Without the extension

Completion for `ai-app.yaml` works with just the YAML extension: add this line at the top of the file:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/Sandaal/ai-app-server/main/schema/ai-app.schema.json
```

## Coding assistants

Each new app includes `.github/copilot-instructions.md`, so GitHub Copilot (and other assistants that read it) know the SDK and write correct handlers, tools and manifests.
