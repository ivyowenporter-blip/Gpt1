# GPT Browser Middleware

This package defines a JSON schema that large language models can use to request browser actions and a middleware that translates those requests into real browser adapter calls. It also keeps track of state, provides safety checks, and enforces timeouts.

## Schema overview

Each tool request must contain an `id`, an `action`, and optional `params`:

```json
{
  "id": "navigate-1",
  "action": "navigate",
  "params": { "url": "https://example.com" }
}
```

Supported actions:

- `navigate`: requires a safe `http`/`https` URL.
- `click`: requires a CSS selector.
- `extractText`: requires a CSS selector and optional `timeoutMs`.

Requests are validated with protocol, selector length, and timeout limits before the middleware executes them.

## Browser middleware

`BrowserMiddleware` accepts a browser adapter with `navigate`, `click`, and `extractText` functions. It:

1. Validates tool requests against the schema and per-action guards.
2. Applies safety checks, timeouts, and error handling.
3. Executes the requested action using the adapter.
4. Returns structured responses to the model, including latest state and rolling history.

Example usage:

```js
const { BrowserMiddleware, MockBrowserAdapter } = require("./src");

const middleware = new BrowserMiddleware(new MockBrowserAdapter());

(async () => {
  const navigateResult = await middleware.handleToolRequest({
    id: "req-1",
    action: "navigate",
    params: { url: "https://example.com" },
  });

  const extractResult = await middleware.handleToolRequest({
    id: "req-2",
    action: "extractText",
    params: { selector: "h1" },
  });

  console.log(navigateResult, extractResult);
})();
```

The middleware response contains the execution status, any error message, the most recent state, and the history of recent tool calls so the AI model can reason about what happened next.
