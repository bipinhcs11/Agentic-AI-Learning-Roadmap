const TRUSTED_COMPONENTS = new Set(["Card", "Table", "Text"]);
const ALLOWED_PROPS = {
  Card: new Set(["title"]),
  Table: new Set(["columns", "rows"]),
  Text: new Set(["text"]),
};

export function validateA2uiPayload(payload) {
  const errors = [];

  if (payload?.metadata?.mimeType !== "application/json+a2ui") {
    errors.push("Unsupported payload MIME type.");
  }

  if (payload?.data?.schemaVersion !== "a2ui.phase10.rung01b.v1") {
    errors.push("Unsupported A2UI schema version.");
  }

  validateComponent(payload?.data?.root, "root", errors);

  return {
    valid: errors.length === 0,
    errors,
  };
}

export function trustedCatalogLabel(payload) {
  const catalog = payload?.metadata?.trustedCatalog;
  return Array.isArray(catalog) ? catalog.join(", ") : "Card, Table, Text";
}

function validateComponent(component, path, errors) {
  if (!component || typeof component !== "object") {
    errors.push(`${path} is missing.`);
    return;
  }

  if (!TRUSTED_COMPONENTS.has(component.type)) {
    errors.push(`${path} uses an untrusted component type.`);
    return;
  }

  const props = component.props ?? {};
  const allowedProps = ALLOWED_PROPS[component.type];
  Object.keys(props).forEach((propName) => {
    if (!allowedProps.has(propName)) {
      errors.push(`${path}.${propName} is not allowed for ${component.type}.`);
    }
  });

  if (component.type === "Card") {
    validateTextProp(props.title, `${path}.title`, errors);
  }

  if (component.type === "Table") {
    validateStringList(props.columns, `${path}.columns`, errors);
    validateTableRows(props.rows, `${path}.rows`, errors);
  }

  if (component.type === "Text") {
    validateTextProp(props.text, `${path}.text`, errors);
  }

  const children = component.children ?? [];
  if (!Array.isArray(children)) {
    errors.push(`${path}.children must be an array.`);
    return;
  }

  children.forEach((child, index) => validateComponent(child, `${path}.children[${index}]`, errors));
}

function validateTextProp(value, path, errors) {
  if (typeof value !== "string" || value.trim().length === 0) {
    errors.push(`${path} must be a non-empty string.`);
  }
}

function validateStringList(value, path, errors) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    errors.push(`${path} must be a string array.`);
  }
}

function validateTableRows(value, path, errors) {
  if (!Array.isArray(value)) {
    errors.push(`${path} must be an array.`);
    return;
  }

  value.forEach((row, index) => validateStringList(row, `${path}[${index}]`, errors));
}
