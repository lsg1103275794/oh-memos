import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";

import { checkArgContract, recordRawArgKeys } from "./handlers/arg-contract.js";
import { toolAnnotations, toolSchemas } from "./tools-registry.js";

const EXPECTED_TOOL_ORDER = [
  "memos_context_resume",
  "memos_search",
  "memos_think",
  "memos_export_wiki",
  "memos_import_wiki",
  "memos_save",
  "memos_list_v2",
  "memos_get",
  "memos_suggest",
  "memos_distill_skill",
  "memos_list_skill_candidates",
  "memos_review_skill_candidate",
  "memos_install_skill_candidate",
  "memos_graph",
  "memos_admin",
  "memos_canvas",
  "memos_delete",
] as const;

const EXPECTED_ANNOTATIONS: Record<
  (typeof EXPECTED_TOOL_ORDER)[number],
  { readOnlyHint: boolean; openWorldHint: boolean }
> = {
  memos_context_resume: { readOnlyHint: true, openWorldHint: false },
  memos_search: { readOnlyHint: true, openWorldHint: true },
  memos_think: { readOnlyHint: true, openWorldHint: true },
  memos_export_wiki: { readOnlyHint: false, openWorldHint: false },
  memos_import_wiki: { readOnlyHint: false, openWorldHint: true },
  memos_save: { readOnlyHint: false, openWorldHint: true },
  memos_list_v2: { readOnlyHint: true, openWorldHint: false },
  memos_get: { readOnlyHint: true, openWorldHint: false },
  memos_suggest: { readOnlyHint: true, openWorldHint: false },
  memos_distill_skill: { readOnlyHint: false, openWorldHint: true },
  memos_list_skill_candidates: { readOnlyHint: true, openWorldHint: false },
  memos_review_skill_candidate: { readOnlyHint: false, openWorldHint: false },
  memos_install_skill_candidate: { readOnlyHint: false, openWorldHint: false },
  memos_graph: { readOnlyHint: true, openWorldHint: true },
  memos_admin: { readOnlyHint: false, openWorldHint: false },
  memos_canvas: { readOnlyHint: false, openWorldHint: false },
  memos_delete: { readOnlyHint: false, openWorldHint: false },
};

/**
 * Hashes cover business-relevant JSON Schema semantics after resolving local
 * refs and removing dialect-only metadata. The configured default cube value
 * is replaced with a placeholder because CI and local environments use
 * different cube ids while preserving the same defaulting behavior.
 */
const EXPECTED_SCHEMA_HASHES: Record<
  (typeof EXPECTED_TOOL_ORDER)[number],
  string
> = {
  memos_context_resume:
    "1b045846428afb958807d15244c6875e8badd5a9da0b64e802fa586b42ef0618",
  memos_search:
    "3f1885c8736be6c90f78695663473a74874ae5fe598f54e8700dd4e4ef305693",
  memos_think:
    "6ae80d34b1353ff9d6c252ef51ae0a2a421ffe1293d12419ebfafd11399c5c40",
  memos_export_wiki:
    "ca2cd9cd6b74949cfaf98e0e17ff89e73c1bd78eec3fdfc96931b8963e96c264",
  memos_import_wiki:
    "44a530cb35590e7422c367ecca94cd6fbed66067d1e40c549e2795bda31205b0",
  memos_save:
    "4ef273a00f2f5d3551c39dfd890c3991b39249016e842f7a57a4a69f2d4b7181",
  memos_list_v2:
    "6ee747b16e3dbf03636482dc0388ae236b8b26d7eecd256dd46f9e579229b9ea",
  memos_get: "33d79ce41fea8684466f0cbe5ee72defc8900f1d8d998206f2b56272d741f9b4",
  memos_suggest:
    "bd36b15903ae30cb175fe0655d9b0e48e88e83755cd70bddcde278ce37d71d36",
  memos_distill_skill:
    "daa0b3562b2825fcca1da38ad1f36916461e71b6fb8ea4cc25597793c389a04a",
  memos_list_skill_candidates:
    "bd360f077f39f7b62d37a51b24fc7519c64515799a0c5e5538c879c4fe1f511f",
  memos_review_skill_candidate:
    "83f005e615d02031a4c4990439aad23871ec51985eb6c607d2433076df63c862",
  memos_install_skill_candidate:
    "3af1fa6643c15036c360984d09c44c4da09aec3ab7f5c513b942539fd9bb14aa",
  memos_graph:
    "0da0f41e93edbf9fa140bcdf7a0c84cd22d23f68e9ea30b48240c467439914d6",
  memos_admin:
    "295e28686f39889ad0a28dcccbfac5eaf5123dd0836f79fae08282b71fb3711e",
  memos_canvas:
    "5279c78ea730154a1b5a95e242d96120cf6c0b2e30146d58091372ff38db6f19",
  memos_delete:
    "1873d01592e481d388068f49d859d21e47f969e8fe3b30019e04d6bc8465dfa7",
};

type JsonObject = Record<string, unknown>;

const SEMANTIC_KEYS = [
  "type",
  "required",
  "additionalProperties",
  "items",
  "enum",
  "const",
  "default",
  "description",
  "minLength",
  "maxLength",
  "minimum",
  "maximum",
  "exclusiveMinimum",
  "exclusiveMaximum",
  "minItems",
  "maxItems",
  "pattern",
  "format",
  "anyOf",
  "oneOf",
  "allOf",
  "not",
] as const;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

type StandardJsonSchema = {
  "~standard"?: {
    jsonSchema?: {
      input: (options: { target: "draft-2020-12" }) => unknown;
    };
  };
};

function toInputJsonSchema(schema: unknown): JsonObject {
  const standard = (schema as StandardJsonSchema)["~standard"];
  const jsonSchema = standard?.jsonSchema;
  if (!jsonSchema) {
    throw new Error("Tool schema does not implement StandardJSONSchemaV1");
  }
  const result = jsonSchema.input({ target: "draft-2020-12" });
  if (!isObject(result)) {
    throw new Error("Tool schema converter returned a non-object root");
  }
  return result.type === undefined ? { type: "object", ...result } : result;
}

function resolvePointer(root: JsonObject, ref: string): unknown {
  if (!ref.startsWith("#/")) return undefined;

  let current: unknown = root;
  for (const rawSegment of ref.slice(2).split("/")) {
    if (!isObject(current)) return undefined;
    const segment = rawSegment.replaceAll("~1", "/").replaceAll("~0", "~");
    current = current[segment];
  }
  return current;
}

function dereference(
  node: unknown,
  root: JsonObject,
  stack = new Set<string>(),
): unknown {
  if (Array.isArray(node)) {
    return node.map((item) => dereference(item, root, stack));
  }
  if (!isObject(node)) return node;

  const ref = typeof node.$ref === "string" ? node.$ref : undefined;
  if (ref) {
    if (stack.has(ref)) return { $ref: ref };
    const target = resolvePointer(root, ref);
    if (target !== undefined) {
      const nextStack = new Set(stack);
      nextStack.add(ref);
      return dereference(target, root, nextStack);
    }
  }

  return Object.fromEntries(
    Object.entries(node).map(([key, value]) => [
      key,
      dereference(value, root, stack),
    ]),
  );
}

function semanticSchema(
  node: unknown,
  parentKey = "",
  path: string[] = [],
): unknown {
  if (Array.isArray(node)) {
    const values = node.map((item) => semanticSchema(item, "", path));
    if (
      ["required", "enum", "type", "anyOf", "oneOf", "allOf"].includes(
        parentKey,
      )
    ) {
      return values.sort((a, b) =>
        JSON.stringify(a).localeCompare(JSON.stringify(b)),
      );
    }
    return values;
  }
  if (!isObject(node)) return node;

  const result: JsonObject = {};
  if (isObject(node.properties)) {
    result.properties = Object.fromEntries(
      Object.entries(node.properties)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([name, value]) => [
          name,
          semanticSchema(value, "properties", [...path, name]),
        ]),
    );
  }

  for (const key of SEMANTIC_KEYS) {
    if (!Object.hasOwn(node, key)) continue;
    result[key] =
      key === "default" && path.at(-1) === "cube_id"
        ? "<MEMOS_DEFAULT_CUBE>"
        : semanticSchema(node[key], key, path);
  }

  return Object.fromEntries(
    Object.entries(result).sort(([a], [b]) => a.localeCompare(b)),
  );
}

function semanticHash(schema: JsonObject): string {
  const canonical = JSON.stringify(semanticSchema(dereference(schema, schema)));
  return createHash("sha256").update(canonical).digest("hex");
}

describe("legacy MCP protocol contract", () => {
  it("keeps the 17-tool registry in deterministic order", () => {
    expect(Object.keys(toolSchemas)).toEqual(EXPECTED_TOOL_ORDER);
  });

  it("keeps tool annotations stable", () => {
    expect(toolAnnotations).toEqual(EXPECTED_ANNOTATIONS);
  });

  for (const name of EXPECTED_TOOL_ORDER) {
    it("keeps " + name + " schema semantics stable", () => {
      const rawSchema = toInputJsonSchema(toolSchemas[name].inputSchema);
      expect(semanticHash(rawSchema)).toBe(EXPECTED_SCHEMA_HASHES[name]);
    });
  }

  it("keeps unknown routing-key disclosure behavior", () => {
    const requestId = "protocol-contract-routing-key";
    recordRawArgKeys(requestId, {
      query: "auth",
      projectPath: "G:/test/oh-memos",
    });

    const result = checkArgContract("memos_search", requestId);

    expect(result.ignored).toEqual(["projectPath"]);
    expect(result.affectsRouting).toBe(true);
    expect(result.warning).toContain("did you mean `project_path`?");
  });

  it("consumes declared raw keys without a warning", () => {
    const requestId = "protocol-contract-declared-keys";
    recordRawArgKeys(requestId, {
      query: "auth",
      project_path: "G:/test/oh-memos",
    });

    expect(checkArgContract("memos_search", requestId)).toEqual({
      ignored: [],
      affectsRouting: false,
      warning: null,
    });
  });
});
