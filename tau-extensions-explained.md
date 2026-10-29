# How extensions load in `huggingface/tau`

Notes from reading the source at `main` (`src/tau_coding/extensions/`), not just the docs.

## 1. The shape: a module with a sync `setup(tau)`

An extension is just a Python module defining a module-level function:

```python
def setup(tau: ExtensionAPI) -> None:
    tau.register_tool(AgentTool(...))
```

No base class, no entry-point metadata, no plugin package required. The loader looks only for the `setup` attribute (`EXTENSION_ENTRY_ATTRIBUTE = "setup"`, `src/tau_coding/extensions/loader.py:16`). Async setup is explicitly rejected.

## 2. Discovery — `discover_extensions()` (`loader.py:88`)

Four sources, in load order:

| Source | Location | Notes |
|---|---|---|
| built-in | `src/tau_coding/built_in_extensions.py` | Declared in code, currently `llama.cpp`. Always loads, even with `--no-extensions`. |
| project | `<cwd>/.tau/extensions/` | Only if `include_project_dir=True`; the session hardcodes `False` (`session.py:561`). |
| user | `~/.tau/extensions/` (`<TauPaths.root>/extensions`) | On by default. |
| explicit | `tau -e PATH` | Still loads when `--no-extensions` disables directory scanning. |

What counts as an extension inside a directory:

- `foo.py` → name `foo`
- `foo/extension.py` → name `foo`, loaded as a package
- `foo/pyproject.toml` with `[tool.tau] extensions = ["src/pkg/extension.py", ...]` → each declared file, loaded as a package (the Python analogue of Pi's `package.json` `pi.extensions`)
- Names starting with `_` or `.` are skipped
- Directories are sorted by name, so load order is deterministic

Dedup in `add()`: resolved paths are deduped, and name collisions keep the first-loaded one with a diagnostic. Project is scanned before user, so **project shadows user** — earlier directories win, the opposite of skills precedence, and deliberately noted as Pi parity (`loader.py:73`).

## 3. Loading — `_load_extension()` (`loader.py:313`)

Uses `importlib.util.spec_from_file_location` directly, not `import`. Each module gets a synthetic name:

```
tau_extension_<slugified-name>_<global counter>
```

The counter matters: two files both named `extension.py` never collide in `sys.modules`. If `package_dir` is set, `submodule_search_locations` is passed so the directory is a real package and `from .helper import x` works. The module is inserted into `sys.modules` before `exec_module` and removed again if import fails.

Every failure is caught (`except BaseException`) and converted to a `ResourceDiagnostic` instead of propagating. One broken extension cannot stop Tau from starting. `load_extensions()` returns `(extensions, diagnostics)`.

Discovery freezes every `source_id` (`extension:<file-uri>`) *before* any import (`loader.py:202`), because extension code could retarget symlinks during import. Ownership is tied to the canonical source, not the display name.

## 4. Setup — `ExtensionRuntime._setup_extension()` (`runtime.py:446`)

For each loaded module the runtime builds a fresh `ExtensionAPI(self, name, generation, source_id=...)` and calls `setup(api)`. Every registration is tagged with that `source_id`. If setup raises, the extension is removed and `_remove_registrations(source_id)` runs — rollback is **per-source**, so an extension that registers three tools then throws leaves nothing behind and later extensions are unaffected.

`ExtensionAPI` (`api.py:1028`) is the whole surface:

- `register_tool(AgentTool)` — name/label/description/JSON schema + async `execute_fn` returning `AgentToolResult`
- `register_command(...)` — slash commands
- `register_provider(...)` / `register_local_backend(...)` — dynamic providers, process-local only, never written to `catalog.toml`
- `add_prompt_guideline(text)` / `add_prompt_section(title, body)` — inject into the system prompt
- `on(event, handler)` — `turn_start`, `turn_end`, `tool_call`, `tool_result`, `input`, `session_start`, `session_shutdown`, `project_trust`
- `send_user_message(...)`, `send_custom_message(...)`, `register_message_renderer(...)`
- `tau.ui` — dialogs (`select`/`confirm`/`input`), sidebar sections, slot widgets, main views, key interceptors
- `tau.context` — frozen read-only view: cwd, paths, model, provider, session id, transcript, `project_trusted`

Tool name collisions inside the runtime are **first-registration-wins**: a second extension registering `hello` is ignored with a diagnostic naming both owners (`runtime.py:535`).

## 5. Where it plugs into the session

`CodingSession` constructs an `ExtensionRuntime` and calls `runtime.load(...)` (`session.py:545-567`) **before** project trust is resolved. That ordering is intentional: extensions can participate in the trust decision via the `project_trust` hook (`extension_deciders=(extension_runtime.decide_project_trust,)`), and a project extension can never approve itself.

After trust resolution the runtime is the merge point:

1. `extension_runtime.compose_tools(base_tools)` (`session.py:720`) — extension tools override a built-in of the same name *in place*, extension-only tools append in registration order, then every tool is wrapped by `_wrap_tool` so `tool_call` / `tool_result` hooks run around it. `allowed_tool_names` is applied *after* this, which is why `tools=` alone cannot cap an extension's tools.
2. `prompt_guidelines` / `sourced_prompt_sections` feed the system prompt.
3. `build_command_registry()` becomes the command registry.
4. `bind(session)` then `attach_harness_listener(session._harness.subscribe)` — harness events fan out to extension subscribers — then `emit_session_start("startup")`.

## 6. Lifecycle: generations, not global state

Each runtime belongs to one prepared session snapshot and carries an `ExtensionGeneration`. `/reload`, session replacement and cwd change stage a **brand new** `ExtensionRuntime`, load it, and only then retire the old one (`reset_for_reload` at `runtime.py:400`, `retire()` at 346).

`retire()` / `reset_for_reload()` clear tools, commands, prompt sections, renderers, provider and local-backend registries, unsubscribe from the harness, and `invalidate()` the generation. Any `tau` API object, context, or UI facade captured by extension code from the old generation — including a still-running background task — raises `ExtensionError` on next use instead of silently writing into the new registration set. `unload_extension_modules()` purges every `tau_extension_*` entry from `sys.modules` so a reload re-imports fresh module objects (no stale module-level state).

## 7. Built-ins are the same system with different provenance

`BuiltInExtension(name, setup, hidden=True, setup_with_context=...)` in `built_in_extensions.py`. They go through the identical `_setup_extension` path and the same API — "generic loading never branches on a capability's name". The differences:

- declared in code rather than discovered
- `source_id` is `built-in:<name>`
- load before filesystem sources
- hidden from extension listings
- receive a `BuiltInExtensionContext` (Tau paths, credential store, env snapshot, httpx client) so a bundled integration never reaches for process-global defaults

## 8. Trust

`~/.tau/extensions/` and `-e` paths execute arbitrary Python at session startup with no sandbox. Project extensions therefore need both project-trust approval *and* the explicit `--project-extensions` flag — and `session.py` currently passes `include_project_dir=False` outright. The docs are blunt: trust is not a process, filesystem, network, tool or model sandbox.

## Concrete example — `examples/extensions/permission_gate.py`

```python
def _gate_tool_call(event, context):
    if event.tool_name != "bash":
        return None
    if DANGEROUS.search(event.arguments["command"]):
        return ToolCallHookResult(block=True, reason="...")

def setup(tau):
    tau.on("tool_call", _gate_tool_call)
```

Registers no tool at all — it hooks the wrapper around every tool and returns a block, so `bash` never executes and the model sees the refusal reason.

## Pointers

- Full public reference: `website/content/guides/extensions.md` (848 lines)
- Trimmed version Tau ships to its own agent: `src/tau_coding/data/docs/extensions.md`
- Design journal: `dev-notes/architecture/phase-21-extensions.md`, `dev-notes/architecture/trusted-built-in-extensions.md`
- Two copies of examples: `examples/extensions/` (repo) and `src/tau_coding/data/examples/extensions/` (shipped in the package)
