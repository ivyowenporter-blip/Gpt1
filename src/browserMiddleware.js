const { ACTIONS, validateToolRequest } = require("./toolSchema");

class BrowserMiddleware {
  constructor(browserAdapter, options = {}) {
    if (!browserAdapter) {
      throw new Error("browserAdapter is required");
    }
    this.browser = browserAdapter;
    this.options = {
      defaultTimeoutMs: 5000,
      maxHistory: 50,
      ...options,
    };
    this.history = [];
    this.state = {
      lastUrl: null,
      lastAction: null,
      lastResult: null,
    };
  }

  getHistory() {
    return [...this.history];
  }

  async handleToolRequest(rawRequest, overrides = {}) {
    const request = validateToolRequest(rawRequest);
    const timeoutMs = this.#resolveTimeout(request, overrides);
    const start = Date.now();

    let result;
    try {
      result = await this.#callWithTimeout(() => this.#execute(request), timeoutMs);
      this.#pushHistory({ request, result, status: "success", startedAt: start });
      this.#updateState(request, result);
      return this.#buildResponse(request, result, start, "success");
    } catch (error) {
      this.#pushHistory({ request, error: error.message, status: "error", startedAt: start });
      this.#updateState(request, null, error.message);
      return this.#buildResponse(request, null, start, "error", error);
    }
  }

  async #execute(request) {
    switch (request.action) {
      case ACTIONS.NAVIGATE:
        return this.browser.navigate(request.params.url);
      case ACTIONS.CLICK:
        return this.browser.click(request.params.selector);
      case ACTIONS.EXTRACT_TEXT:
        return this.browser.extractText(request.params.selector, request.params.timeoutMs);
      default:
        throw new Error(`Unsupported action: ${request.action}`);
    }
  }

  async #callWithTimeout(fn, timeoutMs) {
    const timeout = typeof timeoutMs === "number" && timeoutMs > 0 ? timeoutMs : this.options.defaultTimeoutMs;
    let timeoutId;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error(`Action timed out after ${timeout}ms`));
      }, timeout);
    });

    try {
      const result = await Promise.race([fn(), timeoutPromise]);
      return result;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  #pushHistory(entry) {
    const normalized = {
      ...entry,
      finishedAt: Date.now(),
    };
    this.history.push(normalized);
    if (this.history.length > this.options.maxHistory) {
      this.history.shift();
    }
  }

  #updateState(request, result, errorMessage) {
    this.state = {
      lastUrl: request.action === ACTIONS.NAVIGATE ? request.params.url : this.state.lastUrl,
      lastAction: request.action,
      lastResult: errorMessage ? null : result,
      lastError: errorMessage ?? null,
    };
  }

  #buildResponse(request, result, startedAt, status, error) {
    return {
      id: request.id,
      action: request.action,
      status,
      startedAt,
      finishedAt: Date.now(),
      result: status === "success" ? result : null,
      error: error ? { message: error.message } : null,
      state: { ...this.state },
      history: this.getHistory(),
    };
  }

  #resolveTimeout(request, overrides) {
    if (typeof overrides.timeoutMs === "number") {
      return overrides.timeoutMs;
    }
    if (request.params?.timeoutMs) {
      return request.params.timeoutMs;
    }
    return this.options.defaultTimeoutMs;
  }
}

class MockBrowserAdapter {
  constructor() {
    this.currentUrl = null;
    this.page = {};
  }

  async navigate(url) {
    this.currentUrl = url;
    return { url };
  }

  async click(selector) {
    if (!this.currentUrl) {
      throw new Error("Cannot click before navigating to a page");
    }
    return { clicked: selector };
  }

  async extractText(selector, timeoutMs) {
    if (!this.currentUrl) {
      throw new Error("Cannot extract text before navigating");
    }
    return { selector, text: `Text for ${selector}`, timeoutMs };
  }
}

module.exports = {
  BrowserMiddleware,
  MockBrowserAdapter,
};
