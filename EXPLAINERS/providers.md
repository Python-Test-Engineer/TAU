# Tau provider defaults

Tau stores your saved provider and model defaults in:

- `C:\Users\mrcra\.tau\providers.json`

## What matters most

Two parts control the default model Tau uses when it starts:

### 1. `default_provider`
This decides which provider Tau uses by default.

Current value:

```json
"default_provider": "openai"
```

That means Tau starts with the `openai` provider unless you override it with CLI flags like `--provider` or resume a session with a different saved model.

### 2. `provider_preferences.<provider>.default_model`
Each provider has its own saved default model.

Example for OpenAI:

```json
"openai": {
  "default_model": "gpt-5.4"
}
```

Because your `default_provider` is `openai`, Tau will normally start with:

- Provider: `openai`
- Model: `gpt-5.4`

## How to change the startup default

Edit `providers.json` and change:

### Change provider

```json
"default_provider": "openai"
```

Example:

```json
"default_provider": "openrouter"
```

### Change model for that provider

Example current OpenRouter setting:

```json
"openrouter": {
  "default_model": "qwen/qwen3.7-max"
}
```

If `default_provider` is set to `openrouter`, Tau will start with that model.

## Important rule

The model must belong to the provider.

If you set a model name that is not valid for that provider, Tau may ignore it and fall back to the provider's normal default.

## Current notable defaults in your file

- `openai` → `gpt-5.4`
- `openai-codex` → `gpt-5.5`
- `anthropic` → `claude-sonnet-4-6`
- `openrouter` → `qwen/qwen3.7-max`
- `google` → `gemini-flash-latest`
- `groq` → `openai/gpt-oss-120b`
- `mistral` → `devstral-medium-latest`
- `moonshotai` → `kimi-k2.7-code`
- `deepseek` → `deepseek-v4-pro`

## Easiest non-manual method

Inside Tau:

1. Start `tau`
2. Run `/model`
3. Choose the model you want
4. Send a message

That saves the choice as the durable default for future sessions for normal providers.

## Note about local `llama.cpp`

Tau's built-in `llama.cpp` backend is special. It is not treated like a normal durable startup default provider in the same way. For that backend, it is safest to start Tau explicitly with:

```bash
tau --provider llama.cpp --model <exact-model-id>
```
