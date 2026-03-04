/**
 * MemOS MCP Server TypeScript Interfaces and Types
 */

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T = unknown> {
  code: number;
  message?: string;
  data?: T;
}

export interface MemoryNode {
  id: string;
  memory: string;
  key?: string;
  tags?: string[];
  background?: string;
  updated_at?: string;
  created_at?: string;
  timestamp?: string;
  metadata?: MemoryMetadata;
  sources?: Array<string | Record<string, unknown>>;
  relations?: unknown[];
  [key: string]: unknown;
}

export interface MemoryMetadata {
  relativity?: number;
  temporal_rank?: number;
  source?: string;
  updated_at?: string;
  created_at?: string;
  type?: string;
  key?: string;
  tags?: string[];
  sources?: Array<string | Record<string, unknown>>;
  [key: string]: unknown;
}

export interface MemoriesData {
  nodes?: MemoryNode[];
  edges?: GraphEdge[];
}

export interface CubeMemories {
  cube_id?: string;
  memories: MemoriesData | MemoryNode[];
  _source?: string;
  [key: string]: unknown;
}

export interface SearchData {
  text_mem?: CubeMemories[];
}

export interface GraphEdge {
  source?: string;
  target?: string;
  type?: string;
}

// ============================================================================
// Config Types
// ============================================================================

export interface MemosConfig {
  memosUrl: string;
  memosUser: string;
  defaultCubeId: string;
  cubesDir: string;
  timeoutTool: number;
  timeoutStartup: number;
  timeoutHealth: number;
  apiWaitMax: number;
  enableDelete: boolean;
  neo4jHttpUrl?: string;
  neo4jUser?: string;
  neo4jPassword?: string;
}

// ============================================================================
// Query Processing Types
// ============================================================================

export type QueryIntent = "causal" | "related" | "conflict" | "temporal" | "default";

export interface QueryProcessingResult {
  intent: QueryIntent;
  keywords: string[];
  memType?: string;
  cleanedQuery: string;
}

// ============================================================================
// Model Types (Layered)
// ============================================================================

export interface MemoryMinimal {
  id: string;
  memoryType: string;
  summary: string;
  createdAt?: string;
}

export interface MemoryBrief extends MemoryMinimal {
  key?: string;
  tags: string[];
  relevance: number;
}

export interface MemoryFull extends MemoryBrief {
  content: string;
  background?: string;
  cubeId: string;
  userId: string;
  relations: unknown[];
}

export interface CompactedResult {
  preview: MemoryMinimal[];
  totalCount: number;
  omittedCount: number;
  message: string;
  query: string;
  cubeId: string;
}

// ============================================================================
// Cube Types
// ============================================================================

export interface CubeInfo {
  id: string;
  path: string;
}

export interface CubeConfig {
  model_schema?: string;
  user_id?: string;
  cube_id?: string;
  config_filename?: string;
  text_mem?: Record<string, unknown>;
  act_mem?: Record<string, unknown>;
  para_mem?: Record<string, unknown>;
  [key: string]: unknown;
}

// ============================================================================
// Handler Return Type
// ============================================================================

export interface TextContent {
  type: "text";
  text: string;
}
