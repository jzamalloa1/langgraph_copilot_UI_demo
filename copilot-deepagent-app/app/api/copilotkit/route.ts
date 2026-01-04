import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();

if (!process.env.LANGGRAPH_DEPLOYMENT_URL) {
  throw new Error("LANGGRAPH_DEPLOYMENT_URL environment variable is required");
}
if (!process.env.LANGSMITH_API_KEY) {
  throw new Error("LANGSMITH_API_KEY environment variable is required");
}

const runtime = new CopilotRuntime({
  agents: {
    sample_agent: new LangGraphAgent({
      deploymentUrl: process.env.LANGGRAPH_DEPLOYMENT_URL,
      graphId: "my_agent",
      langsmithApiKey: process.env.LANGSMITH_API_KEY,
    }),
  }
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};