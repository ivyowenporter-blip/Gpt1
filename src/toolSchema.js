const SAFE_PROTOCOLS = new Set(["http:", "https:"]);

const ACTIONS = {
  NAVIGATE: "navigate",
  CLICK: "click",
  EXTRACT_TEXT: "extractText",
};

const schema = {
  type: "object",
  required: ["id", "action"],
  additionalProperties: false,
  properties: {
    id: {
      type: "string",
      minLength: 1,
      maxLength: 128,
    },
    action: {
      type: "string",
      enum: Object.values(ACTIONS),
    },
    params: {
      type: "object",
      default: {},
      additionalProperties: true,
    },
    meta: {
      type: "object",
      additionalProperties: true,
    },
  },
};

function assertString(value, fieldName) {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${fieldName} must be a non-empty string`);
  }
}

function normalizeUrl(candidate) {
  try {
    const url = new URL(candidate);
    if (!SAFE_PROTOCOLS.has(url.protocol)) {
      throw new Error(`Protocol ${url.protocol} is not allowed`);
    }
    return url.toString();
  } catch (error) {
    throw new Error(`Invalid URL: ${candidate}. ${error.message}`);
  }
}

function validateSelector(selector, fieldName) {
  assertString(selector, fieldName);
  if (selector.length > 512) {
    throw new Error(`${fieldName} exceeds maximum length (512)`);
  }
  return selector.trim();
}

function validateSchema(request) {
  if (typeof request !== "object" || request === null) {
    throw new Error("Tool request must be an object");
  }

  if (!request.id) {
    throw new Error("Tool request requires an id");
  }
  assertString(request.id, "id");

  if (!Object.values(ACTIONS).includes(request.action)) {
    throw new Error(`Unsupported action: ${request.action}`);
  }

  if (request.params && typeof request.params !== "object") {
    throw new Error("params must be an object when provided");
  }
}

function applyActionSpecificValidation(request) {
  const safeRequest = { ...request, params: { ...request.params } };

  switch (request.action) {
    case ACTIONS.NAVIGATE: {
      const url = normalizeUrl(request.params?.url ?? "");
      safeRequest.params.url = url;
      break;
    }
    case ACTIONS.CLICK: {
      const selector = validateSelector(request.params?.selector, "selector");
      safeRequest.params.selector = selector;
      break;
    }
    case ACTIONS.EXTRACT_TEXT: {
      const selector = validateSelector(request.params?.selector, "selector");
      const timeoutMs = Number(request.params?.timeoutMs ?? 0) || 0;
      if (timeoutMs < 0 || timeoutMs > 30000) {
        throw new Error("timeoutMs must be between 0 and 30000");
      }
      safeRequest.params.selector = selector;
      safeRequest.params.timeoutMs = timeoutMs;
      break;
    }
    default:
      throw new Error(`Unhandled action: ${request.action}`);
  }
  return safeRequest;
}

function validateToolRequest(request) {
  validateSchema(request);
  return applyActionSpecificValidation(request);
}

module.exports = {
  ACTIONS,
  SAFE_PROTOCOLS,
  schema,
  validateToolRequest,
};
